"""NL → SQL → Chart query processing pipeline.

This pipeline transforms natural language questions into SQL queries,
executes them, feeds results through the chart builder (heuristic + Plotly),
uploads a static PNG + CSV chart artifact to MinIO, and streams results via SSE.

Pipeline stages:
  1. THINKING — validating input
  2. GENERATING_SQL — schema discovery + SQL generation
  3. SQL_READY — SQL preview available
  4. SQL_EXECUTING — executing query against database
  5. RENDERING_CHART — chart builder → Recharts JSON + MinIO PNG/CSV artifact
  6. COMPLETE — final response ready
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid as _uuid
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from agents.artifact_store import ArtifactStore
from agents.chart_builder import run_chart_pipeline_sync
from backend.app.db import DatabaseType, DBConfig
from backend.app.memory.service import MemoryService
from backend.app.query import (
    Conversation,
    ConversationMessage,
    QueryRequest,
    QueryStatus,
)
from backend.app.services.audit import AuditService

logger = logging.getLogger(__name__)


# ── User Preference Detection ─────────────────────────────────────────────────


def _detect_user_correction(question: str, prev_messages: list) -> dict | None:
    """Detect if user is correcting a previous result.

    Patterns:
    - "no, I meant X" / "hayır, X'i kastetmiştim"
    - "not X, use Y" / "X değil, Y kullan"
    - "actually I want X" / "aslında X istiyorum"
    - "wrong column, use X" / "yanlış kolon, X kullan"

    Returns dict with correction info if detected, None otherwise.
    """
    q = question.lower()

    correction_patterns = [
        # English
        (r"\b(no|not)\b.*(meant|want|use|should be|i need)\s+(\w+)", "correction"),
        (r"\bactually\b.*(want|need|use|meant)\s+(\w+)", "correction"),
        (r"\bwrong\b.*(column|table|field).*(use|should be)\s+(\w+)", "column_correction"),
        (r"\binstead of\b.*\buse\s+(\w+)", "correction"),
        # Turkish
        (r"\b(hayır|yanlış|değil)\b.*(kastet|kullan|olmalı|istiyorum)\s*(\w+)?", "correction"),
        (r"\baslında\b.*(istiyorum|kullan|lazım)\s*(\w+)?", "correction"),
    ]

    for pattern, correction_type in correction_patterns:
        match = re.search(pattern, q, re.IGNORECASE)
        if match:
            # Extract what they want
            groups = match.groups()
            target = groups[-1] if groups[-1] else None
            return {
                "type": correction_type,
                "target": target,
                "original_question": question,
            }

    return None


def _detect_chart_preference(question: str) -> dict | None:
    """Detect chart type preference from user message.

    E.g., "always show as bar chart", "I prefer pie charts"
    """
    q = question.lower()

    preference_patterns = [
        (r"\b(always|prefer|like)\b.*(bar|line|pie|area|scatter|table)", "chart_type"),
        (r"\b(her zaman|tercih|seviyorum)\b.*(bar|çizgi|pasta|alan|tablo)", "chart_type"),
    ]

    chart_map = {
        "bar": "bar",
        "line": "line",
        "pie": "pie",
        "area": "area",
        "scatter": "scatter",
        "table": "table",
        "çizgi": "line",
        "pasta": "pie",
        "alan": "area",
        "tablo": "table",
    }

    for pattern, pref_type in preference_patterns:
        match = re.search(pattern, q, re.IGNORECASE)
        if match:
            chart_word = match.group(2).lower()
            chart_type = chart_map.get(chart_word)
            if chart_type:
                return {
                    "type": pref_type,
                    "value": chart_type,
                    "original_question": question,
                }

    return None


def _extract_preference_from_successful_query(
    question: str,
    sql: str,
    table: str,
    columns_used: list[str],
) -> str | None:
    """Extract implicit preference from successful query patterns.

    E.g., if user asks for "revenue" and we used TOPUP_AMOUNT successfully,
    store: "User uses TOPUP_AMOUNT for revenue queries"
    """
    q = question.lower()

    # Revenue/amount mapping
    if any(w in q for w in ["revenue", "gelir", "amount", "tutar"]):
        amount_cols = [
            c
            for c in columns_used
            if any(x in c.lower() for x in ["amount", "revenue", "total", "sum", "topup", "bill"])
        ]
        if amount_cols:
            return f"User associates '{amount_cols[0]}' with revenue/amount queries on {table}"

    # Count/subscriber mapping
    if any(w in q for w in ["subscriber", "customer", "abone", "müşteri", "count"]):
        id_cols = [
            c
            for c in columns_used
            if any(x in c.lower() for x in ["msisdn", "subscriber", "customer", "id", "contrno"])
        ]
        if id_cols:
            return f"User uses '{id_cols[0]}' for subscriber/customer counts on {table}"

    return None


# ── Vault-policy resolution (shared by table-pruning + row-level security) ──────


# sqlglot dialect names keyed by the DatabaseType enum *value*.
_SQLGLOT_DIALECTS: dict[str, str] = {
    "postgresql": "postgres",
    "mysql": "mysql",
    "oracle": "oracle",
    "mssql": "tsql",
}


def _sqlglot_dialect(db_type_value: str | None) -> str | None:
    """Map a ``DatabaseType`` value to a sqlglot dialect (None if unknown)."""
    if not db_type_value:
        return None
    return _SQLGLOT_DIALECTS.get(db_type_value.lower())


async def _resolve_vault_policy(
    workspace_id: str,
    db: AsyncSession,
    team_id: str | None = None,
):
    """Resolve the active ``TeamVaultPolicy`` for ``(workspace_id, team_id)``.

    Scopes by ``Customer.slug == workspace_id`` and prefers the team-specific
    policy over the customer-wide default (``team_id IS NULL``).  Only active
    policies are considered.  Returns ``None`` when no policy applies.

    This is the single source of truth for policy lookup, shared by both
    table-level pruning and row-level security so the two never diverge.
    """
    from sqlalchemy import select as sa_select

    from backend.app.models.governance import TeamVaultPolicy
    from backend.app.models.organization import Customer

    # Accept team_id as either a UUID string or a raw UUID.
    if isinstance(team_id, str):
        try:
            team_uuid = _uuid.UUID(team_id)
        except ValueError:
            team_uuid = None
    else:
        team_uuid = team_id

    # Scope policy lookup to THIS customer — otherwise another tenant's default
    # (team_id IS NULL) policy would leak into this workspace.
    cust_id = (
        await db.execute(sa_select(Customer.id).where(Customer.slug == workspace_id))
    ).scalar_one_or_none()
    if cust_id is None:
        return None

    result = await db.execute(
        sa_select(TeamVaultPolicy).where(
            TeamVaultPolicy.customer_id == cust_id,
            TeamVaultPolicy.team_id.in_([team_uuid, None])
            if team_uuid
            else TeamVaultPolicy.team_id.is_(None),
            TeamVaultPolicy.is_active == True,  # noqa: E712
        )
    )
    policies = result.scalars().all()

    # Prefer team-specific policy over the customer-wide default.
    policy = None
    if team_uuid:
        policy = next((p for p in policies if p.team_id == team_uuid), None)
    if not policy:
        policy = next((p for p in policies if p.team_id is None), None)
    return policy


async def get_active_tables(workspace_id: str, db: AsyncSession) -> set[str]:
    """Union of ``allowed_tables`` across all ACTIVE TeamVaultPolicy rows for the
    workspace's customer (team-specific policies AND the customer-wide default).

    These are the tables at least one team can query — the only ones worth the
    expensive per-table work (enum sampling, sample-data extraction, LLM
    enrichment). Returns LOWERCASED names. An empty set means "no active scoping
    policy exists"; callers MUST treat that as 'fall back to all tables', never
    as 'process nothing' (scoping is a performance optimization, not a security
    boundary — RLS/CLS remain the enforcement points).
    """
    from sqlalchemy import select as sa_select

    from backend.app.models.governance import TeamVaultPolicy
    from backend.app.models.organization import Customer

    cust_id = (
        await db.execute(sa_select(Customer.id).where(Customer.slug == workspace_id))
    ).scalar_one_or_none()
    if cust_id is None:
        return set()

    rows = (
        (
            await db.execute(
                sa_select(TeamVaultPolicy.allowed_tables).where(
                    TeamVaultPolicy.customer_id == cust_id,
                    TeamVaultPolicy.is_active == True,  # noqa: E712
                )
            )
        )
        .scalars()
        .all()
    )

    active: set[str] = set()
    for allowed in rows:
        if allowed:
            active.update(t.lower() for t in allowed)
    return active


async def _get_available_tables(
    engine: AsyncEngine,
    workspace_id: str,
    db: AsyncSession | None = None,
    team_id: str | None = None,
) -> list[dict]:
    """Discover available tables from Obsidian vault (multi-tenant).

    Returns list of dicts with: name, keywords, description (for semantic matching).

    When *db* and *team_id* are provided, a ``TeamVaultPolicy`` lookup is
    performed and the table list is pruned to only include tables listed in
    ``policy.allowed_tables``.  If no policy exists for the team the full
    vault table list is returned unchanged.
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
                domain_match = re.search(
                    r'(?:domain:\s*["\']?([^"\'\n]+)|## Domain\s*\n([^\n#]+))',
                    content,
                    re.IGNORECASE,
                )
                topic_match = re.search(
                    r'(?:topic:\s*["\']?([^"\'\n]+)|## Topic\s*\n([^\n#]+))', content, re.IGNORECASE
                )
                order_match = re.search(r"(?:order:\s*(\d+))", content, re.IGNORECASE)

                if domain_match:
                    domain = (domain_match.group(1) or domain_match.group(2)).strip()
                if topic_match:
                    topic = (topic_match.group(1) or topic_match.group(2)).strip()
                if order_match:
                    order = int(order_match.group(1).strip())

                # Extract insights as list
                insights_match = re.search(
                    r"(?:insights:\s*\n(.*?)---)", content, re.IGNORECASE | re.DOTALL
                )
                if insights_match:
                    lines = insights_match.group(1).strip().split("\n")
                    insights = [
                        line.strip().lstrip("-").strip()
                        for line in lines
                        if line.strip() and not line.strip().startswith("#")
                    ]

                # Extract keywords section
                kw_match = re.search(
                    r'(?:keywords:\s*["\']?([^"\'\n]+)|## Keywords\s*\n([^\n#]+))',
                    content,
                    re.IGNORECASE,
                )
                if kw_match:
                    keywords = (kw_match.group(1) or kw_match.group(2)).strip()

                # Extract description section
                desc_match = re.search(
                    r'(?:description:\s*["\']?([^"\'\n]+)|## Description\s*\n([^\n#]+))',
                    content,
                    re.IGNORECASE,
                )
                if desc_match:
                    description = (desc_match.group(1) or desc_match.group(2)).strip()

            except Exception:
                pass

            tables.append(
                {
                    "name": name,
                    "keywords": keywords,
                    "description": description,
                    "domain": domain,
                    "topic": topic,
                    "order": order,
                    "insights": insights,
                }
            )

        # ── TeamVaultPolicy pruning ───────────────────────────────────────
        if db is not None and team_id:
            try:
                policy = await _resolve_vault_policy(workspace_id, db, team_id)

                if policy and policy.allowed_tables:
                    allowed = {t.lower() for t in policy.allowed_tables}
                    original_count = len(tables)
                    tables = [t for t in tables if t["name"].lower() in allowed]
                    logger.info(
                        "Vault policy %r applied: pruned %d tables → %d allowed",
                        policy.name,
                        original_count,
                        len(tables),
                    )
            except Exception:
                # Intentional asymmetry: table-level pruning fails OPEN (logged,
                # full list returned) since over-exposing schema metadata is
                # low-risk, whereas RLS row-filtering (in _execute_sql) fails
                # CLOSED — it rejects the query rather than leak rows.
                logger.exception("Failed to enforce vault policy — returning full table list")

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
        table_pattern = r"^\s*\|\s*([A-Z_][A-Z0-9_]*)\s*\|\s*([A-Z0-9_()]+)\s*\|"
        for match in re.finditer(table_pattern, content, re.MULTILINE | re.IGNORECASE):
            col_name = match.group(1).strip()
            col_type = match.group(2).strip()
            # Skip header/separator rows
            if col_name.lower() in ("column", "---", "--------"):
                continue
            cols.append({"name": col_name, "type": col_type})

        # Also try to extract descriptions for better SQL generation context
        # Format: - **COLUMN_NAME**: Description text
        desc_map = {}
        for match in re.finditer(
            r"-\s*\*\*([A-Z_][A-Z0-9_]*)\*\*:\s*(.+?)(?:\n|$)", content, re.IGNORECASE
        ):
            desc_map[match.group(1).upper()] = match.group(2).strip()[
                :200
            ]  # Truncate long descriptions (keep enum lists / formulas)

        # Enrich columns with descriptions
        for col in cols:
            col["description"] = desc_map.get(col["name"].upper(), "")

        if cols:
            logger.debug("Parsed %d columns from vault %s", len(cols), table_name)
            return cols

        # Fallback: try legacy format **COLUMN**: TYPE (...)
        for match in re.finditer(
            r"\*\*([A-Z_][A-Z0-9_]*)\*\*:\s*([A-Z0-9_]+)", content, re.IGNORECASE
        ):
            cols.append({"name": match.group(1), "type": match.group(2), "description": ""})

        return cols if cols else [{"name": "unknown", "type": "VARCHAR2", "description": ""}]
    except Exception as e:
        logger.warning("Could not read vault %s: %s", table_name, e)
        return [{"name": "unknown", "type": "VARCHAR2", "description": ""}]


