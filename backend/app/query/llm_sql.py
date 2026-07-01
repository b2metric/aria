"""LLM-based SQL generation service using LiteLLM.

Handles complex queries that rule-based generation can't handle:
- Multi-table JOINs
- Subqueries
- Window functions
- Complex WHERE conditions
- Date range filters with natural language

Uses memory context from Mem0 to improve accuracy.
"""

from __future__ import annotations

import logging
import re

import httpx

from backend.app.core.config import get_settings
from backend.app.memory.service import MemoryContext

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an expert SQL query generator for Oracle databases. 
Generate ONLY the SQL query, no explanations.

RULES:
1. Use Oracle SQL syntax (TRUNC for dates, FETCH FIRST N ROWS ONLY for limits, NVL for null handling)
2. Do NOT add your own row limit — the system applies the row limit automatically.
   Only add `FETCH FIRST N ROWS ONLY` when the user EXPLICITLY asks for a specific
   count ("top 10", "first 50", "5 largest"). Otherwise return the query unlimited.
3. Use proper date truncation: TRUNC(date_col, 'MM') for monthly, TRUNC(date_col) for daily
4. Add GROUP BY / date bucketing ONLY when the user asks for a breakdown or a trend
   (over time, by month, daily, per X, "trend"). For a single aggregate — a ratio,
   total, count, or average with no breakdown requested — return a SCALAR: no GROUP BY
   and no TRUNC(date) bucketing.
5. Order results logically (by date ASC for time series, by metric DESC for rankings)
6. Use table aliases for readability in JOINs
7. NEVER use semicolons at the end
8. Return ONLY the SQL, no markdown, no explanations
9. Use ONLY tables and columns that appear in the provided schema. NEVER invent,
   assume, or guess a table/column that is not explicitly listed — querying a
   non-existent object fails with ORA-00942. Likewise, use ONLY the column VALUES /
   enums shown in the column descriptions — never invent status codes or category
   values (e.g. cache statuses, role names) that are not documented there.
10. For metrics/aggregations (revenue, amount, balance, counts, totals, trends),
    the source MUST be a FACT table (name starting with 'fct_'). Use dimension
    tables ('dim_*') ONLY to look up descriptive attributes via a JOIN, never as
    the sole source of a numeric metric.
