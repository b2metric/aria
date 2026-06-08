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
from typing import Any

import httpx

from backend.app.core.config import get_settings
from backend.app.memory.service import MemoryContext

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an expert SQL query generator for Oracle databases. 
Generate ONLY the SQL query, no explanations.

RULES:
1. Use Oracle SQL syntax (TRUNC for dates, FETCH FIRST N ROWS ONLY for limits, NVL for null handling)
2. Always include reasonable limits (default: FETCH FIRST 100 ROWS ONLY)
3. Use proper date truncation: TRUNC(date_col, 'MM') for monthly, TRUNC(date_col) for daily
4. For aggregations, always include GROUP BY
5. Order results logically (by date ASC for time series, by metric DESC for rankings)
6. Use table aliases for readability in JOINs
7. NEVER use semicolons at the end
8. Return ONLY the SQL, no markdown, no explanations"""


def _build_schema_context(tables: list[dict], table_columns: dict[str, list[dict]]) -> str:
    """Build schema context string for LLM prompt."""
    parts = ["Available tables and columns:"]
    for tbl in tables[:10]:  # Limit to 10 tables
        name = tbl["name"]
        cols = table_columns.get(name, [])
        col_str = ", ".join(
            f"{c['name']} ({c['type']})" 
            for c in cols[:20]  # Limit columns
        )
        parts.append(f"\n{name}: {col_str}")
        if tbl.get("description"):
            parts.append(f"  Description: {tbl['description'][:100]}")
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


async def generate_sql_with_llm(
    question: str,
    tables: list[dict],
    table_columns: dict[str, list[dict]],
    memory_context: MemoryContext | None = None,
    db_type: str = "oracle",
    history: list[dict] | None = None,
) -> tuple[str, str]:
    """Generate SQL using LLM.
    
    Args:
        question: Natural language question
        tables: List of table dicts with name, keywords, description
        table_columns: Dict mapping table names to column lists
        memory_context: Optional memory context for better accuracy
        db_type: Database type (oracle, postgresql, mysql, mssql)
        
    Returns:
        Tuple of (sql, explanation)
    """
    settings = get_settings()
    
    # Build the prompt
    schema_ctx = _build_schema_context(tables, table_columns)
    memory_ctx = _build_memory_context(memory_context)
    history_ctx = _build_history_context(history)

    user_prompt = f"""Database type: {db_type.upper()}

{schema_ctx}
{memory_ctx}
{history_ctx}
User question: {question}

Generate the SQL query:"""

    # Call LiteLLM proxy
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.litellm_api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.litellm_api_key or 'sk-placeholder'}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": settings.llm_temperature,
                    "max_tokens": settings.llm_max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            
        sql = data["choices"][0]["message"]["content"].strip()
        
        # Clean up the SQL
        sql = _clean_sql(sql)
        
        # Generate explanation
        explanation = f"LLM-generated query based on: {question[:100]}"
        
        logger.info("LLM SQL generation successful: %s", sql[:100])
        return sql, explanation
        
    except httpx.HTTPStatusError as e:
        logger.error("LLM API error: %s - %s", e.response.status_code, e.response.text[:200])
        raise ValueError(f"LLM API error: {e.response.status_code}") from e
    except Exception as e:
        logger.error("LLM SQL generation failed: %s", e)
        raise ValueError(f"LLM SQL generation failed: {e}") from e


def _clean_sql(sql: str) -> str:
    """Clean up LLM-generated SQL."""
    # Remove markdown code blocks
    sql = re.sub(r'^```sql\s*', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'^```\s*$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'```$', '', sql)
    
    # Remove trailing semicolons
    sql = sql.rstrip(';').strip()
    
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
        r'\b(join|combine|merge|along with|together with|and their|with the)\b',
        r'\bfrom\s+\w+\s+and\s+\w+\b',
        
        # Subqueries
        r'\b(greater than average|more than average|above average|below average)\b',
        r'\b(where .+ is .+ than)\b',
        r'\b(who have|that have|which have)\b',
        
        # Window functions
        r'\b(running total|cumulative|rank|ranking|previous|next|lag|lead)\b',
        r'\b(year over year|month over month|yoy|mom|growth rate)\b',
        r'\b(moving average|rolling)\b',
        
        # Complex date
        r'\b(last quarter|this quarter|previous quarter|q[1-4]\s+\d{4})\b',
        r'\b(fiscal year|fy\d{2,4})\b',
        r'\b(between .+ and .+ date)\b',
        
        # Comparisons
        r'\b(compare|comparison|vs|versus|difference between)\b',
        r'\b(correlation|relationship between)\b',
        
        # Percentages and ratios
        r'\b(percentage of|percent of|ratio of|proportion)\b',
        r'\b(share of|contribution)\b',
    ]
    
    for pattern in complex_patterns:
        if re.search(pattern, question_lower):
            logger.debug("Complex query detected (pattern: %s): %s", pattern, question[:50])
            return True
    
    return False
