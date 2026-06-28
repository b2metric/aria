"""Team-convention approval workflow (Sprint 15 Task 3).

Unit-tests the MemoryService status gating with a mocked Mem0 client:
- ``lookup`` only surfaces approved (or legacy/no-status) team conventions.
- ``set_memory_status`` re-writes the entry with the new metadata status.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.app.memory.service import MemoryService


def _service_with_mock_memory() -> tuple[MemoryService, MagicMock]:
    """Build a MemoryService bypassing __init__ (no real Mem0/Qdrant)."""
    svc = MemoryService.__new__(MemoryService)
    mem = MagicMock()
    svc._memory = mem
    return svc, mem


def test_lookup_only_returns_approved_team_conventions() -> None:
    svc, mem = _service_with_mock_memory()
    team_results = {
        "results": [
            {"memory": "approved rule", "metadata": {"status": "approved"}},
            {"memory": "pending rule", "metadata": {"status": "pending"}},
            {"memory": "rejected rule", "metadata": {"status": "rejected"}},
            {"memory": "legacy rule", "metadata": {}},  # no status → treated approved
        ]
    }
    # lookup runs 3 searches: user, team, query_cache
    mem.search.side_effect = [{"results": []}, team_results, {"results": []}]

    ctx = svc.lookup(question="revenue", user_id="u1", workspace_id="ws1", team_id="t1")

    contents = [m["memory"] for m in ctx.team_conventions]
    assert contents == ["approved rule", "legacy rule"]
    assert "pending rule" not in contents
    assert "rejected rule" not in contents


def test_set_memory_status_updates_metadata() -> None:
    svc, mem = _service_with_mock_memory()
    mem.get_all.return_value = {
        "results": [
            {"id": "mem-123", "memory": "some convention", "metadata": {"created_by": "admin"}},
        ]
    }

    ok = svc.set_memory_status("mem-123", "approved", workspace_id="ws1", team_id="t1")

    assert ok is True
    mem.get_all.assert_called_once_with(filters={"user_id": "ws1:team:t1"})
    # status change = delete + re-add (Mem0 2.x update()/get() by id unreliable)
    mem.delete.assert_called_once_with("mem-123")
    mem.add.assert_called_once()
    args, kwargs = mem.add.call_args
    assert args[0] == "some convention"
    assert kwargs["metadata"]["status"] == "approved"
    assert kwargs["metadata"]["created_by"] == "admin"  # preserved
    assert kwargs["infer"] is False


def test_set_memory_status_missing_entry_returns_false() -> None:
    svc, mem = _service_with_mock_memory()
    mem.get_all.return_value = {"results": []}

    assert svc.set_memory_status("nope", "approved", workspace_id="ws1", team_id="t1") is False
    mem.delete.assert_not_called()
    mem.add.assert_not_called()