11. If the question names a specific tier/segment/category/label, you MUST filter on
    it. Map the natural-language label to the documented coded column value from the
    schema descriptions (e.g. an "Edge tier" → the matching SERVER_ROLE value)."""


def _build_schema_context(tables: list[dict], table_columns: dict[str, list[dict]]) -> str:
    """Build schema context string for the LLM prompt.

    Includes each column's description (which carries the documented enum values and
    coded categories, e.g. SERVER_ROLE = Node/Mcache/Feda) so the model can scope
    filters to a named segment and never has to guess a value.
    """
    import os

    # ARIA_MAX_TABLES_IN_LLM caps the schema slice handed to the LLM. The old
    # hard-coded 10 was tight for vaults with 20-40 tables (e.g. STC), causing
    # the correct table to be dropped from context before the model ever saw it.
    # Bump to 30 by default; tune higher only if prompts become token-heavy.
    max_tables = int(os.environ.get("ARIA_MAX_TABLES_IN_LLM", "30"))
    parts = ["Available tables and columns:"]
    for tbl in tables[:max_tables]:
        name = tbl["name"]
        cols = table_columns.get(name, [])
        parts.append(f"\n{name}:")
        if tbl.get("description"):
            parts.append(f"  Description: {tbl['description'][:200]}")
        for c in cols[:20]:  # Limit columns
            desc = (c.get("description") or "").strip()
            line = f"  - {c['name']} ({c['type']})"
            if desc:
                line += f" — {desc}"
            parts.append(line)
        if tbl.get("keywords"):
            parts.append(f"  Keywords: {tbl['keywords'][:100]}")
    return "\n".join(parts)


def _build_memory_context(memory: MemoryContext | None) -> str:
    """Build memory context string for LLM prompt."""
    if not memory or not memory.has_context:
        return ""
    return f"\nRelevant context from past queries:\n{memory.to_prompt_context()}"


def _build_history_context(history: list[dict] | None) -> str:
    """Render recent conversation turns (+ last SQL) so the LLM can do follow-ups.

    history: list of {"question": str, "sql": str | None} ordered oldest→newest.
    """
    if not history:
        return ""
    lines = [
        "Conversation so far (most recent last). If the user is asking to MODIFY the",
        "previous result — change the grouping/filter/date range/chart type, 'also ...',",
        "'instead ...', 'as a pie chart', etc. — START FROM the previous SQL and adjust",
        "it. Stay on the SAME tables/columns unless the user clearly asks for new data.",
    ]
    for turn in history[-3:]:
        q = (turn.get("question") or "").strip()
        sql = (turn.get("sql") or "").strip()
        if q:
            lines.append(f"- User asked: {q}")
        if sql:
            lines.append(f"  SQL used: {sql}")
    return "\n".join(lines) + "\n"


def _build_reference_context(
    workspace_id: str | None, tables: list[dict], top_k: int = 3, max_chars: int = 7000
) -> str:
    """Pull the Domain Mapping + Example Queries md sections for the top-ranked
    tables and render them as few-shot guidance. This is what carries the
    CANONICAL verified queries (e.g. the recharge MoM bucket query) into the LLM
    prompt — without it the model only sees columns and re-invents wrong SQL.
    """
    if not workspace_id:
        return ""
    import pathlib

    from backend.app.core.config import get_settings
    from backend.app.services.vault_md import read_sections, resolve_vault_file

    vault_dir = pathlib.Path(get_settings().vault_base_path) / workspace_id / "tables"
    if not vault_dir.exists():
        return ""

    blocks: list[str] = []
    used = 0
    for tbl in tables[:top_k]:
        fp = resolve_vault_file(vault_dir, tbl["name"])
        guidance = read_sections(fp, ["Domain Mapping", "Example Queries"])
        if guidance:
            block = f"\n--- Guidance for {tbl['name']} ---\n{guidance}"
            blocks.append(block)
            used += len(block)
            if used >= max_chars:
                break
    if not blocks:
        return ""
    return (
        "\nReference domain mappings and VERIFIED example queries for the most relevant "
        "tables. Strongly PREFER adapting these example queries (correct table, columns, "
        "bucket logic, entity grain) over writing SQL from scratch:\n" + "\n".join(blocks)
    )


async def generate_sql_with_llm(
    question: str,
    tables: list[dict],
    table_columns: dict[str, list[dict]],
    memory_context: MemoryContext | None = None,
    db_type: str = "oracle",
    history: list[dict] | None = None,
    llm=None,
    workspace_id: str | None = None,
) -> tuple[str, str, dict]:
    """Generate SQL using LLM.

    Args:
        question: Natural language question
        tables: List of table dicts with name, keywords, description
        table_columns: Dict mapping table names to column lists
        memory_context: Optional memory context for better accuracy
        db_type: Database type (oracle, postgresql, mysql, mssql)
        llm: Optional ResolvedLLM (model/api_base/api_key/temperature/max_tokens).
            When provided, its values win over ``settings`` — this is how BYOK and
            per-operation ("sql_generation") model routing reach SQL generation.

    Returns:
        Tuple of (sql, explanation, token_usage) where token_usage is a dict
        with keys: prompt_tokens, completion_tokens, model.
    """
    settings = get_settings()

    # Resolve effective model/credentials: ResolvedLLM wins, else platform settings.
    model = (llm.model if llm and llm.model else None) or settings.llm_model
    api_base = (llm.api_base if llm and llm.api_base else None) or settings.litellm_api_base
    api_key = (
        (llm.api_key if llm and llm.api_key else None)
        or settings.litellm_api_key
        or "sk-placeholder"
    )
    temperature = (
        llm.temperature if llm and llm.temperature is not None else settings.llm_temperature
    )
    max_tokens = llm.max_tokens if llm and llm.max_tokens is not None else settings.llm_max_tokens

    # Build the prompt
    schema_ctx = _build_schema_context(tables, table_columns)
    reference_ctx = _build_reference_context(workspace_id, tables)
    join_keys_ctx = ""
    if workspace_id:
        try:
            from backend.app.services.vault_join_keys import build_join_keys_context

            join_keys_ctx = build_join_keys_context(workspace_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("join-keys context unavailable: %s", e)
    memory_ctx = _build_memory_context(memory_context)
    history_ctx = _build_history_context(history)

    user_prompt = f"""Database type: {db_type.upper()}

