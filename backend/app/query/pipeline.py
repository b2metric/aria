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
from typing import AsyncGenerator

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.app.core.config import get_settings
from backend.app.query import (
    Conversation,
    ConversationMessage,
    QueryRequest,
    QueryStatus,
)
from agents.artifact_store import ArtifactStore
from agents.chart_builder import run_chart_pipeline_sync
from agents.chart_types import ChartConfig, ChartType

logger = logging.getLogger(__name__)


async def _get_available_tables(engine: AsyncEngine, workspace_id: str) -> list[dict]:
    """Discover available tables from Obsidian vault (multi-tenant)."""
    import os, glob
    vault_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "vaults", workspace_id, "tables")
    try:
        files = glob.glob(os.path.join(vault_path, "*.md"))
        return [{"name": os.path.splitext(os.path.basename(f))[0]} for f in sorted(files)]
    except Exception as e:
        logger.warning("Could not discover tables from vault: %s", e)
        return []


async def _get_table_columns(engine: AsyncEngine, table_name: str, workspace_id: str) -> list[dict]:
    """Discover columns from Obsidian vault markdown (multi-tenant)."""
    import os, re
    vault_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "vaults", workspace_id, "tables")
    md_file = os.path.join(vault_path, f"{table_name}.md")
    try:
        with open(md_file) as f:
            content = f.read()
        cols = []
        for match in re.finditer(r'\*\*(.+?)\*\*:\s*(.+?)\s*\(', content):
            cols.append({"name": match.group(1), "type": match.group(2)})
        return cols if cols else [{"name": "unknown", "type": "VARCHAR2"}]
    except Exception as e:
        logger.warning("Could not read vault %s: %s", table_name, e)
        return [{"name": "unknown", "type": "VARCHAR2"}]


