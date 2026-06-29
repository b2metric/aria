"""QueryTrace assembly (TIER 3 item 23).

A QueryTrace is a small, JSON-safe debug record attached to each assistant
message: which model produced it, how many rows it returned, whether SQL was
generated, and what memory context influenced generation. It powers the
``/admin/conversations`` debug screen (Sprint 9 scope) without leaking anything
heavier than short memory snippets.
"""

from __future__ import annotations

from typing import Any


def build_query_trace(
    *,
    mem_trace: dict | None,
    model: str | None,
    model_source: str | None,
    row_count: int,
    sql: str | None,
) -> dict[str, Any]:
    """Assemble the per-turn debug trace persisted on the assistant message.

    *mem_trace* is the pipeline's memory-context summary (counts + short raw
    snippets). All outputs are JSON-native so the trace serializes onto the
    Redis-backed conversation without a custom encoder.
    """
    memory: dict[str, Any] | None = None
    if mem_trace is not None:
        memory = {
            "user_preferences": mem_trace.get("user_preferences_count", 0),
            "team_conventions": mem_trace.get("team_conventions_count", 0),
            "similar_queries": mem_trace.get("similar_queries_count", 0),
            "snippets": list(mem_trace.get("raw", []) or []),
        }
    return {
        "model": model,
        "model_source": model_source,
        "row_count": int(row_count or 0),
        "sql_generated": bool(sql),
        "memory": memory,
    }