{schema_ctx}
{join_keys_ctx}
{reference_ctx}
{memory_ctx}
{history_ctx}
User question: {question}

Generate the SQL query:"""

    # Call LiteLLM proxy
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            # LiteLLM reports the authoritative USD cost in a response header (proxy over HTTP
            # doesn't put it in the JSON body). Carry it forward for metering (Task 13).
            response_cost = response.headers.get("x-litellm-response-cost")

        sql = data["choices"][0]["message"]["content"].strip()

        # Clean up the SQL
        sql = _clean_sql(sql)

        # Generate explanation
        explanation = f"LLM-generated query based on: {question[:100]}"

        # Extract token usage from the response
        usage = data.get("usage", {})
        token_usage = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "model": model,
            "_response_cost": response_cost,
        }

        logger.info(
            "LLM SQL generation successful: %s (tokens: prompt=%d, completion=%d)",
            sql[:100],
            token_usage["prompt_tokens"],
            token_usage["completion_tokens"],
        )
        return sql, explanation, token_usage

    except httpx.HTTPStatusError as e:
        logger.error("LLM API error: %s - %s", e.response.status_code, e.response.text[:200])
        raise ValueError(f"LLM API error: {e.response.status_code}") from e
    except Exception as e:
        logger.error("LLM SQL generation failed: %s", e)
        raise ValueError(f"LLM SQL generation failed: {e}") from e


def _clean_sql(sql: str) -> str:
    """Clean up LLM-generated SQL."""
    # Remove markdown code blocks
    sql = re.sub(r"^```sql\s*", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"^```\s*$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"```$", "", sql)

    # Remove trailing semicolons
    sql = sql.rstrip(";").strip()

    # Remove any leading/trailing whitespace
    sql = sql.strip()

    return sql


def is_complex_query(question: str) -> bool:
    """Determine if a question requires LLM-based SQL generation.

    Complex queries include:
    - JOINs (explicit or implicit via "with", "and their", "along with")
    - Subqueries ("where X is greater than average")
    - Window functions ("running total", "rank", "previous")
    - Complex date filters ("last quarter", "year over year")
    - Comparisons ("compare", "vs", "difference between")
    """
    question_lower = question.lower()

    complex_patterns = [
        # JOINs
        r"\b(join|combine|merge|along with|together with|and their|with the)\b",
        r"\bfrom\s+\w+\s+and\s+\w+\b",
        # Subqueries
        r"\b(greater than average|more than average|above average|below average)\b",
        r"\b(where .+ is .+ than)\b",
        r"\b(who have|that have|which have)\b",
        # Window functions
        r"\b(running total|cumulative|rank|ranking|previous|next|lag|lead)\b",
        r"\b(year over year|month over month|yoy|mom|growth rate)\b",
        r"\b(moving average|rolling)\b",
        # Complex date
        r"\b(last quarter|this quarter|previous quarter|q[1-4]\s+\d{4})\b",
        r"\b(fiscal year|fy\d{2,4})\b",
        r"\b(between .+ and .+ date)\b",
        # Comparisons
        r"\b(compare|comparison|vs|versus|difference between)\b",
        r"\b(correlation|relationship between)\b",
        # Percentages and ratios
        r"\b(percentage of|percent of|ratio of|proportion)\b",
        r"\b(share of|contribution)\b",
    ]

    for pattern in complex_patterns:
        if re.search(pattern, question_lower):
            logger.debug("Complex query detected (pattern: %s): %s", pattern, question[:50])
            return True

    return False
