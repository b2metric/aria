"""Memory decay tuning — relevance scoring over hard delete (Sprint 15 Task 5).

User preferences used a hard 180-day delete. These tests cover the replacement:
a recency- and usage-weighted relevance score that (a) ranks recall and (b) only
purges long-cold entries (low score), so a frequently-recalled old preference
survives where an untouched one decays away.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from backend.app.memory.service import (
    MEMORY_HALF_LIFE_DAYS,
    MEMORY_PURGE_THRESHOLD,
    MemoryService,
    relevance_score,
    should_purge_user_memory,
)


def _iso_days_ago(days: float) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def test_relevance_score_decays_with_age() -> None:
    assert relevance_score(0) == 1.0
    # One half-life → ~0.5; monotonically decreasing afterwards.
    assert abs(relevance_score(MEMORY_HALF_LIFE_DAYS) - 0.5) < 1e-9
    assert (
        relevance_score(0)
        > relevance_score(MEMORY_HALF_LIFE_DAYS)
        > relevance_score(2 * MEMORY_HALF_LIFE_DAYS)
    )


def test_usage_slows_decay() -> None:
    # Same age, more recalls → higher relevance (usage extends effective life).
    cold = relevance_score(MEMORY_HALF_LIFE_DAYS, use_count=0)
    warm = relevance_score(MEMORY_HALF_LIFE_DAYS, use_count=20)
    assert warm > cold
    assert warm <= 1.0


def test_should_purge_only_long_cold_entries() -> None:
    now = datetime.now(UTC)
    fresh = {"created_at": _iso_days_ago(5)}
    cold = {"created_at": _iso_days_ago(400)}
    cold_but_used = {"created_at": _iso_days_ago(400), "metadata": {"use_count": 100}}
    unknown = {"created_at": None}

    assert should_purge_user_memory(fresh, now) is False
    assert should_purge_user_memory(cold, now) is True
    # Heavy usage rescues an otherwise-cold entry from the purge.
    assert should_purge_user_memory(cold_but_used, now) is False
    # Unknown age → never blindly deleted.
    assert should_purge_user_memory(unknown, now) is False


def test_purge_threshold_is_below_one() -> None:
    assert 0.0 < MEMORY_PURGE_THRESHOLD < 1.0


def test_get_user_preferences_ranked_by_relevance() -> None:
    svc = MemoryService.__new__(MemoryService)
    mem = MagicMock()
    svc._memory = mem
    # Returned out of order: old, fresh, mid.
    mem.get_all.return_value = {
        "results": [
            {"id": "old", "memory": "old", "created_at": _iso_days_ago(300)},
            {"id": "fresh", "memory": "fresh", "created_at": _iso_days_ago(1)},
            {"id": "mid", "memory": "mid", "created_at": _iso_days_ago(60)},
        ]
    }

    prefs = svc.get_user_preferences(workspace_id="ws1", user_id="u1")

    # Ranked freshest (highest relevance) first.
    assert [p["id"] for p in prefs] == ["fresh", "mid", "old"]
