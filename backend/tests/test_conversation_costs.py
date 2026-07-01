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


# ── Task 18: per-conversation unpriced share ─────────────────────────────────


def test_merge_attaches_unpriced_share() -> None:
    """Each conversation summary also carries ``unpriced_tokens`` (the self-hosted
    / $0-cost portion) so the admin table can show the unpriced share. Missing =>
    zero, never a KeyError."""
    summaries = [
        {"id": "cid-1", "title": "A", "message_count": 3},
        {"id": "cid-2", "title": "B", "message_count": 1},
    ]
    totals = {
        "cid-1": {"tokens": 12500, "cost": 0.05, "unpriced": 2500},
        "cid-2": {"tokens": 100, "cost": 0.01},  # no unpriced key
    }
    out = _with_token_totals(summaries, totals)

    assert out[0]["total_tokens"] == 12500
    assert out[0]["unpriced_tokens"] == 2500
    # unpriced defaults to zero when the split isn't present
    assert out[1]["total_tokens"] == 100
    assert out[1]["unpriced_tokens"] == 0
