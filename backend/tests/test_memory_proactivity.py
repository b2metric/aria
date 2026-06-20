"""Memory proactivity — standing preferences feed SQL generation (Sprint 15 Task 4).

Stored user preferences (e.g. "User associates TOPUP_AMOUNT with revenue") are
recalled via semantic search, which only fires when the question wording is
similar. These tests cover the *proactive* path: `lookup` also pulls standing
USER-type preferences unconditionally (via `get_all`) and merges them into the
SQL prompt context, deduped against the semantic matches.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.app.memory.service import MemoryContext, MemoryService


def _service_with_mock_memory() -> tuple[MemoryService, MagicMock]:
    svc = MemoryService.__new__(MemoryService)
    mem = MagicMock()
    svc._memory = mem
    return svc, mem


def test_get_user_preferences_returns_all_user_memories() -> None:
    svc, mem = _service_with_mock_memory()
    mem.get_all.return_value = {
        "results": [
            {"id": "p1", "memory": "User prefers bar charts"},
            {"id": "p2", "memory": "User associates TOPUP_AMOUNT with revenue"},
        ]
    }

    prefs = svc.get_user_preferences(workspace_id="ws1", user_id="u1")

    assert [p["id"] for p in prefs] == ["p1", "p2"]
    mem.get_all.assert_called_once_with(user_id="ws1:u1")


def test_lookup_proactively_injects_standing_preferences() -> None:
    svc, mem = _service_with_mock_memory()
    # Semantic user search matches only one pref for this question…
    user_semantic = {"results": [{"id": "p1", "memory": "User prefers bar charts"}]}
    # …but the user also has a standing directive that the question doesn't match.
    standing = {
        "results": [
            {"id": "p1", "memory": "User prefers bar charts"},  # dup of semantic
            {"id": "p2", "memory": "User associates TOPUP_AMOUNT with revenue"},
        ]
    }
    # lookup runs 3 searches (user, team, cache); team/cache empty here.
    mem.search.side_effect = [user_semantic, {"results": []}, {"results": []}]
    mem.get_all.return_value = standing

    ctx = svc.lookup(question="show me churn", user_id="u1", workspace_id="ws1", team_id="t1")

    ids = [p["id"] for p in ctx.user_preferences]
    # Both prefs present, standing one injected, no duplicate of p1.
    assert ids == ["p1", "p2"]


def test_lookup_proactive_injection_survives_when_memory_unset() -> None:
    svc = MemoryService.__new__(MemoryService)
    svc._memory = None
    assert svc.get_user_preferences(workspace_id="ws1", user_id="u1") == []


def test_to_prompt_context_shows_up_to_five_user_preferences() -> None:
    prefs = [{"memory": f"pref-{i}"} for i in range(6)]
    ctx = MemoryContext(
        user_preferences=prefs,
        team_conventions=[],
        similar_queries=[],
        raw_memories=[],
    )
    rendered = ctx.to_prompt_context()
    # Five shown (proactive directives + relevant matches), sixth trimmed.
    assert "pref-0" in rendered
    assert "pref-4" in rendered
    assert "pref-5" not in rendered