import contextlib  # noqa: E402

from backend.app.services.llm_resolver import ResolvedLLM  # noqa: E402


async def _generate_sql(
    question: str,
    engine: AsyncEngine,
    workspace_id: str,
    memory_context=None,
    history: list[dict] | None = None,
    db: AsyncSession | None = None,
    team_id: str | None = None,
    llm: ResolvedLLM | None = None,
) -> tuple[str, str, bool, dict]:
    """Generate SQL from a natural language question using Obsidian vault schema.

    Returns (sql, explanation, is_llm, token_usage).
    """
    tables = await _get_available_tables(engine, workspace_id, db=db, team_id=team_id)
    if not tables:
        return (
            "SELECT 'no_tables_found' AS info",
            "No database tables were found. Please connect a database first.",
            False,
            {},
        )

    # ── Semantic re-rank (Qdrant) before column fetch ───────────────────────
    # If the workspace has its vault embedded into Qdrant, ask which tables are
    # closest to the user's question and re-order `tables` accordingly. The
    # column-fetch limit below then picks the SEMANTICALLY relevant top-N
    # instead of whatever order the vault traversal returned. Falls back
    # silently to the existing order if Qdrant is down or the collection
    # doesn't exist yet (the next call auto-indexes).
    try:
        from backend.app.services.vault_retrieval import top_n_tables

        semantic_ranked = await top_n_tables(workspace_id, question, n=30)
        if semantic_ranked:
            rank_map = {name: i for i, (name, _) in enumerate(semantic_ranked)}
            tables.sort(key=lambda t: rank_map.get(t["name"], 999))
            logger.info(
                "Semantic re-rank applied for workspace=%s (top3=%s)",
                workspace_id,
                [r[0] for r in semantic_ranked[:3]],
            )
    except Exception as _rerank_err:
        logger.warning("Semantic rerank skipped: %s", _rerank_err)

    # Get columns for the top-N most relevant tables. Capped by
    # ARIA_MAX_TABLES_IN_LLM so the LLM schema slice and column-fetch agree.
    import os as _os_pipe

    _max_tables_for_columns = int(_os_pipe.environ.get("ARIA_MAX_TABLES_IN_LLM", "30"))
    table_columns: dict[str, list[dict]] = {}
    schema_info: list[str] = []
    for tbl in tables[:_max_tables_for_columns]:
        cols = await _get_table_columns(engine, tbl["name"], workspace_id)
        table_columns[tbl["name"]] = cols

    # ── Column-Level Security: hide denied columns from the LLM (prevention) ──
    # Drop every column listed in ``policy.deny_columns`` from the schema dict
    # BEFORE it is handed to the LLM (`generate_sql_with_llm` →
    # `_build_schema_context`) or the rule-based generator below.  A column the
    # model never sees cannot be SELECTed or referenced.  Defense-in-depth (a
    # result post-filter for `SELECT *` / aliases) lives in `_execute_sql`.
    # Guard matches Step 2 in `_execute_sql` (db + workspace): a team-less
    # request must still resolve the customer-wide-default policy
    # (``team_id IS NULL``) so its ``deny_columns`` are pruned, not leaked.
    if db is not None and workspace_id:
        cls_policy = await _resolve_vault_policy(workspace_id, db, team_id)
        deny_columns = getattr(cls_policy, "deny_columns", None) if cls_policy else None
        if deny_columns:
            from backend.app.query.cls import strip_denied_columns_from_schema

            table_columns = strip_denied_columns_from_schema(table_columns, deny_columns)

    for tbl in tables[:_max_tables_for_columns]:
        cols = table_columns.get(tbl["name"], [])
        col_str = ", ".join(f"{c['name']} ({c['type']})" for c in cols[:15])
        schema_info.append(f"  {tbl['name']}: {col_str}")

    # Generic SQL intent detection

    # Rule-based SQL generation based on question keywords and schema
    question_lower = question.lower()

    # Detect aggregations - with priority handling
    # "total" alone = count, "total X amount/revenue" = sum
    question_has_measure = any(
        w in question_lower
        for w in ["amount", "revenue", "sales", "sum", "value", "money", "balance", "topup"]
    )
    wants_sum = question_has_measure and any(
        w in question_lower for w in ["sum", "total", "revenue", "amount"]
    )
    wants_count = any(w in question_lower for w in ["count", "how many", "number of"]) or (
        "total" in question_lower and not question_has_measure
    )
    wants_avg = any(w in question_lower for w in ["average", "avg", "mean"])
    wants_group = any(w in question_lower for w in ["by", "per", "each", "group"])
    wants_top = any(w in question_lower for w in ["top", "highest", "most", "largest", "best"])
    wants_bottom = any(
        w in question_lower for w in ["bottom", "lowest", "least", "smallest", "worst"]
    )
    wants_trend = any(
        w in question_lower for w in ["trend", "over time", "monthly", "daily", "weekly", "by date"]
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
        if score > best_score or (
            score >= best_score - 2 and score > 0 and tbl_order < tables[0].get("order", 999)
        ):
            best_score = score
            best_table = tbl["name"]

            # Update the top table properties for later comparison if needed
            # We move the best_table to the front of the list virtually by tracking its order
            if tbl_order < tables[0].get("order", 999):
                tables[0] = tbl

    # If score is too low OR the question is structurally complex (MoM, bucket,
    # compare, growth, JOIN, subquery, window), forward to LLM. The old rule-based
    # path picks ONE table by keyword overlap and slaps SUM(first_numeric) GROUP BY
    # date on it — fine for "total sales by month", wrong for anything analytical.
    # Threshold + complex-question gate are env-configurable so we can tune without
    # a code change.
    import os as _os

    from backend.app.query.llm_sql import generate_sql_with_llm, is_complex_query

    keyword_threshold = int(_os.environ.get("ARIA_KEYWORD_SCORE_THRESHOLD", "30"))
    is_complex = is_complex_query(question)
    force_llm = best_score < keyword_threshold or is_complex
    if force_llm:
        logger.info(
            "Delegating to LLM (score=%d, threshold=%d, complex=%s)",
            best_score,
            keyword_threshold,
            is_complex,
        )
        try:
            sql, explanation, token_usage = await generate_sql_with_llm(
                question=question,
                tables=tables,
                table_columns=table_columns,
                memory_context=memory_context,
                db_type="oracle",
                history=history,
                llm=llm,
                workspace_id=workspace_id,
            )
            return sql, explanation, True, token_usage
        except Exception as e:
            logger.warning("LLM SQL generation failed during fallback: %s", e)

    # ── Heuristic (Rule-based) Grouping Engine ────────────────────────────────
    logger.info(
        "Table matching: question='%s' -> best_table='%s' (score=%d)",
        question[:50],
        best_table,
        best_score,
    )

    # Build the SELECT clause.  Prefer the already-built (and CLS-pruned)
    # `table_columns` so denied columns stay hidden from the rule-based path
    # too; fall back to a fresh fetch only if the chosen table wasn't in the
    # first-10 schema slice above.
    columns = table_columns.get(best_table)
    if columns is None:
        columns = await _get_table_columns(engine, best_table, workspace_id)

    # Oracle + PostgreSQL numeric types
    numeric_types = (
        "integer",
        "numeric",
        "bigint",
        "double precision",
        "real",
        "float",
        "number",
        "int",
        "decimal",
        "binary_float",
        "binary_double",
    )
    # Oracle + PostgreSQL text types
    text_types = (
        "character varying",
        "text",
        "varchar",
        "char",
        "varchar2",
        "nvarchar2",
        "clob",
        "nclob",
        "long",
    )
    # Oracle + PostgreSQL date types
    date_types = (
        "date",
        "timestamp without time zone",
        "timestamp with time zone",
        "timestamptz",
        "timestamp",
        "datetime",
    )

    numeric_cols = [c for c in columns if c["type"].lower() in numeric_types]
    text_cols = [c for c in columns if c["type"].lower().split("(")[0] in text_types]
    date_cols = [c for c in columns if c["type"].lower().split("(")[0] in date_types]
    all_cols = columns

    # Smart column selection: match column names/descriptions to question keywords
    def _find_best_column(
        cols: list[dict], question_words: list[str], default_idx: int = 0
    ) -> dict:
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
            group_col = _find_best_column(text_cols, question_words)["name"]
            return (
                f"SELECT {group_col}, COUNT(*) AS count\nFROM {best_table}\n"
                f"GROUP BY {group_col}\nORDER BY count DESC\nLIMIT 50",
                f"Counting records grouped by {group_col} from the {best_table} table.",
                False,
                {},
            )
        return (
            f"SELECT COUNT(*) AS total_count FROM {best_table}",
            f"Counting all records in the {best_table} table.",
            False,
            {},
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
                    False,
                    {},
                )
            elif date_cols and any(
                w in question_lower for w in ["day", "daily", "by day", "by date"]
            ):
                date_col = _find_best_column(date_cols, question_words)["name"]
                return (
                    f"SELECT TRUNC({date_col}) AS day, SUM({measure}) AS total_{measure}\n"
                    f"FROM {best_table}\n"
                    f"GROUP BY TRUNC({date_col})\n"
                    f"ORDER BY day\n"
                    f"FETCH FIRST 100 ROWS ONLY",
                    f"Daily total of {measure} from {best_table}, grouped by {date_col}.",
                    False,
                    {},
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
                    False,
                    {},
                )
        return (
            f"SELECT SUM({measure}) AS total_{measure} FROM {best_table}",
            f"Total sum of {measure} from {best_table}.",
            False,
            {},
        )

    if wants_top and numeric_cols:
        measure = numeric_cols[0]["name"]
        label_col = (
            _find_best_column(text_cols, question_words)["name"]
            if text_cols
            else all_cols[0]["name"]
        )
        return (
            f"SELECT {label_col}, {measure}\nFROM {best_table}\nORDER BY {measure} DESC\nLIMIT 10",
            f"Top 10 records from {best_table} ranked by {measure}.",
            False,
            {},
        )

    if wants_bottom and numeric_cols:
        measure = numeric_cols[0]["name"]
        label_col = (
            _find_best_column(text_cols, question_words)["name"]
            if text_cols
            else all_cols[0]["name"]
        )
        return (
            f"SELECT {label_col}, {measure}\nFROM {best_table}\nORDER BY {measure} ASC\nLIMIT 10",
            f"Bottom 10 records from {best_table} ranked by {measure}.",
            False,
            {},
        )

    if wants_trend and date_cols and numeric_cols:
        date_col = date_cols[0]["name"]
        measure = numeric_cols[0]["name"]
        return (
            f"SELECT DATE_TRUNC('month', {date_col}) AS month, "
            f"SUM({measure}) AS total\nFROM {best_table}\n"
            f"GROUP BY month\nORDER BY month\nLIMIT 100",
            f"Monthly trend of {measure} from {best_table}.",
            False,
            {},
        )

    if wants_avg and numeric_cols:
        measure = numeric_cols[0]["name"]
        return (
            f"SELECT AVG({measure}) AS avg_{measure} FROM {best_table}",
            f"Average {measure} from {best_table}.",
            False,
            {},
        )

    # Default: select first few columns
    select_cols = ", ".join(c["name"] for c in all_cols[:5])
    return (
        f"SELECT {select_cols}\nFROM {best_table}\nLIMIT 50",
        f"Showing sample data from {best_table} (first 50 rows).",
        False,
        {},
    )


# ── SQL Execution ──────────────────────────────────────────────────────────


def _extract_invalid_column(error_msg: str) -> str | None:
    """Extracts the invalid column name from Oracle ORA-00904 error."""
    import re

    match = re.search(r'ORA-00904: (?:".*?"\\.)?"(.*?)": invalid identifier', error_msg)
    if match:
        return match.group(1)
    return None


def _get_relevant_columns(invalid_col: str, table_columns: dict) -> str:
    """Finds closely matching or semantically relevant column names from available tables."""
    import difflib

    all_cols = []
    for _t_name, cols in table_columns.items():
        all_cols.extend([c["name"] for c in cols])

    invalid_lower = invalid_col.lower()
    cols_lower = {c.lower(): c for c in all_cols}

    close_matches = difflib.get_close_matches(
        invalid_lower, list(cols_lower.keys()), n=5, cutoff=0.4
    )

    semantic_map = {
        "region": [
            "nationality",
            "city",
            "country",
            "location",
            "territory",
            "district",
            "address",
        ],
        "price": ["amount", "revenue", "cost", "fee", "billamount", "total"],
        "date": ["revenue_date", "logdate", "appdate", "created_at", "insert_date"],
        "user": ["subno", "subscriberid", "contrno", "accountid", "msisdn"],
        "phone": ["subno", "msisdn", "subscriberid"],
    }

    suggestions = [cols_lower[m] for m in close_matches]

    for key, mapped_cols in semantic_map.items():
        if key in invalid_lower or invalid_lower in key:
            for mc in mapped_cols:
                for col in cols_lower:
                    if mc in col and cols_lower[col] not in suggestions:
                        suggestions.append(cols_lower[col])

    unique_suggestions = list(dict.fromkeys(suggestions))[:5]
    if unique_suggestions:
        return (
            f"Did you mean one of these existing columns instead: {', '.join(unique_suggestions)}?"
        )
    return "Please only use columns that exist in the schema."


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

        pattern = r"\bLIMIT\s+(\d+)\s*$"
        match = re.search(pattern, sql, re.IGNORECASE | re.MULTILINE)
        if match:
            n = match.group(1)
            sql = re.sub(
                pattern, f"FETCH FIRST {n} ROWS ONLY", sql, flags=re.IGNORECASE | re.MULTILINE
            )

    elif db_type == DatabaseType.MSSQL:
        # For MSSQL, LIMIT must be replaced with TOP (simple cases only)
        # Complex cases with ORDER BY need OFFSET/FETCH
        import re

        pattern = r"\bLIMIT\s+(\d+)\s*$"
        match = re.search(pattern, sql, re.IGNORECASE | re.MULTILINE)
        if match:
            n = match.group(1)
            # Remove LIMIT clause
            sql = re.sub(pattern, "", sql, flags=re.IGNORECASE | re.MULTILINE)
            # Add TOP after SELECT
            sql = re.sub(r"^SELECT\b", f"SELECT TOP {n}", sql, count=1, flags=re.IGNORECASE)

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
    from backend.app.services.crypto import async_decrypt_password

    async with engine.connect() as conn:
        result = await conn.execute(
            sa_text("""
                SELECT c.id as customer_id, db_type, host, port, database, username, encrypted_password, max_row_limit
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
                    max_row_limit=1000,
                )
            raise ValueError(f"No DB config found for workspace: {workspace_id}")

        (
            customer_id,
            db_type_str,
            host,
            port,
            database,
            username,
            encrypted_password,
            max_row_limit,
        ) = row
        decrypted_password = await async_decrypt_password(
            encrypted_password, str(customer_id), conn
        )

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
        password=decrypted_password,
        max_row_limit=max_row_limit if max_row_limit is not None else 1000,
    )


@retry(
    retry=retry_if_exception_type(OperationalError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def verify_sql_security(
    sql: str, engine, workspace_id: str, db, team_id: str | None = None
) -> None:
    import re

    from backend.app.query.guards import verify_read_only_sql

    # 1. Read-only guard
    verify_read_only_sql(sql)

    # 2. App-Level Table RLS guard
    if workspace_id and db:
        all_tables = await _get_available_tables(engine, workspace_id, db=db, team_id=None)
        allowed_tables = await _get_available_tables(engine, workspace_id, db=db, team_id=team_id)

        allowed_names = {t["name"].lower() for t in allowed_tables}
        blocked_names = {
            t["name"].lower() for t in all_tables if t["name"].lower() not in allowed_names
        }

        sql_clean = re.sub(r"'[^']*'", "", sql).lower()
        words = set(re.findall(r"[a-z_][a-z0-9_]*", sql_clean))

        for b_table in blocked_names:
            if b_table in words:
                raise ValueError(
                    f"Security Exception: You do not have permission to query the table '{b_table}'."
                )


async def _execute_sql(
    sql: str,
    engine: AsyncEngine,
    workspace_id: str | None = None,
    db: AsyncSession | None = None,
    user_id: str | None = None,
    question: str | None = None,
    explanation: str | None = None,
    mem_trace: dict | None = None,
    team_id: str | None = None,
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
        db: Optional AsyncSession for audit logging (writes to data_audit_logs)
        user_id: Optional user ID string for audit logging

    Returns:
        List of dicts, each representing a row

    Raises:
        ValueError: If no DB config found or unsupported DB type
    """

    await verify_sql_security(sql, engine, workspace_id, db, team_id)

    # ── Fetch DB config once ─────────────────────────────────────────────
    # Both the RLS rewrite (dialect) and execution (below) need the customer's
    # DB config.  Each fetch opens a connection + decrypts the password, so we
    # fetch it a single time here and reuse it.  Guarded on ``workspace_id`` to
    # preserve the original behavior: the no-``workspace_id`` schema-query path
    # never fetched a config and must still execute against the metadata DB.
    config: DBConfig | None = None
    if workspace_id:
        config = await _get_db_config(engine, workspace_id)

    # ── Row-Level Security: structurally scope filtered tables ───────────
    # Enforced on the generated SQL itself (table → filtered-subquery rewrite
    # via sqlglot), NOT trusted to the LLM.  Runs after table-level security
    # (verify_sql_security) and before any dialect transformation.  Fails
    # closed: if a filtered table cannot be safely rewritten, the query is
    # rejected rather than executed unfiltered.
    # Column-Level Security deny-list, resolved once here and reused for the
    # result post-filter (defense-in-depth) at the row-return path below.
    # ── Resolve customer / user UUIDs for audit logging ──────────────────
    # Resolved up-front so the RLS-applied governance entry (written right after
    # the rewrite below) and the query/CLS entries all share the same identities.
    _customer_uuid: _uuid.UUID | None = None
    _user_uuid: _uuid.UUID | None = None

    if db is not None and workspace_id:
        try:
            result = await db.execute(
                text("SELECT id FROM customers WHERE slug = :slug"),
                {"slug": workspace_id},
            )
            row = result.fetchone()
            if row:
                _customer_uuid = row[0]
        except Exception:
            logger.debug("Could not resolve customer UUID for audit: %s", workspace_id)

    if user_id:
        with contextlib.suppress(ValueError, AttributeError):
            _user_uuid = _uuid.UUID(user_id)

    deny_columns: dict | None = None
    if db is not None and workspace_id and config is not None:
        policy = await _resolve_vault_policy(workspace_id, db, team_id)
        row_filters = getattr(policy, "row_filters", None) if policy else None
        deny_columns = getattr(policy, "deny_columns", None) if policy else None
        if row_filters:
            from backend.app.query.rls import apply_row_filters

            dialect = _sqlglot_dialect(config.db_type.value)
            rewritten = apply_row_filters(sql, row_filters, dialect=dialect)
            # Governance audit: log ONLY when the rewrite actually changed the SQL
            # (apply_row_filters returns the input byte-for-byte on a no-op pass).
            if rewritten != sql and _customer_uuid is not None:
                from backend.app.query.sql_visibility import audit_rls_applied

                await audit_rls_applied(
                    AuditService(db),
                    customer_id=_customer_uuid,
                    user_id=_user_uuid,
                    row_filters=row_filters,
                )
            sql = rewritten

    from backend.app.db import execute_query

    # ── Audit helper ────────────────────────────────────────────────────
    async def _audit(
        success: bool, row_count: int = 0, error: str | None = None, mem_trace: dict | None = None
    ) -> None:
        """Write a query audit log entry if db + customer_uuid are available."""
        if db is None or _customer_uuid is None:
            return
        try:
            audit = AuditService(db)
            details_sql = sql[:2000] if sql else None

            # Pack trace info into details dict, then we'll intercept in AuditService or just pass it
            # AuditService.log_query takes kwargs, but wait, `mem_trace` isn't in log_query signature yet.
            # We can pass it via `explanation` as JSON or update log_query.
            # Let's pass it via log_event directly to inject custom `details`.

            details = {
                "sql": details_sql,
                "row_count": row_count,
                "question": question,
                "explanation": explanation,
                "success": success,
            }
            if mem_trace:
                details["mem_trace"] = mem_trace
            if error:
                details["error"] = error

            from backend.app.services.audit import AuditAction, AuditResourceType

            await audit.log_event(
                customer_id=_customer_uuid,
                user_id=_user_uuid,
                action=AuditAction.QUERY,
                resource_type=AuditResourceType.QUERY,
                details=details,
            )
        except Exception:
            logger.exception("Failed to write audit log")

    # If no workspace_id, try to execute against metadata DB (for schema queries)
    if not workspace_id:
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text(sql))
                rows = result.fetchall()
                if not rows:
                    await _audit(success=True, row_count=0, mem_trace=mem_trace)
                    return []
                columns = list(result.keys())
                rows_out = [dict(zip(columns, row, strict=False)) for row in rows]
                await _audit(success=True, row_count=len(rows_out), mem_trace=mem_trace)
                return rows_out
        except Exception as e:
            logger.exception("SQL execution failed: %s", sql[:200])
            await _audit(success=False, error=str(e), mem_trace=mem_trace)
            raise

    # Reuse the DB config fetched once above (workspace_id is guaranteed set
    # here — the no-workspace_id path returned earlier).  Avoids a second
    # connection + password-decrypt round-trip.
    assert config is not None  # narrows Optional for the type checker
    # Transform SQL for target dialect (LIMIT → FETCH FIRST for Oracle)
    transformed_sql = _transform_sql_for_dialect(sql, config.db_type)

    # Apply row limits
    import re

    row_limit = getattr(config, "max_row_limit", 1000)

    # Simple limit injection for safety if the query doesn't already have one
    if config.db_type.value == "oracle":
        if not re.search(r"FETCH\s+FIRST", transformed_sql, re.IGNORECASE):
            transformed_sql += f"\nFETCH FIRST {row_limit + 1} ROWS ONLY"
    else:
        if not re.search(r"\bLIMIT\b", transformed_sql, re.IGNORECASE) and not re.search(
            r"\bTOP\b", transformed_sql, re.IGNORECASE
        ):
            transformed_sql += f"\nLIMIT {row_limit + 1}"

    # ── Security Guard: read-only queries only (SELECT incl. WITH/CTE) ───────
    # Strip comments/whitespace first, then validate. A `WITH ... SELECT` CTE is
    # a valid read-only query (it starts with WITH, not SELECT) — the old
    # startswith("SELECT") check wrongly rejected it. We parse with sqlglot and
    # require a SINGLE statement that is a SELECT (CTEs parse as Select) with no
    # write/DDL nodes anywhere; if the parser is unavailable we fall back to a
    # lexical check that allows SELECT/WITH and scans for DML keywords.
    import re

    clean_sql_for_check = re.sub(r"--.*$", "", transformed_sql, flags=re.MULTILINE)
    clean_sql_for_check = re.sub(r"/\*.*?\*/", "", clean_sql_for_check, flags=re.DOTALL)
    clean_sql_for_check = clean_sql_for_check.strip()
    upper_sql = clean_sql_for_check.upper()

    dml_keywords = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "REPLACE",
        "MERGE",
        "GRANT",
        "REVOKE",
        "CREATE",
    ]

    async def _block(msg: str) -> None:
        logger.warning("Blocked non-read-only query: %s", transformed_sql[:200])
        await _audit(success=False, error=msg, mem_trace=mem_trace)
        raise ValueError(msg)

    parsed_ok = False
    try:
        import sqlglot
        from sqlglot import expressions as _sg

        dialect = _sqlglot_dialect(
            config.db_type.value if hasattr(config.db_type, "value") else str(config.db_type)
        )
        statements = [s for s in sqlglot.parse(clean_sql_for_check, read=dialect) if s is not None]
        write_nodes = (
            _sg.Insert,
            _sg.Update,
            _sg.Delete,
            _sg.Drop,
            _sg.Alter,
            _sg.Create,
            _sg.Merge,
            _sg.Command,
        )
        if len(statements) == 1 and isinstance(statements[0], _sg.Select):
            if statements[0].find(*write_nodes) is not None:
                await _block("Security Exception: Only read-only SELECT queries are permitted.")
            parsed_ok = True
        else:
            await _block("Security Exception: Only read-only SELECT queries are permitted.")
    except ValueError:
        raise  # propagate our own block
    except Exception as _parse_err:  # parser unavailable / unsupported syntax → lexical fallback
        logger.info("SQL guard falling back to lexical check: %s", _parse_err)

    if not parsed_ok:
        if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
            await _block("Security Exception: Only SELECT queries are permitted.")
        for kw in dml_keywords:
            if re.search(r"(?:^|;|\s+)" + kw + r"\s+", upper_sql):
                await _block(f"Security Exception: Query contains forbidden keyword '{kw}'.")

    logger.info(
        "Executing query on %s://%s:%d/%s",
        config.db_type.value,
        config.host,
        config.port,
        config.database,
    )

    try:
        import uuid

        from backend.app.db import explain_query
        from backend.app.worker.tasks import export_massive_query_to_minio

        # Sprint 14 Task 1: EXPLAIN Guard
        row_limit = getattr(config, "max_row_limit", 1000)
        UI_RENDER_THRESHOLD = 5000  # noqa: N806  # Triggers background job if > 5000 rows

        explain_res = await explain_query(transformed_sql, config)
        estimated_rows = explain_res.get("estimated_rows", 0)

        # If estimated rows massively exceed limits (e.g., 100x max_row_limit = 100,000 for a 1k limit), block execution
        if estimated_rows > row_limit * 100:
            error_msg = f"Security Exception: Query execution blocked. Estimated rows ({estimated_rows:,}) vastly exceed the allowed safe limit."
            logger.warning("Blocked massive query execution: Estimated %d rows", estimated_rows)
            await _audit(success=False, error=error_msg, mem_trace=mem_trace)
            raise ValueError(error_msg)

        # Sprint 14 Task 2: Background Data Offload
        if estimated_rows > UI_RENDER_THRESHOLD:
            logger.info(
                "Estimated rows (%d) exceeds UI threshold (%d). Offloading to background.",
                estimated_rows,
                UI_RENDER_THRESHOLD,
            )

            # Run the export and DELIVER the download link. Previously this was a
            # fire-and-forget asyncio.create_task whose returned URL was discarded —
            # the user was promised "a link when ready" that never arrived. We now
            # await it (the heavy query runs in a thread pool, so the event loop is
            # not blocked) and surface the URL in the response message.
            export_result = await export_massive_query_to_minio(
                sql=transformed_sql,
                db_config=config,
                conversation_id=str(uuid.uuid4())
                if not workspace_id
                else f"{workspace_id}_{user_id}",
                workspace_id=workspace_id or "default",
            )
            row_count = export_result.get("row_count", estimated_rows)
            await _audit(success=True, row_count=row_count, mem_trace=mem_trace)
            if export_result.get("status") == "success" and export_result.get("url"):
                raise ValueError(
                    f"Your query returned ~{row_count:,} rows — too large to display here. "
                    f"Download the full result (CSV, valid 3 days): {export_result['url']}"
                )
            raise ValueError(
                f"Query estimated ~{estimated_rows:,} rows (too large to display) but the "
                "background export failed — please narrow the query and retry."
            )

        result = await execute_query(transformed_sql, config)

        if len(result) > row_limit:
            logger.warning("Query exceeded tenant row limit (%d). Truncating result.", row_limit)
            result = result[:row_limit]
            explanation = (
                explanation
                + f"\n\n⚠️ Result was truncated to the maximum allowed limit of {row_limit} rows."
                if explanation
                else f"⚠️ Result was truncated to the maximum allowed limit of {row_limit} rows."
            )

        # ── Column-Level Security: defense-in-depth result post-filter ──────
        # Name-based strip of any denied column that reaches the result with its
        # original name (e.g. via `SELECT *`), as a backstop to the schema-level
        # CLS in `_generate_sql`.  This does NOT catch renamed aliases
        # (`SELECT revenue AS r`), but those can't occur once layer 1 fires.
        # Result rows are flat dicts and can't be mapped back to a source table,
        # so the union of all denied column names is stripped (case-insensitive).
        if deny_columns:
            from backend.app.query.cls import strip_denied_columns_from_rows

            # Determine which denied columns were ACTUALLY present in the result
            # (case-insensitive) so we only audit a genuine restriction, not a
            # no-op pass.  Build a per-table map of just the columns truly removed.
            present_keys = {str(k).lower() for r in result for k in r}
            removed_by_table = {
                table: [c for c in (cols or []) if str(c).lower() in present_keys]
                for table, cols in deny_columns.items()
            }
            removed_by_table = {t: cols for t, cols in removed_by_table.items() if cols}

            result = strip_denied_columns_from_rows(result, deny_columns)

            if removed_by_table and _customer_uuid is not None:
                from backend.app.query.sql_visibility import audit_cls_denied

                await audit_cls_denied(
                    AuditService(db),
                    customer_id=_customer_uuid,
                    user_id=_user_uuid,
                    deny_columns=removed_by_table,
                )

        await _audit(success=True, row_count=len(result), mem_trace=mem_trace)
        return result
    except Exception as e:
        logger.exception(
            "SQL execution failed on %s: %s",
            config.db_type.value,
            sql[:200],
        )
        await _audit(success=False, error=str(e), mem_trace=mem_trace)
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
    "give",
    "me",
    "a",
    "an",
    "the",
    "show",
    "make",
    "it",
    "as",
    "to",
    "chart",
    "charts",
    "graph",
    "plot",
    "please",
    "can",
    "you",
    "this",
    "that",
    "into",
    "draw",
    "display",
    "with",
    "of",
    "in",
    "view",
    "instead",
    "turn",
    "convert",
    "now",
    "pie",
    "bar",
    "line",
    "area",
    "scatter",
    "table",
    "tablo",
    "grid",
    "data",
    "color",
    "colour",
    "colors",
    "colours",
    "palette",
    "renk",
    "renkler",
    "rengini",
    "renkleri",
    "rengi",
    "renge",
    "paleti",
    "palet",
    "change",
    "different",
    "new",
    "style",
    "değiştir",
    "degistir",
    "yap",
    "çevir",
    "cevir",
}


