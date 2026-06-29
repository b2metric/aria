"""TIER 3 item 23 — QueryTrace: the per-turn debug trace persisted on the
assistant message and surfaced in the /admin/conversations debug screen.

``build_query_trace`` is a pure assembler so the trace's shape/redaction is
unit-tested without driving the whole NL→SQL pipeline.
"""

from __future__ import annotations

from backend.app.query.trace import build_query_trace


def test_build_query_trace_full_shape():
    mem_trace = {
        "user_preferences_count": 2,
        "team_conventions_count": 1,
        "similar_queries_count": 3,
        "raw": ["pref: prefers bar charts", "convention: revenue = net"],
    }
    trace = build_query_trace(
        mem_trace=mem_trace,
        model="gemini-reasoner",
        model_source="customer_byok",
        row_count=42,
        sql="SELECT region, revenue FROM sales",
    )
    assert trace["model"] == "gemini-reasoner"
    assert trace["model_source"] == "customer_byok"
    assert trace["row_count"] == 42
    assert trace["sql_generated"] is True
    assert trace["memory"] == {
        "user_preferences": 2,
        "team_conventions": 1,
        "similar_queries": 3,
        "snippets": ["pref: prefers bar charts", "convention: revenue = net"],
    }


def test_build_query_trace_handles_no_memory_and_no_sql():
    trace = build_query_trace(
        mem_trace=None, model=None, model_source=None, row_count=0, sql=None
    )
    assert trace["model"] is None
    assert trace["row_count"] == 0
    assert trace["sql_generated"] is False
    assert trace["memory"] is None


def test_build_query_trace_is_json_safe():
    """The trace is persisted as JSON on the conversation message, so every
    value must be a JSON-native type (no objects, no bytes)."""
    import json

    trace = build_query_trace(
        mem_trace={
            "user_preferences_count": 0,
            "team_conventions_count": 0,
            "similar_queries_count": 0,
            "raw": [],
        },
        model="m",
        model_source="default",
        row_count=1,
        sql="SELECT 1",
    )
    # Round-trips without a custom encoder.
    assert json.loads(json.dumps(trace)) == trace
