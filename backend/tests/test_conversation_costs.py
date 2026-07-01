"""Sprint 2 Task 11: per-conversation cumulative tokens + cost merge helper."""

from __future__ import annotations

from backend.app.api.endpoints.admin.conversations import _with_token_totals


def test_merge_attaches_totals_by_conversation_id() -> None:
    summaries = [
        {"id": "cid-1", "title": "A", "message_count": 2},
        {"id": "cid-2", "title": "B", "message_count": 1},
    ]
    totals = {
        "cid-1": {"tokens": 12884, "cost": 0.0304},
        # cid-2 has no LLM events yet
    }
    out = _with_token_totals(summaries, totals)

    assert out[0]["total_tokens"] == 12884
    assert out[0]["cost_usd"] == 0.0304
    # original fields preserved
    assert out[0]["title"] == "A"
    # a conversation with no events defaults to zero, never missing
    assert out[1]["total_tokens"] == 0
    assert out[1]["cost_usd"] == 0.0