_STYLE_PALETTES = [
    ["#4a9eed", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4"],
    ["#6366f1", "#14b8a6", "#f43f5e", "#eab308", "#a855f7", "#0ea5e9", "#84cc16"],
    ["#0f172a", "#334155", "#64748b", "#94a3b8", "#cbd5e1", "#475569", "#1e293b"],
    ["#e11d48", "#fb923c", "#facc15", "#4ade80", "#2dd4bf", "#60a5fa", "#c084fc"],
]


def _wants_color_change(question: str) -> bool:
    """True if the user asked to recolor/restyle (no new data)."""
    q = (question or "").lower()
    return any(w in q for w in ("palette", "palet", "color", "colour", "renk"))


def _next_palette(current) -> list:
    """Return a palette different from the current one (cycles the presets)."""
    try:
        idx = _STYLE_PALETTES.index(list(current)) if current else -1
    except ValueError:
        idx = -1
    return _STYLE_PALETTES[(idx + 1) % len(_STYLE_PALETTES)]


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
    """Run the chart builder pipeline: heuristic → render → MinIO artifact upload.

    Interactive chart is client-side Recharts (from chart_data). MinIO stores a
    static PNG + CSV artifact for history/export (no Plotly HTML — removed).

    Args:
        rows: Query result rows (list of dicts).
        question: Original natural language question.
        conversation_id: For MinIO key prefix.

    Returns:
        Dict with chart_data, chart_config, chart_url (PNG), csv_url, and errors.
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

    # ── Stage 1: Chart pipeline (heuristic proposer + render) ─────────────
    # The interactive chart is drawn client-side via Recharts from chart_data
    # (derived below). The MinIO artifact is a static PNG (Plotly/Kaleido) plus
    # the raw CSV — for history/export. Plotly HTML iframe rendering was removed
    # (see agents/chart_renderer), so we no longer produce/upload chart HTML.
    columns = list(rows[0].keys())
    from backend.app.core.config import get_settings as _get_settings

    _s = _get_settings()
    pipeline_result = run_chart_pipeline_sync(
        rows,
        columns=columns,
        question=question,
        # LLM-assisted chart-type selection routed through the LiteLLM proxy
        # (custom_llm_provider="openai" + api_base). Degrades gracefully to the
        # heuristic/table choice on any LLM/parse error, so it never blocks.
        use_llm=True,
        model_name=_s.llm_model,
        llm_base_url=_s.litellm_api_base,
        llm_api_key=_s.litellm_api_key or "sk-placeholder",
        render_formats=("png", "csv"),
    )

    chart_type = pipeline_result.config.chart_type.value
    # Honor an explicit user request ("give me a pie chart") over the heuristic pick.
    if forced_type:
        chart_type = forced_type
    png_bytes = pipeline_result.png_bytes
    csv_content = pipeline_result.csv_content or ""
    errors = pipeline_result.errors

    # ── Stage 2: Upload artifacts to MinIO (static PNG image + CSV data) ──
    chart_url = ""
    csv_url = ""

    try:
        store = ArtifactStore()
        prefix = f"conversations/{conversation_id}"

        if png_bytes:
            png_ref = store.upload_png(
                png_bytes,
                key_prefix=prefix,
                key=f"{prefix}/chart_{conversation_id}.png",
            )
            chart_url = png_ref.public_url() or png_ref.presigned_url(expires=86400)
            logger.info("chart_uploaded_to_minio", key=png_ref.key)

        if csv_content:
            csv_ref = store.upload_csv(
                csv_content,
                key_prefix=prefix,
                key=f"{prefix}/data_{conversation_id}.csv",
            )
            csv_url = csv_ref.public_url() or csv_ref.presigned_url(expires=86400)
    except Exception as exc:
        logger.warning("MinIO chart artifact upload failed: %s", exc)
        errors.append(f"MinIO upload failed: {exc}")
        # Chart still renders client-side from chart_data even if MinIO is down.

    # Derive recharts keys + JSON data for client-side rendering (ChartArea).
    # This replaces shipping multi-MB inline Plotly HTML to the browser.
    cfg = pipeline_result.config
    x_key = cfg.x.column or (columns[0] if columns else "")
    y_keys = (
        [cfg.y.column]
        if cfg.y.column
        else [
            c
            for c in columns
            if c != x_key
            and rows
            and isinstance(
                rows[0].get(c), (int, float, str)
            )  # str dahil (ör: "1,234.56" veya parse edilebilen stringler olabilir)
        ]
    )

    # If the LLM chart_builder specifically set Y to a metric, ensure we respect it
    if not cfg.y.column and y_keys:
        # Check if the query asks for revenue, count, etc., and force the appropriate column
        lower_q = question.lower()
        if ("revenue" in lower_q or "sum" in lower_q or "total" in lower_q) and not any(
            "revenue" in y.lower() for y in y_keys
        ):
            possible_ys = [
                c
                for c in columns
                if "revenue" in c.lower() or "total" in c.lower() or "amount" in c.lower()
            ]
            if possible_ys:
                y_keys = possible_ys
        elif "count" in lower_q:
            possible_ys = [c for c in columns if "count" in c.lower() or c.lower() == "count"]
            if possible_ys:
                y_keys = possible_ys

    # Force x_key and y_keys for known SQL structures (like the revenue by region grouping)
    # If group by contains 'month' and 'region', x_key should probably be 'month' and 'region' is grouped.
    # We set x_key dynamically based on typical time-series axes
    if "month" in columns and "region" in columns:
        x_key = "month"

    MAX_CHART_POINTS = 1000  # noqa: N806
    chart_data = _json_safe_rows(rows[:MAX_CHART_POINTS])

    # ── Multi-Series Pivot for Recharts ──────────────────────────────────────────
    # If the result has exactly 3 columns and one is intended as a category (e.g. Month, Region, Revenue)
    # we need to pivot it so Recharts can draw one bar/line per Region.
    if len(columns) == 3 and cfg.x and cfg.y:
        x_col = cfg.x.column
        y_col = cfg.y.column
        cat_cols = [c for c in columns if c not in (x_col, y_col)]
        if len(cat_cols) == 1:
            cat_col = cat_cols[0]
            pivoted_dict = {}
            unique_categories = set()

            for row in chart_data:
                x_val = row.get(x_col)
                cat_val = row.get(cat_col)
                y_val = row.get(y_col)

                if x_val is not None:
                    # Make sure X values are strings if they are dates, to match correctly
                    x_str = str(x_val)
                    if x_str not in pivoted_dict:
                        pivoted_dict[x_str] = {x_col: x_val}

                    if cat_val is not None:
                        cat_str = str(cat_val)
                        pivoted_dict[x_str][cat_str] = y_val
                        unique_categories.add(cat_str)

            chart_data = list(pivoted_dict.values())
            y_keys = sorted(unique_categories)
            x_key = x_col

    return {
        "chart_type": chart_type,
        "chart_html": "",  # interactive chart is client-side Recharts (chart_data); no server HTML
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
    team_id: str | None = None,
    sql_visible: bool = True,
) -> AsyncGenerator[dict, None]:
    """Process a natural language query and yield SSE events.

    Honours the per-user SQL-visibility invariant: when *sql_visible* is
    ``False`` every emitted event is passed through
    :func:`~backend.app.query.sql_visibility.gate_sse_event`, which omits the
    raw ``sql`` events, strips the raw SQL string from the ``sql_ready`` status
    event, and blanks a raw table grid — while still streaming the chart
    visualisation and the insight.  Defaults to ``True`` to preserve the
    behaviour of any caller that does not resolve visibility.
    """
    from backend.app.query.sql_visibility import gate_sse_event

    async for _event in _process_query_impl(
        redis=redis,
        engine=engine,
        request=request,
        workspace_id=workspace_id,
        user_id=user_id,
        team_id=team_id,
    ):
        gated = gate_sse_event(_event, sql_visible)
        if gated is not None:
            yield gated


async def _process_query_impl(
    redis: Redis,
    engine: AsyncEngine,
    request: QueryRequest,
    workspace_id: str,
    user_id: str,
    team_id: str | None = None,
) -> AsyncGenerator[dict, None]:
    """Inner pipeline generator (un-gated).  See :func:`process_query`.

    Pipeline stages:
    1. THINKING — validating input
    2. GENERATING_SQL — schema discovery + SQL generation
    3. SQL_READY — SQL preview available
    4. SQL_EXECUTING — executing query against database
    5. RENDERING_CHART — chart builder → Recharts JSON + MinIO PNG/CSV artifact
    6. COMPLETE — final response ready
    """
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
    _wants_color = _wants_color_change(request.question)
    if (
        _is_chart_type_only_request(request.question)
        and (_req_type or _wants_color)
        and _prev_assistant is not None
        and _prev_assistant.chart_data
    ):
        reused_sql = _prev_assistant.sql or ""
        cfg = dict(_prev_assistant.chart_spec or {})
        new_type = _req_type or cfg.get("type") or "bar"
        cfg["type"] = new_type
        if _wants_color:
            cfg["colors"] = _next_palette(cfg.get("colors"))
        note = (
            "Re-rendered the previous result with a new color palette."
            if _wants_color and not _req_type
            else f"Re-rendered the previous result as a {new_type} chart."
        )
        if reused_sql:
            yield {
                "event": "sql",
                "data": json.dumps({"sql": reused_sql, "explanation": note}),
            }
        yield {
            "event": "chart",
            "data": json.dumps(
                {
                    "chart_type": new_type,
                    "chart_data": _prev_assistant.chart_data,
                    "chart_url": _prev_assistant.chart_url or "",
                    "csv_url": "",
                    "chart_config": cfg,
                    "row_count": len(_prev_assistant.chart_data),
                },
                default=str,
            ),
        }
        await append_message(
            redis,
            workspace_id,
            cid,
            ConversationMessage(
                role="assistant",
                content=note,
                sql=reused_sql,
                chart_spec=cfg,
                chart_data=_prev_assistant.chart_data,
                chart_url=_prev_assistant.chart_url,
            ),
        )
        yield {
            "event": "status",
            "data": json.dumps(
                {
                    "status": QueryStatus.COMPLETE.value,
                    "message": "Chart updated",
                    "conversation_id": cid,
                }
            ),
        }
        yield {"event": "done", "data": json.dumps({"conversation_id": cid})}
        return

    # Stage 1.5: MEMORY_LOOKUP
    memory_svc = MemoryService.get_instance()
    mem_context = memory_svc.lookup(
        question=request.question,
        user_id=user_id,
        workspace_id=workspace_id,
        team_id=team_id,
    )
    prompt_context = mem_context.to_prompt_context()
    if prompt_context:
        logger.info("Found memory context for user %s: %s bytes", user_id, len(prompt_context))

    mem_trace = {
        "user_preferences_count": len(mem_context.user_preferences) if mem_context else 0,
        "team_conventions_count": len(mem_context.team_conventions) if mem_context else 0,
        "similar_queries_count": len(mem_context.similar_queries) if mem_context else 0,
        "raw": [
            r.get("memory", "")[:100] for r in (mem_context.raw_memories if mem_context else [])
        ],
    }

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
        from sqlalchemy import select as sa_select
        from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

        from backend.app.models.organization import Customer
        from backend.app.services.token import TokenService

        gen_kwargs: dict = {}
        token_usage: dict = {}

        async with _AsyncSession(engine) as sess:
            # ── Resolve customer UUID from workspace slug ──────────────────
            result = await sess.execute(sa_select(Customer.id).where(Customer.slug == workspace_id))
            customer_row = result.scalar_one_or_none()
            customer_uuid: _uuid.UUID | None = customer_row

            # Parse user and team UUIDs from string ids
            try:
                user_uuid = _uuid.UUID(user_id) if user_id else None
            except (ValueError, TypeError):
                user_uuid = None
            try:
                team_uuid = _uuid.UUID(team_id) if team_id else None
            except (ValueError, TypeError):
                team_uuid = None

            # ── Resolve LLM ────────────────────────────────────────────────
            from backend.app.services.llm_resolver import resolve_llm

            resolved_llm = await resolve_llm(workspace_id, sess, operation="sql_generation")
            insight_llm = await resolve_llm(workspace_id, sess, operation="insight")
            logger.info("Using LLM configuration: %s", resolved_llm)

            # ── Token quota enforcement ────────────────────────────────────
            token_svc = None
            if customer_uuid and user_uuid:
                try:
                    token_svc = TokenService(db=sess, redis=redis)
                    allowed = await token_svc.check_quota(
                        customer_id=customer_uuid,
                        user_id=user_uuid,
                        team_id=team_uuid,
                        session_id=cid,
                    )
                    if not allowed:
                        yield {
                            "event": "error",
                            "data": json.dumps(
                                {"error": "Daily token quota exceeded. Please try again tomorrow."}
                            ),
                        }
                        return
                except Exception:
                    # Fail CLOSED: a quota check that errors must DENY, not silently
                    # let the request through (which made the hard cap bypassable).
                    # Redis backs quotas AND conversations, so if it is down the app
                    # is already degraded — denying here loses little availability.
                    logger.exception("Token quota check failed — denying request (fail-closed)")
                    yield {
                        "event": "error",
                        "data": json.dumps(
                            {"error": "Unable to verify your usage quota right now. Please retry shortly."}
                        ),
                    }
                    return

            # ── Generate SQL ───────────────────────────────────────────────
            # Always pass the session so Step-1 CLS can resolve the
            # customer-wide-default policy even for team-less requests; team_id
            # may be None (the default policy is keyed on team_id IS NULL).
            gen_kwargs["db"] = sess
            gen_kwargs["team_id"] = team_id
            sql, explanation, is_llm, token_usage = await _generate_sql(
                request.question,
                engine,
                workspace_id,
                memory_context=mem_context,
                history=history,
                llm=resolved_llm,
                **gen_kwargs,
            )

            # Run security checks *before* exposing the SQL to the user
            await verify_sql_security(sql, engine, workspace_id, sess, team_id)

            # ── Record token usage ─────────────────────────────────────────
            if token_svc and token_usage and customer_uuid and user_uuid:
                total = token_usage.get("prompt_tokens", 0) + token_usage.get(
                    "completion_tokens", 0
                )
                if total > 0:
                    try:
                        await token_svc.record_usage(
                            customer_id=customer_uuid,
                            user_id=user_uuid,
                            team_id=team_uuid,
                            session_id=cid,
                            model=token_usage.get("model", "unknown"),
                            prompt_tokens=token_usage.get("prompt_tokens", 0),
                            completion_tokens=token_usage.get("completion_tokens", 0),
                        )
                    except Exception:
                        logger.exception("Failed to record token usage")
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
        from sqlalchemy.ext.asyncio import AsyncSession as _ExecSession

        async with _ExecSession(engine) as sess:
            rows = await _execute_sql(
                sql,
                engine,
                workspace_id=workspace_id,
                db=sess,
                user_id=user_id,
                question=request.question,
                explanation=explanation,
                mem_trace=mem_trace,
                team_id=team_id,
            )
    except Exception as e:
        logger.warning("SQL execution failed. Attempting LLM self-correction. Error: %s", e)
        # Stage 4.1: SELF_CORRECTION
        yield {
            "event": "status",
            "data": json.dumps(
                {
                    "status": "correcting_sql",
                    "message": "Syntax error detected. Attempting to self-correct SQL...",
                }
            ),
        }
        try:
            # Re-generate SQL with error feedback
            error_str = str(e)
            correction_prompt = f"The previous SQL query failed with this error: {error_str}. "

            invalid_col = _extract_invalid_column(error_str)
            if invalid_col:
                correction_prompt += f"\nThe column '{invalid_col}' does not exist. NEVER invent or guess columns. If the exact data is missing, use the closest relevant existing column."
            else:
                correction_prompt += "Please fix the syntax and ensure you ONLY use tables and columns defined in the schema."

            history.append({"question": correction_prompt, "sql": sql})
            sql, explanation, is_llm, token_usage = await _generate_sql(
                request.question,
                engine,
                workspace_id,
                memory_context=mem_context,
                history=history,
                llm=resolved_llm,
                **gen_kwargs,
            )

            # Run security checks *before* exposing the SQL to the user
            await verify_sql_security(sql, engine, workspace_id, sess, team_id)
            yield {
                "event": "sql",
                "data": json.dumps(
                    {"sql": sql, "explanation": explanation + "\n\n(Self-corrected)"}
                ),
            }
            # Re-execute the corrected SQL
            async with _ExecSession(engine) as sess:
                rows = await _execute_sql(
                    sql,
                    engine,
                    workspace_id=workspace_id,
                    db=sess,
                    user_id=user_id,
                    question=request.question,
                    explanation=explanation,
                    mem_trace=mem_trace,
                    team_id=team_id,
                )
        except Exception as retry_e:
            logger.exception("SQL self-correction failed")
            yield {
                "event": "error",
                "data": json.dumps(
                    {"error": f"Query execution failed after correction attempt: {retry_e}"}
                ),
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

    # Stage 5.2: INSIGHT_GENERATION
    yield {
        "event": "status",
        "data": json.dumps(
            {
                "status": "generating_insight",
                "message": "Generating insights and suggestions...",
            }
        ),
    }

    summary = ""
    suggestions = []
    if len(rows) > 0 and sql != "SELECT 'no_tables_found' AS info":
        from backend.app.query.llm_insight import generate_insight_and_suggestions
        from backend.app.services.workspace_language import get_workspace_language

        # Pass a sample of rows to the insight generator to avoid massive prompt context
        sample_rows = _json_safe_rows(rows[:10])
        language = await get_workspace_language(workspace_id)
        insight_res = await generate_insight_and_suggestions(
            request.question, sql, sample_rows, llm=insight_llm, language=language
        )
        summary = insight_res.get("summary", "")
        suggestions = insight_res.get("suggestions", [])

        if summary or suggestions:
            yield {
                "event": "insight",
                "data": json.dumps({"summary": summary, "suggestions": suggestions}),
            }

    # Stage 5.5: STORE_MEMORY
    # Store query cache + detect user preferences from successful queries
    if len(rows) > 0 and sql != "SELECT 'no_tables_found' AS info":
        try:
            # Extract table name from SQL for better context
            table_match = re.search(r"\bFROM\s+(\w+)", sql, re.IGNORECASE)
            table_name = table_match.group(1) if table_match else "multiple_tables"

            # Extract columns used from SQL
            select_match = re.search(r"SELECT\s+(.+?)\s+FROM", sql, re.IGNORECASE | re.DOTALL)
            columns_used = []
            if select_match:
                cols_str = select_match.group(1)
                # Extract column names (simplified)
                columns_used = re.findall(r"\b([A-Z_][A-Z0-9_]*)\b", cols_str, re.IGNORECASE)

            # 1. Store query cache (existing)
            memory_svc.store_query(
                question=request.question,
                sql=sql,
                table=table_name,
                user_id=user_id,
                workspace_id=workspace_id,
                row_count=len(rows),
            )
            logger.info("Stored query cache for user %s", user_id)

            # 2. Detect and store user preferences from successful patterns
            preference = _extract_preference_from_successful_query(
                question=request.question,
                sql=sql,
                table=table_name,
                columns_used=columns_used,
            )
            if preference:
                memory_svc.store_user_preference(
                    preference=preference,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    metadata={"table": table_name, "columns": columns_used[:5]},
                )
                logger.info("Stored user preference: %s", preference[:50])

            # 3. Detect explicit chart preference
            chart_pref = _detect_chart_preference(request.question)
            if chart_pref:
                pref_text = f"User prefers {chart_pref['value']} charts for data visualization"
                memory_svc.store_user_preference(
                    preference=pref_text,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    metadata={"chart_type": chart_pref["value"]},
                )
                logger.info("Stored chart preference: %s", chart_pref["value"])

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
        summary=summary,
        suggestions=suggestions,
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
