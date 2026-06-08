"""NL → SQL → Chart query processing pipeline.

This pipeline transforms natural language questions into SQL queries,
executes them, feeds results through the chart builder (heuristic + Plotly),
uploads rendered HTML/PNG/CSV to MinIO, and streams results via SSE.

Pipeline stages:
  1. THINKING — validating input
  2. GENERATING_SQL — schema discovery + SQL generation
  3. SQL_READY — SQL preview available
  4. SQL_EXECUTING — executing query against database
  5. RENDERING_CHART — chart builder + Plotly render + MinIO upload
  6. COMPLETE — final response ready
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from agents.artifact_store import ArtifactStore
from agents.chart_builder import run_chart_pipeline_sync
from backend.app.query import (
    Conversation,
    ConversationMessage,
    QueryRequest,
    QueryStatus,
)
from backend.app.db import DBConfig, DatabaseType

logger = logging.getLogger(__name__)


async def _get_available_tables(engine: AsyncEngine, workspace_id: str) -> list[dict]:
    """Discover available tables from Obsidian vault (multi-tenant).
    
    Returns list of dicts with: name, keywords, description (for semantic matching).
    """
    import glob
    import os
    import pathlib
    
    # Use absolute path based on project root
    project_root = pathlib.Path(__file__).parent.parent.parent.parent
    vault_path = os.path.join(project_root, "docs", "vaults", workspace_id, "tables")
    
    try:
        files = glob.glob(os.path.join(vault_path, "*.md"))
        tables = []
        for f in sorted(files):
            name = os.path.splitext(os.path.basename(f))[0]
            keywords = ""
            description = ""
            domain = ""
            topic = ""
            order = 999
            insights = []
            try:
                with open(f) as fp:
                    content = fp.read()
                
                # Extract generic metadata from frontmatter or text
                domain_match = re.search(r'(?:domain:\s*["\']?([^"\'\n]+)|## Domain\s*\n([^\n#]+))', content, re.IGNORECASE)
                topic_match = re.search(r'(?:topic:\s*["\']?([^"\'\n]+)|## Topic\s*\n([^\n#]+))', content, re.IGNORECASE)
                order_match = re.search(r'(?:order:\s*(\d+))', content, re.IGNORECASE)
                
                if domain_match:
                    domain = (domain_match.group(1) or domain_match.group(2)).strip()
                if topic_match:
                    topic = (topic_match.group(1) or topic_match.group(2)).strip()
                if order_match:
                    order = int(order_match.group(1).strip())
                    
                # Extract insights as list
                insights_match = re.search(r'(?:insights:\s*\n(.*?)---)', content, re.IGNORECASE | re.DOTALL)
                if insights_match:
                    lines = insights_match.group(1).strip().split('\n')
                    insights = [line.strip().lstrip('-').strip() for line in lines if line.strip() and not line.strip().startswith('#')]
                
                # Extract keywords section
                kw_match = re.search(r'(?:keywords:\s*["\']?([^"\'\n]+)|## Keywords\s*\n([^\n#]+))', content, re.IGNORECASE)
                if kw_match:
                    keywords = (kw_match.group(1) or kw_match.group(2)).strip()
                    
                # Extract description section
                desc_match = re.search(r'(?:description:\s*["\']?([^"\'\n]+)|## Description\s*\n([^\n#]+))', content, re.IGNORECASE)
                if desc_match:
                    description = (desc_match.group(1) or desc_match.group(2)).strip()
                    
            except Exception:
                pass
            
            tables.append({
                "name": name, 
                "keywords": keywords, 
                "description": description,
                "domain": domain,
                "topic": topic,
                "order": order,
                "insights": insights
            })
        return tables
    except Exception as e:
        logger.warning("Could not discover tables from vault: %s", e)
        return []


async def _get_table_columns(engine: AsyncEngine, table_name: str, workspace_id: str) -> list[dict]:
    """Discover columns from Obsidian vault markdown (multi-tenant).
    
    Parses the markdown table format:
    | Column | Type | Nullable | PK | Description |
    |--------|------|----------|----|-----------—|
    | EXEC_DATE | DATE | ✓ |  | Description text |
    
    Also extracts column descriptions from the "## Column Descriptions" section
    for semantic SQL generation.
    """
    import os
    import pathlib
    project_root = pathlib.Path(__file__).parent.parent.parent.parent
    vault_path = os.path.join(project_root, "docs", "vaults", workspace_id, "tables")
    md_file = os.path.join(vault_path, f"{table_name}.md")
    try:
        with open(md_file) as f:
            content = f.read()
        
        cols = []
        
        # Parse markdown table format: | Column | Type | Nullable | PK | Description |
        # Handle leading whitespace and pipe delimiter
        # Example: " | EXEC_DATE | DATE | ✓ |  | Description... |"
        table_pattern = r'^\s*\|\s*([A-Z_][A-Z0-9_]*)\s*\|\s*([A-Z0-9_()]+)\s*\|'
        for match in re.finditer(table_pattern, content, re.MULTILINE | re.IGNORECASE):
            col_name = match.group(1).strip()
            col_type = match.group(2).strip()
            # Skip header/separator rows
            if col_name.lower() in ('column', '---', '--------'):
                continue
            cols.append({"name": col_name, "type": col_type})
        
        # Also try to extract descriptions for better SQL generation context
        # Format: - **COLUMN_NAME**: Description text
        desc_map = {}
        for match in re.finditer(r'-\s*\*\*([A-Z_][A-Z0-9_]*)\*\*:\s*(.+?)(?:\n|$)', content, re.IGNORECASE):
            desc_map[match.group(1).upper()] = match.group(2).strip()[:100]  # Truncate long descriptions
        
        # Enrich columns with descriptions
        for col in cols:
            col["description"] = desc_map.get(col["name"].upper(), "")
        
        if cols:
            logger.debug("Parsed %d columns from vault %s", len(cols), table_name)
            return cols
        
        # Fallback: try legacy format **COLUMN**: TYPE (...)
        for match in re.finditer(r'\*\*([A-Z_][A-Z0-9_]*)\*\*:\s*([A-Z0-9_]+)', content, re.IGNORECASE):
            cols.append({"name": match.group(1), "type": match.group(2), "description": ""})
        
        return cols if cols else [{"name": "unknown", "type": "VARCHAR2", "description": ""}]
    except Exception as e:
        logger.warning("Could not read vault %s: %s", table_name, e)
        return [{"name": "unknown", "type": "VARCHAR2", "description": ""}]


async def _generate_sql(
    question: str, engine: AsyncEngine, workspace_id: str, memory_context=None,
    history: list[dict] | None = None,
) -> tuple[str, str]:
    """Generate SQL from a natural language question using Obsidian vault schema.
    
    Returns (sql, explanation).
    """
    tables = await _get_available_tables(engine, workspace_id)
    if not tables:
        return (
            "SELECT 'no_tables_found' AS info",
            "No database tables were found. Please connect a database first.",
        )

    # Get columns for each table (up to 10 tables for performance)
    # Get columns for each table (up to 10 tables for performance)
    table_columns: dict[str, list[dict]] = {}
    schema_info: list[str] = []
    for tbl in tables[:10]:
        cols = await _get_table_columns(engine, tbl["name"], workspace_id)
        table_columns[tbl["name"]] = cols
        col_str = ", ".join(f"{c['name']} ({c['type']})" for c in cols[:15])
        schema_info.append(f"  {tbl['name']}: {col_str}")
    
    # Generic SQL intent detection

    # Rule-based SQL generation based on question keywords and schema
    question_lower = question.lower()

    # Detect aggregations - with priority handling
    # "total" alone = count, "total X amount/revenue" = sum
    question_has_measure = any(w in question_lower for w in ["amount", "revenue", "sales", "sum", "value", "money", "balance", "topup"])
    wants_sum = question_has_measure and any(w in question_lower for w in ["sum", "total", "revenue", "amount"])
    wants_count = any(w in question_lower for w in ["count", "how many", "number of"]) or ("total" in question_lower and not question_has_measure)
    wants_avg = any(w in question_lower for w in ["average", "avg", "mean"])
    wants_group = any(w in question_lower for w in ["by", "per", "each", "group"])
    wants_top = any(w in question_lower for w in ["top", "highest", "most", "largest", "best"])
    wants_bottom = any(w in question_lower for w in ["bottom", "lowest", "least", "smallest", "worst"])
    wants_trend = any(
        w in question_lower
        for w in ["trend", "over time", "monthly", "daily", "weekly", "by date"]
    )

    # Find matching tables based on question keywords + vault metadata
    best_table = tables[0]["name"]
    best_score = 0
    
    for tbl in tables:
        score = 0
        tbl_name_lower = tbl["name"].lower()
        keywords_lower = tbl.get("keywords", "").lower()
        description_lower = tbl.get("description", "").lower()
        
        # Search context = table name + keywords + description
        
        for word in question_lower.split():
            if len(word) < 3:  # Skip short words
                continue
            # Exact match in table name (weight: 3)
            if word in tbl_name_lower:
                score += 3
            # Match in keywords (weight: 5 - most important)
            if word in keywords_lower:
                score += 5
            # Match in description (weight: 2)
            if word in description_lower:
                score += 2
        
        # Use order as a tie-breaker or priority mechanism if scores are identical or very close (e.g., within 2 points)
        # Lower order number means higher priority.
        tbl_order = tbl.get("order", 999)
        if score > best_score or (score >= best_score - 2 and score > 0 and tbl_order < tables[0].get("order", 999)):
            best_score = score
            best_table = tbl["name"]
            
            # Update the top table properties for later comparison if needed
            # We move the best_table to the front of the list virtually by tracking its order
            if tbl_order < tables[0].get("order", 999):
                 tables[0] = tbl
    
    # If score is too low, our simple lexical heuristic failed to find a confident match
    # This means the question requires semantic understanding (e.g. synonyms, cross-language)
    # Forward to LLM instead of guessing blindly.
    if best_score < 15:
        from backend.app.query.llm_sql import generate_sql_with_llm
        logger.info("Low confidence in rule-based table selection (score=%d). Delegating to LLM.", best_score)
        try:
            return await generate_sql_with_llm(
                question=question,
                tables=tables,
                table_columns=table_columns,
                memory_context=memory_context,
                db_type="oracle",
                history=history,
            )
        except Exception as e:
            logger.warning("LLM SQL generation failed during fallback: %s", e)
    
    logger.info("Table matching: question='%s' -> best_table='%s' (score=%d)", 
                question[:50], best_table, best_score)

    # Build the SELECT clause
    columns = await _get_table_columns(engine, best_table, workspace_id)
    
    # Oracle + PostgreSQL numeric types
    numeric_types = (
        "integer", "numeric", "bigint", "double precision", "real", "float",
        "number", "int", "decimal", "binary_float", "binary_double"
    )
    # Oracle + PostgreSQL text types  
    text_types = (
        "character varying", "text", "varchar", "char", "varchar2", "nvarchar2", 
        "clob", "nclob", "long"
    )
    # Oracle + PostgreSQL date types
    date_types = (
        "date", "timestamp without time zone", "timestamp with time zone",
        "timestamptz", "timestamp", "datetime"
    )
    
    numeric_cols = [c for c in columns if c["type"].lower() in numeric_types]
    text_cols = [c for c in columns if c["type"].lower().split("(")[0] in text_types]
    date_cols = [c for c in columns if c["type"].lower().split("(")[0] in date_types]
    all_cols = columns
    
    # Smart column selection: match column names/descriptions to question keywords
    def _find_best_column(cols: list[dict], question_words: list[str], default_idx: int = 0) -> dict:
        """Find the column most relevant to the question."""
        if not cols:
            return {"name": "unknown", "type": "VARCHAR2", "description": ""}
        best = cols[default_idx] if default_idx < len(cols) else cols[0]
        best_score = 0
        for col in cols:
            score = 0
            col_name_lower = col["name"].lower()
            col_desc_lower = col.get("description", "").lower()
            for word in question_words:
                if len(word) < 3:
                    continue
                if word in col_name_lower:
                    score += 3
                if word in col_desc_lower:
                    score += 2
            if score > best_score:
                best_score = score
                best = col
        return best
    
    question_words = question_lower.split()

    if wants_count:
        if wants_group and text_cols:
            group_col = text_cols[0]["name"]
            return (
                f"SELECT {group_col}, COUNT(*) AS count\nFROM {best_table}\n"
                f"GROUP BY {group_col}\nORDER BY count DESC\nLIMIT 50",
                f"Counting records grouped by {group_col} from the {best_table} table.",
            )
        return (
            f"SELECT COUNT(*) AS total_count FROM {best_table}",
            f"Counting all records in the {best_table} table.",
        )

    if wants_sum and numeric_cols:
        # Find the best numeric column matching the question (amount, revenue, etc.)
        measure_col = _find_best_column(numeric_cols, question_words)
        measure = measure_col["name"]
        
        if wants_group:
            # Determine grouping: by date (month/day/week) or by category
            if date_cols and any(w in question_lower for w in ["month", "monthly", "by month"]):
                date_col = _find_best_column(date_cols, question_words)["name"]
                # Oracle: TRUNC(date, 'MM'), PostgreSQL: DATE_TRUNC('month', date)
                return (
                    f"SELECT TRUNC({date_col}, 'MM') AS month, SUM({measure}) AS total_{measure}\n"
                    f"FROM {best_table}\n"
                    f"GROUP BY TRUNC({date_col}, 'MM')\n"
                    f"ORDER BY month\n"
                    f"FETCH FIRST 100 ROWS ONLY",
                    f"Monthly total of {measure} from {best_table}, grouped by {date_col}.",
                )
            elif date_cols and any(w in question_lower for w in ["day", "daily", "by day", "by date"]):
                date_col = _find_best_column(date_cols, question_words)["name"]
                return (
                    f"SELECT TRUNC({date_col}) AS day, SUM({measure}) AS total_{measure}\n"
                    f"FROM {best_table}\n"
                    f"GROUP BY TRUNC({date_col})\n"
                    f"ORDER BY day\n"
                    f"FETCH FIRST 100 ROWS ONLY",
                    f"Daily total of {measure} from {best_table}, grouped by {date_col}.",
                )
            elif text_cols:
                group_col = _find_best_column(text_cols, question_words)["name"]
                return (
                    f"SELECT {group_col}, SUM({measure}) AS total_{measure}\n"
                    f"FROM {best_table}\n"
                    f"GROUP BY {group_col}\n"
                    f"ORDER BY total_{measure} DESC\n"
                    f"FETCH FIRST 50 ROWS ONLY",
                    f"Summing {measure} grouped by {group_col} from {best_table}.",
                )
        return (
            f"SELECT SUM({measure}) AS total_{measure} FROM {best_table}",
            f"Total sum of {measure} from {best_table}.",
        )

    if wants_top and numeric_cols:
        measure = numeric_cols[0]["name"]
        label_col = text_cols[0]["name"] if text_cols else all_cols[0]["name"]
        return (
            f"SELECT {label_col}, {measure}\nFROM {best_table}\n"
            f"ORDER BY {measure} DESC\nLIMIT 10",
            f"Top 10 records from {best_table} ranked by {measure}.",
        )

    if wants_bottom and numeric_cols:
        measure = numeric_cols[0]["name"]
        label_col = text_cols[0]["name"] if text_cols else all_cols[0]["name"]
        return (
            f"SELECT {label_col}, {measure}\nFROM {best_table}\n"
            f"ORDER BY {measure} ASC\nLIMIT 10",
            f"Bottom 10 records from {best_table} ranked by {measure}.",
        )

    if wants_trend and date_cols and numeric_cols:
        date_col = date_cols[0]["name"]
        measure = numeric_cols[0]["name"]
        return (
            f"SELECT DATE_TRUNC('month', {date_col}) AS month, "
            f"SUM({measure}) AS total\nFROM {best_table}\n"
            f"GROUP BY month\nORDER BY month\nLIMIT 100",
            f"Monthly trend of {measure} from {best_table}.",
        )

    if wants_avg and numeric_cols:
        measure = numeric_cols[0]["name"]
        return (
            f"SELECT AVG({measure}) AS avg_{measure} FROM {best_table}",
            f"Average {measure} from {best_table}.",
        )

    # Default: select first few columns
    select_cols = ", ".join(c["name"] for c in all_cols[:5])
    return (
        f"SELECT {select_cols}\nFROM {best_table}\nLIMIT 50",
        f"Showing sample data from {best_table} (first 50 rows).",
    )


# ── SQL Execution ──────────────────────────────────────────────────────────


def _transform_sql_for_dialect(sql: str, db_type: DatabaseType) -> str:
    """Transform SQL syntax for the target database dialect.
    
    Handles dialect-specific differences like:
    - LIMIT N → FETCH FIRST N ROWS ONLY (Oracle)
    - LIMIT N → TOP N (MSSQL - for simple cases)
    
    Args:
        sql: Original SQL query
        db_type: Target database type
        
    Returns:
        Transformed SQL for the target dialect
    """
    from backend.app.db import DatabaseType
    
    if db_type == DatabaseType.ORACLE:
        # Convert "LIMIT N" to "FETCH FIRST N ROWS ONLY"
        import re
        pattern = r'\bLIMIT\s+(\d+)\s*$'
        match = re.search(pattern, sql, re.IGNORECASE | re.MULTILINE)
        if match:
            n = match.group(1)
            sql = re.sub(pattern, f'FETCH FIRST {n} ROWS ONLY', sql, flags=re.IGNORECASE | re.MULTILINE)
    
    elif db_type == DatabaseType.MSSQL:
        # For MSSQL, LIMIT must be replaced with TOP (simple cases only)
        # Complex cases with ORDER BY need OFFSET/FETCH
        import re
        pattern = r'\bLIMIT\s+(\d+)\s*$'
        match = re.search(pattern, sql, re.IGNORECASE | re.MULTILINE)
        if match:
            n = match.group(1)
            # Remove LIMIT clause
            sql = re.sub(pattern, '', sql, flags=re.IGNORECASE | re.MULTILINE)
            # Add TOP after SELECT
            sql = re.sub(r'^SELECT\b', f'SELECT TOP {n}', sql, count=1, flags=re.IGNORECASE)
    
    return sql


async def _get_db_config(engine: AsyncEngine, workspace_id: str) -> DBConfig:
    """Fetch database config for the workspace from customer_db_configs.
    
    Args:
        engine: Async SQLAlchemy engine (metadata DB)
        workspace_id: Workspace/customer ID
        
    Returns:
        DBConfig instance for the customer's database
        
    Raises:
        ValueError: If no DB config found for workspace
    """
    import os
    env = os.getenv("APP_ENV", "development")
    
    # Dev override: Ignore "default" workspace requests and force stc-kuwait
    if env != "production" and workspace_id == "default":
        workspace_id = "stc-kuwait"
    from sqlalchemy import text as sa_text

    from backend.app.db import DatabaseType, DBConfig
    
    async with engine.connect() as conn:
        result = await conn.execute(
            sa_text("""
                SELECT db_type, host, port, database_name, username, encrypted_password
                FROM customer_db_configs cdc
                JOIN customers c ON cdc.customer_id = c.id
                WHERE c.slug = :workspace_id
                LIMIT 1
            """),
            {"workspace_id": workspace_id},
        )
        row = result.fetchone()
        
    if not row:
        # Fallback to defaults or dummy connection for local dev if customer is not found
        import os
        env = os.getenv("APP_ENV", "development")
        if env != "production":
            return DBConfig(
                db_type=DatabaseType.ORACLE,
                host="localhost",
                port=1521,
                database="FREEPDB1",
                username="stc",
                password="stc123",
            )
        raise ValueError(f"No DB config found for workspace: {workspace_id}")
    
    db_type_str, host, port, database, username, password = row
    
    # Map string to enum
    db_type_map = {
        "postgresql": DatabaseType.POSTGRESQL,
        "mysql": DatabaseType.MYSQL,
        "oracle": DatabaseType.ORACLE,
        "mssql": DatabaseType.MSSQL,
    }
    db_type = db_type_map.get(db_type_str.lower())
    if not db_type:
        raise ValueError(f"Unsupported database type: {db_type_str}")
    
    return DBConfig(
        db_type=db_type,
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,  # TODO: decrypt encrypted_password
    )


async def _execute_sql(
    sql: str,
    engine: AsyncEngine,
    workspace_id: str | None = None,
) -> list[dict]:
    """Execute a generated SQL query against the customer's database.
    
    This function supports multiple database backends:
    - PostgreSQL
    - MySQL
    - Oracle (thin mode by default)
    - MSSQL
    
    Args:
        sql: The SQL query to execute
        engine: Async SQLAlchemy engine (for fetching DB config)
        workspace_id: Workspace/customer ID to look up DB config
        
    Returns:
        List of dicts, each representing a row
        
    Raises:
        ValueError: If no DB config found or unsupported DB type
    """
    from backend.app.db import execute_query
    
    # If no workspace_id, try to execute against metadata DB (for schema queries)
    if not workspace_id:
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text(sql))
                rows = result.fetchall()
                if not rows:
                    return []
                columns = list(result.keys())
                return [dict(zip(columns, row, strict=False)) for row in rows]
        except Exception:
            logger.exception("SQL execution failed: %s", sql[:200])
            raise
    
    # Get customer's DB config and execute
    config = await _get_db_config(engine, workspace_id)
    
    # Transform SQL for target dialect (LIMIT → FETCH FIRST for Oracle)
    transformed_sql = _transform_sql_for_dialect(sql, config.db_type)
    
    logger.info(
        "Executing query on %s://%s:%d/%s",
        config.db_type.value,
        config.host,
        config.port,
        config.database,
    )
    
    try:
        return await execute_query(transformed_sql, config)
    except Exception:
        logger.exception(
            "SQL execution failed on %s: %s",
            config.db_type.value,
            sql[:200],
        )
        raise


# ── Chart Building ─────────────────────────────────────────────────────────


def _json_safe(value):
    """Coerce a DB cell into a JSON-serialisable value.

    Oracle/Postgres rows carry Decimal / datetime / date / bytes, which
    json.dumps cannot encode — sending them raw over SSE breaks the stream
    ("[Errno 32] Broken pipe"). Convert them here.
    """
    import datetime as _dt
    from decimal import Decimal as _Decimal

    if isinstance(value, _Decimal):
        return float(value)
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", "replace")
    return value


def _json_safe_rows(rows: list[dict]) -> list[dict]:
    """Return rows with every cell coerced to a JSON-serialisable value."""
    return [{k: _json_safe(v) for k, v in row.items()} for row in rows]


def _detect_requested_chart_type(question: str) -> str | None:
    """Detect an explicit chart-type request in the question ('as a pie chart').

    Returns one of bar/line/area/pie/scatter, or None if the user didn't ask.
    """
    q = (question or "").lower()
    if "grid" in q or "table" in q or "tablo" in q:
        return "table"
    for t in ("pie", "scatter", "area", "line", "bar"):
        if t in q:
            return t
    return None


_CHART_REQ_FILLER = {
    "give", "me", "a", "an", "the", "show", "make", "it", "as", "to", "chart",
    "charts", "graph", "plot", "please", "can", "you", "this", "that", "into",
    "draw", "display", "with", "of", "in", "view", "instead", "turn", "convert",
    "now", "pie", "bar", "line", "area", "scatter", "table", "tablo", "grid", "data",
}


def _is_chart_type_only_request(question: str) -> bool:
    """True if the question ONLY asks to change the chart type (no new data).

    e.g. 'give me a pie chart', 'make it a bar', 'as line' -> True;
    'revenue by region as pie' -> False (mentions data).
    """
    q = (question or "").lower()
    for ch in ",.!?;:'\"()-/\n\t":
        q = q.replace(ch, " ")
    tokens = [t for t in q.split() if t and t not in _CHART_REQ_FILLER]
    return len(tokens) == 0


def _build_chart(
    rows: list[dict],
    question: str,
    conversation_id: str,
    forced_type: str | None = None,
) -> dict:
    """Run the chart builder pipeline: heuristic → Plotly render → MinIO upload.

    Args:
        rows: Query result rows (list of dicts).
        question: Original natural language question.
        conversation_id: For MinIO key prefix.

    Returns:
        Dict with chart_html, chart_url, chart_type, csv_url, and errors.
    """
    if not rows:
        return {
            "chart_type": "table",
            "chart_html": _empty_chart_html("No data returned from query."),
            "chart_url": "",
            "csv_url": "",
            "chart_data": [],
            "chart_config": {"type": "table", "title": "", "xKey": "", "yKeys": []},
            "errors": ["No data returned"],
        }

    # ── Stage 1: Chart pipeline (heuristic proposer + Plotly render) ──────
    columns = list(rows[0].keys())
    pipeline_result = run_chart_pipeline_sync(
        rows,
        columns=columns,
        question=question,
        use_llm=False,  # Heuristic only — fast, no external API call
        render_formats=("html", "csv"),
    )

    chart_type = pipeline_result.config.chart_type.value
    # Honor an explicit user request ("give me a pie chart") over the heuristic pick.
    if forced_type:
        chart_type = forced_type
    html_content = pipeline_result.html_content or _empty_chart_html("Chart rendering failed.")
    csv_content = pipeline_result.csv_content or ""
    errors = pipeline_result.errors

    # ── Stage 2: Upload to MinIO ──────────────────────────────────────────
    chart_url = ""
    csv_url = ""

    try:
        store = ArtifactStore()
        prefix = f"conversations/{conversation_id}"

        if html_content:
            html_ref = store.upload_html(
                html_content,
                key_prefix=prefix,
                key=f"{prefix}/chart_{conversation_id}.html",
            )
            chart_url = html_ref.public_url() or html_ref.presigned_url(expires=86400)
            logger.info("chart_uploaded_to_minio", key=html_ref.key)

        if csv_content:
            csv_ref = store.upload_csv(
                csv_content,
                key_prefix=prefix,
                key=f"{prefix}/data_{conversation_id}.csv",
            )
            csv_url = csv_ref.public_url() or csv_ref.presigned_url(expires=86400)
    except Exception as exc:
        logger.warning("MinIO upload failed, using inline HTML: %s", exc)
        errors.append(f"MinIO upload failed: {exc}")
        # Even if MinIO fails, chart_html is still available inline

    # Derive recharts keys + JSON data for client-side rendering (ChartArea).
    # This replaces shipping multi-MB inline Plotly HTML to the browser.
    cfg = pipeline_result.config
    x_key = cfg.x.column or (columns[0] if columns else "")
    y_keys = [cfg.y.column] if cfg.y.column else [
        c for c in columns
        if c != x_key and rows and isinstance(rows[0].get(c), (int, float))
    ]
    MAX_CHART_POINTS = 1000
    chart_data = _json_safe_rows(rows[:MAX_CHART_POINTS])

    return {
        "chart_type": chart_type,
        # chart_html retained only for the MinIO upload above; NOT streamed inline.
        "chart_html": html_content,
        "chart_url": chart_url,
        "csv_url": csv_url,
        "chart_data": chart_data,
        "chart_config": {
            "type": chart_type,
            "title": cfg.title or question[:60],
            "xKey": x_key,
            "yKeys": y_keys,
            "confidence": cfg.confidence,
            "total_rows": len(rows),
            "truncated": len(rows) > MAX_CHART_POINTS,
        },
        "errors": errors,
    }


def _empty_chart_html(message: str = "No data available.") -> str:
    """Return a minimal HTML page for empty/error states."""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        "<style>\n"
        "  body {\n"
        "    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;\n"
        "    display: flex; align-items: center; justify-content: center;\n"
        "    height: 100vh; margin: 0; color: #888; font-size: 16px;\n"
        "  }\n"
        "</style>\n"
        "</head>\n"
        f"<body><p>{message}</p></body>\n"
        "</html>"
    )


# ── Main Pipeline ──────────────────────────────────────────────────────────


async def process_query(
    redis: Redis,
    engine: AsyncEngine,
    request: QueryRequest,
    workspace_id: str,
    user_id: str,
) -> AsyncGenerator[dict, None]:
    """Process a natural language query and yield SSE events.

    Pipeline stages:
    1. THINKING — validating input
    2. GENERATING_SQL — schema discovery + SQL generation
    3. SQL_READY — SQL preview available
    4. SQL_EXECUTING — executing query against database
    5. RENDERING_CHART — chart builder + Plotly render + MinIO upload
    6. COMPLETE — final response ready
    """
    from backend.app.memory.service import MemoryService
    from backend.app.query.conversation import (
        append_message,
        get_conversation,
        save_conversation,
    )

    cid: str = request.conversation_id or ""
    conversation: Conversation | None = None
    
    # Dev override: Force workspace_id to stc-kuwait
    import os
    env = os.getenv("APP_ENV", "development")
    if env != "production" and workspace_id == "default":
        workspace_id = "stc-kuwait"

    # Stage 1: THINKING
    yield {
        "event": "status",
        "data": json.dumps(
            {"status": QueryStatus.THINKING.value, "message": "Analyzing your question..."}
        ),
    }
    await asyncio.sleep(0.1)

    # Load or create conversation
    if cid:
        conversation = await get_conversation(redis, workspace_id, cid)
        if conversation is None:
            yield {
                "event": "error",
                "data": json.dumps({"error": f"Conversation {cid} not found"}),
            }
            return

    if conversation is None:
        conversation = Conversation(workspace_id=workspace_id, user_id=user_id)
        await save_conversation(redis, conversation)
        cid = conversation.id

    # Save user message
    user_msg = ConversationMessage(role="user", content=request.question)
    conversation = await append_message(redis, workspace_id, cid, user_msg)

    # ── Fast path: pure chart-type change ("give me a pie chart") ──────────
    # Reuse the previous result's data and just re-render with the requested type.
    # No LLM, no SQL re-run -> it can never drift to a different/unrelated query.
    _req_type = _detect_requested_chart_type(request.question)
    _prev_assistant = next(
        (m for m in reversed(conversation.messages[:-1]) if m.role == "assistant"),
        None,
    )
    if (
        _req_type
        and _is_chart_type_only_request(request.question)
        and _prev_assistant is not None
        and _prev_assistant.chart_data
    ):
        reused_sql = _prev_assistant.sql or ""
        cfg = dict(_prev_assistant.chart_spec or {})
        cfg["type"] = _req_type
        if reused_sql:
            yield {
                "event": "sql",
                "data": json.dumps({
                    "sql": reused_sql,
                    "explanation": f"Re-rendered the previous result as a {_req_type} chart.",
                }),
            }
        yield {
            "event": "chart",
            "data": json.dumps({
                "chart_type": _req_type,
                "chart_data": _prev_assistant.chart_data,
                "chart_url": _prev_assistant.chart_url or "",
                "csv_url": "",
                "chart_config": cfg,
                "row_count": len(_prev_assistant.chart_data),
            }, default=str),
        }
        await append_message(
            redis, workspace_id, cid,
            ConversationMessage(
                role="assistant",
                content=f"Here is the previous result as a {_req_type} chart.",
                sql=reused_sql,
                chart_spec=cfg,
                chart_data=_prev_assistant.chart_data,
                chart_url=_prev_assistant.chart_url,
            ),
        )
        yield {
            "event": "status",
            "data": json.dumps({
                "status": QueryStatus.COMPLETE.value,
                "message": "Chart updated",
                "conversation_id": cid,
            }),
        }
        yield {"event": "done", "data": json.dumps({"conversation_id": cid})}
        return

    # Stage 1.5: MEMORY_LOOKUP
    memory_svc = MemoryService.get_instance()
    # Team ID is mock for now since user.team_id could be passed.
    mem_context = memory_svc.lookup(
        question=request.question,
        user_id=user_id,
        workspace_id=workspace_id,
        team_id="default-team"
    )
    prompt_context = mem_context.to_prompt_context()
    if prompt_context:
        logger.info("Found memory context for user %s: %s bytes", user_id, len(prompt_context))
    
    # Stage 2: GENERATING_SQL
    yield {
        "event": "status",
        "data": json.dumps(
            {
                "status": QueryStatus.GENERATING_SQL.value,
                "message": "Discovering schema and generating SQL...",
            }
        ),
    }

    # Build recent conversation history (prior user questions + the SQL used) so the
    # LLM can handle follow-ups ("as a pie chart", "filter to last 30 days", "add region").
    history: list[dict] = []
    _prev_q: str | None = None
    for _m in conversation.messages[:-1]:  # exclude the just-added current user message
        if _m.role == "user":
            _prev_q = _m.content
        elif _m.role == "assistant":
            history.append({"question": _prev_q or "", "sql": _m.sql})
            _prev_q = None

    try:
        sql, explanation = await _generate_sql(
            request.question, engine, workspace_id,
            memory_context=mem_context, history=history,
        )
    except Exception as e:
        logger.exception("SQL generation failed")
        yield {
            "event": "error",
            "data": json.dumps({"error": f"SQL generation failed: {e}"}),
        }
        return

    # Stage 3: SQL_READY
    yield {
        "event": "sql",
        "data": json.dumps({"sql": sql, "explanation": explanation}),
    }
    yield {
        "event": "status",
        "data": json.dumps(
            {
                "status": QueryStatus.SQL_READY.value,
                "message": "SQL generated",
                "sql": sql,
            }
        ),
    }

    # Stage 4: SQL_EXECUTING
    yield {
        "event": "status",
        "data": json.dumps(
            {
                "status": QueryStatus.EXECUTING.value,
                "message": "Executing query...",
            }
        ),
    }

    rows: list[dict] = []
    try:
        rows = await _execute_sql(sql, engine, workspace_id=workspace_id)
    except Exception as e:
        logger.exception("SQL execution failed")
        yield {
            "event": "error",
            "data": json.dumps({"error": f"Query execution failed: {e}"}),
        }
        return

    # Stage 5: RENDERING_CHART
    yield {
        "event": "status",
        "data": json.dumps(
            {
                "status": QueryStatus.RENDERING_CHART.value,
                "message": f"Building chart from {len(rows)} rows...",
            }
        ),
    }

    chart_result = _build_chart(
        rows=rows,
        question=request.question,
        conversation_id=cid,
        forced_type=_detect_requested_chart_type(request.question),
    )

    yield {
        "event": "chart",
        "data": json.dumps(
            {
                "chart_type": chart_result.get("chart_type", "table"),
                # JSON data points for client-side recharts (was multi-MB chart_html).
                "chart_data": chart_result.get("chart_data", []),
                # MinIO link to the full Plotly artifact (lazy-loaded, not inlined).
                "chart_url": chart_result.get("chart_url", ""),
                "csv_url": chart_result.get("csv_url", ""),
                "chart_config": chart_result.get("chart_config", {"type": "table"}),
                "row_count": len(rows),
            },
            # Safety net: any value missed by _json_safe_rows degrades to str
            # instead of crashing the SSE stream ("[Errno 32] Broken pipe").
            default=str,
        ),
    }

    # Stage 5.5: STORE_MEMORY
    # Sadece veri donduyse (success rate %100 ise) SQL cache'e veya pattern hafizasina at
    if len(rows) > 0:
        try:
            # Arka planda await blocklamamak icin asenkron degil, hizlica yolluyoruz (veya async function cevrilmeli, service senkron oldugu icin direkt calisir)
            memory_svc.store_query(
                question=request.question,
                sql=sql,
                table="unknown", # We can extract best_table if needed, mock for now
                user_id=user_id,
                workspace_id=workspace_id,
                row_count=len(rows)
            )
            logger.info("Successfully stored query context in Mem0 MemoryService")
        except Exception as e:
            logger.warning("Failed to store memory: %s", e)
            
    # Stage 6: COMPLETE
    assistant_msg = ConversationMessage(
        role="assistant",
        content=explanation,
        sql=sql,
        chart_spec=chart_result.get("chart_config", {"type": "table"}),
        # Persist JSON data + MinIO url, NOT the multi-MB inline HTML (Redis/history bloat).
        chart_data=chart_result.get("chart_data", []),
        chart_url=chart_result.get("chart_url", ""),
    )
    conversation = await append_message(redis, workspace_id, cid, assistant_msg)

    yield {
        "event": "status",
        "data": json.dumps(
            {
                "status": QueryStatus.COMPLETE.value,
                "message": "Query processed successfully",
                "conversation_id": cid,
            }
        ),
    }

    yield {
        "event": "done",
        "data": json.dumps({"conversation_id": cid}),
    }
