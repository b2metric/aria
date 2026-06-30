"""Phase 2 — the SQL prompt must NOT auto-cap rows (only honor explicit top-N).

A default 'FETCH FIRST 100' instruction made the model emit its own limit, which
defeated the EXPLAIN-based routing (EXPLAIN saw the capped SQL). The pipeline owns
limiting now; the model only limits when the user explicitly asks for top/first N.
"""

from __future__ import annotations

from backend.app.query.llm_sql import SYSTEM_PROMPT


def test_prompt_does_not_instruct_a_default_row_limit():
    text = SYSTEM_PROMPT.lower()
    assert "default: fetch first 100" not in text
    assert "always include reasonable limits" not in text


def test_prompt_tells_model_not_to_self_limit():
    text = SYSTEM_PROMPT.lower()
    # The model is told the system applies limits; it only limits on explicit top-N.
    assert "do not add" in text          # told not to self-limit
    assert "limit" in text               # the prohibition is about row limits
    assert "explicitly asks" in text     # explicit top-N / first-N intent still honored
