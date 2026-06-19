"""The SQL-gen schema context must surface column descriptions to the LLM.

Regression guard for the 'Edge (Node) cache hit ratio' grounding bug: the prompt used
to carry only column name+type, so the model couldn't scope to a coded value
(SERVER_ROLE='Node') and invented enum values.
"""

from backend.app.query.llm_sql import _build_schema_context


def test_schema_context_includes_column_descriptions():
    tables = [{"name": "DS_BASE_1M", "description": "CDN 1-min rollup", "keywords": "cache"}]
    cols = {
        "DS_BASE_1M": [
            {
                "name": "SERVER_ROLE",
                "type": "VARCHAR2",
                "description": "Cache tier: Node (=Edge), Mcache, Feda",
            },
            {"name": "PROXY_CACHE_STATUS", "type": "VARCHAR2", "description": "HIT/MISS/EXPIRED"},
        ]
    }
    ctx = _build_schema_context(tables, cols)
    assert "DS_BASE_1M" in ctx
    assert "SERVER_ROLE" in ctx
    # the descriptions (enum values / tier synonym) must reach the prompt
    assert "Node (=Edge)" in ctx
    assert "HIT/MISS/EXPIRED" in ctx


def test_schema_context_handles_missing_description():
    tables = [{"name": "T", "description": "", "keywords": ""}]
    cols = {"T": [{"name": "C", "type": "NUMBER"}]}  # no 'description' key
    ctx = _build_schema_context(tables, cols)
    assert "C (NUMBER)" in ctx  # renders name+type, no crash