async def _generate_sql(question: str, engine: AsyncEngine, workspace_id: str) -> tuple[str, str]:
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
    schema_info: list[str] = []
    for tbl in tables[:10]:
        cols = await _get_table_columns(engine, tbl["name"], workspace_id)
        col_str = ", ".join(f"{c['name']} ({c['type']})" for c in cols[:15])
        schema_info.append(f"  {tbl['name']}: {col_str}")

    schema_text = "\n".join(schema_info)

    # Rule-based SQL generation based on question keywords and schema
    question_lower = question.lower()

    # Detect aggregations
    wants_count = any(w in question_lower for w in ["count", "how many", "number of", "total"])
    wants_sum = any(w in question_lower for w in ["sum", "total", "revenue", "amount"])
    wants_avg = any(w in question_lower for w in ["average", "avg", "mean"])
    wants_group = any(w in question_lower for w in ["by", "per", "each", "group"])
    wants_top = any(w in question_lower for w in ["top", "highest", "most", "largest", "best"])
    wants_bottom = any(w in question_lower for w in ["bottom", "lowest", "least", "smallest", "worst"])
    wants_trend = any(
        w in question_lower
        for w in ["trend", "over time", "monthly", "daily", "weekly", "by date"]
    )

    # Find matching tables based on question keywords
    best_table = tables[0]["name"]
    best_score = 0
    for tbl in tables:
        score = sum(1 for word in question_lower.split() if word in tbl["name"].lower())
        if score > best_score:
            best_score = score
            best_table = tbl["name"]

    # Build the SELECT clause
    columns = await _get_table_columns(engine, best_table, workspace_id)
    numeric_cols = [
        c
        for c in columns
        if c["type"]
        in ("integer", "numeric", "bigint", "double precision", "real", "float")
    ]
    text_cols = [
        c
        for c in columns
        if c["type"] in ("character varying", "text", "varchar", "char")
    ]
    date_cols = [
        c
        for c in columns
        if c["type"]
        in (
            "date",
            "timestamp without time zone",
            "timestamp with time zone",
            "timestamptz",
        )
    ]
    all_cols = columns

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
        measure = numeric_cols[0]["name"]
        if wants_group and text_cols:
            group_col = text_cols[0]["name"]
            return (
                f"SELECT {group_col}, SUM({measure}) AS total_{measure}\n"
                f"FROM {best_table}\n"
                f"GROUP BY {group_col}\nORDER BY total_{measure} DESC\nLIMIT 50",
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

# Track if Oracle thick mode has been initialized (one-time init)
_oracle_thick_initialized = False


def _init_oracle_thick_mode() -> None:
    """Initialize Oracle thick mode (once per process).
    
    Thick mode is required for advanced Oracle features like:
    - LDAP/OID authentication
    - Kerberos authentication  
    - Oracle Net features (encryption, compression)
    - Some data types (BFILE, REF CURSOR in certain contexts)
    """
    global _oracle_thick_initialized
    if _oracle_thick_initialized:
        return
    
    import oracledb
    from backend.app.core.config import get_settings
    
    settings = get_settings()
    lib_dir = settings.oracle_client_lib_dir
    
    if lib_dir:
        try:
            oracledb.init_oracle_client(lib_dir=lib_dir)
            logger.info("Oracle thick mode initialized", lib_dir=lib_dir)
        except oracledb.ProgrammingError as e:
            if "already been called" in str(e):
                pass  # Already initialized
            else:
                raise
    else:
        # Try default locations
        import os
        default_paths = [
            "/opt/oracle/instantclient_23_3",
            "/opt/oracle/instantclient_21_3", 
            os.path.expanduser("~/instantclient_23_3"),
            os.path.expanduser("~/instantclient_21_3"),
        ]
        for path in default_paths:
            if os.path.exists(path):
                try:
                    oracledb.init_oracle_client(lib_dir=path)
                    logger.info("Oracle thick mode initialized", lib_dir=path)
                    break
                except oracledb.ProgrammingError as e:
                    if "already been called" in str(e):
                        break
                    continue
        else:
            logger.warning("Oracle Instant Client not found, using thin mode")
    
    _oracle_thick_initialized = True


async def _execute_sql_oracle(sql: str, engine: AsyncEngine) -> list[dict]:
    """Execute SQL against Oracle using customer_db_configs."""
    import oracledb
    
    # Initialize thick mode (idempotent)
    _init_oracle_thick_mode()
    from sqlalchemy import text as sa_text
    # Read Oracle connection from customer_db_configs
    async with engine.connect() as conn:
        result = await conn.execute(
            sa_text("SELECT host, port, database_name, username, encrypted_password FROM customer_db_configs WHERE db_type='oracle' LIMIT 1")
        )
        row = result.fetchone()
        if not row:
            raise ValueError("No Oracle DB config found")
        host, port, db, user, pwd = row
    dsn = f"{host}:{port}/{db}"
    conn = oracledb.connect(user=user, password=pwd, dsn=dsn)
    cur = conn.cursor()
    cur.execute(sql)
    columns = [d[0] for d in cur.description]
    rows = [dict(zip(columns, r)) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


async def _execute_sql(sql: str, engine: AsyncEngine) -> list[dict]:
    """Execute a generated SQL query and return the result rows.

    Args:
        sql: The SQL query to execute.
        engine: Async SQLAlchemy engine.

    Returns:
        List of dicts, each representing a row.
    """
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text(sql))
            rows = result.fetchall()
            if not rows:
                return []

            columns = list(result.keys())
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.exception("SQL execution failed: %s", sql[:200])
        raise


# ── Chart Building ─────────────────────────────────────────────────────────


def _build_chart(
    rows: list[dict],
    question: str,
    conversation_id: str,
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
            "chart_config": {"type": "table"},
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

    return {
        "chart_type": chart_type,
        "chart_html": html_content,
        "chart_url": chart_url,
        "csv_url": csv_url,
        "chart_config": {
            "type": chart_type,
            "title": pipeline_result.config.title or question[:60],
            "confidence": pipeline_result.config.confidence,
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
    from backend.app.query.conversation import (
        append_message,
        get_conversation,
        save_conversation,
    )

    cid: str = request.conversation_id or ""
    conversation: Conversation | None = None

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

    try:
        sql, explanation = await _generate_sql(request.question, engine, workspace_id)
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
        rows = await _execute_sql_oracle(sql, engine)  # Oracle via customer_db_configs
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
    )

    yield {
        "event": "chart",
        "data": json.dumps(
            {
                "chart_type": chart_result["chart_type"],
                "chart_html": chart_result["chart_html"],
                "chart_url": chart_result["chart_url"],
                "csv_url": chart_result["csv_url"],
                "chart_config": chart_result["chart_config"],
                "row_count": len(rows),
            }
        ),
    }

    # Stage 6: COMPLETE
    assistant_msg = ConversationMessage(
        role="assistant",
        content=explanation,
        sql=sql,
        chart_spec=chart_result["chart_config"],
        chart_html=chart_result["chart_html"],
        chart_url=chart_result["chart_url"],
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
