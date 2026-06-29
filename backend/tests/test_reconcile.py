"""TIER 3 item 18 (Plan 2) — Prefect reconcile flow for deploy-durability.

The reconcile core scans for stalled runs (status ``running`` but the producer's
lock has expired → its process died), reclaims each via the fencing token, and
re-runs generation idempotently using the persisted run context (NOT a JWT).

Fencing invariants under test:
- a STALE run is reclaimed exactly once and re-run with ``resume=True``;
- a LIVE run (lock still held) is never stolen → never double-run;
- a run with no persisted context is failed terminally, not left running forever.
"""

from __future__ import annotations

import json

import pytest
from fakeredis.aioredis import FakeRedis

from backend.app.flows import reconcile
from backend.app.query import run_store as rs

pytestmark = pytest.mark.asyncio


def _make_fake_process_query(calls: list[dict]):
    """A process_query stand-in that records its kwargs and emits a tiny run."""

    async def _fake(*args, **kwargs):
        calls.append(kwargs)
        yield {"event": "status", "data": json.dumps({"status": "thinking"})}
        yield {"event": "sql", "data": json.dumps({"sql": "SELECT 1"})}
        yield {"event": "done", "data": json.dumps({"conversation_id": kwargs.get("workspace_id")})}

    return _fake


async def _seed_stale_run(r: FakeRedis, cid: str) -> None:
    """A run left ``running`` whose producer died: lock gone, context present."""
    ctx = {
        "question": "orders last month?",
        "db_config_id": None,
        "workspace_id": "ws-1",
        "user_id": "user-1",
        "team_id": "team-1",
        "sql_visible": False,
    }
    await rs.acquire_run(r, cid, "run-dead", context=ctx)
    await r.delete(rs._lock_key(cid))  # producer death: lock expired, meta still running


async def test_reconcile_reclaims_stale_run_and_reruns_with_resume(monkeypatch):
    r = FakeRedis(decode_responses=True)
    calls: list[dict] = []
    monkeypatch.setattr(reconcile, "process_query", _make_fake_process_query(calls))
    await _seed_stale_run(r, "c1")

    reclaimed = await reconcile.reconcile_stalled_runs_core(r, engine=None)

    assert reclaimed == ["c1"]
    # Re-run used the persisted security context, NOT a fresh/default one.
    assert len(calls) == 1
    assert calls[0]["resume"] is True
    assert calls[0]["user_id"] == "user-1"
    assert calls[0]["workspace_id"] == "ws-1"
    assert calls[0]["team_id"] == "team-1"
    assert calls[0]["sql_visible"] is False
    # The re-run's events landed in the stream and the run is now terminal.
    events, _ = await rs.read_events(r, "c1", "0", block_ms=0)
    assert [e["event"] for e in events] == ["status", "sql", "done"]
    assert await rs.get_status(r, "c1") == rs.COMPLETE


async def test_reconcile_does_not_steal_a_live_run(monkeypatch):
    r = FakeRedis(decode_responses=True)
    calls: list[dict] = []
    monkeypatch.setattr(reconcile, "process_query", _make_fake_process_query(calls))
    # Live run: lock still held (heartbeat alive). Must NOT be reclaimed/re-run.
    await rs.acquire_run(
        r,
        "c1",
        "run-live",
        context={
            "question": "q",
            "db_config_id": None,
            "workspace_id": "ws",
            "user_id": "u",
            "team_id": None,
            "sql_visible": True,
        },
    )

    reclaimed = await reconcile.reconcile_stalled_runs_core(r, engine=None)

    assert reclaimed == []
    assert calls == []  # no duplicate generation
    assert await rs.get_status(r, "c1") == rs.RUNNING


async def test_reconcile_fails_run_with_missing_context(monkeypatch):
    r = FakeRedis(decode_responses=True)
    calls: list[dict] = []
    monkeypatch.setattr(reconcile, "process_query", _make_fake_process_query(calls))
    await rs.acquire_run(r, "c1", "run-dead")  # running, NO context
    await r.delete(rs._lock_key("c1"))  # producer died

    reclaimed = await reconcile.reconcile_stalled_runs_core(r, engine=None)

    assert reclaimed == []
    assert calls == []  # cannot faithfully re-run → do not run blind
    assert await rs.get_status(r, "c1") == rs.ERROR  # not left running forever


async def test_reconcile_is_idempotent_across_passes(monkeypatch):
    """A second reconcile pass finds nothing to do (run already completed)."""
    r = FakeRedis(decode_responses=True)
    calls: list[dict] = []
    monkeypatch.setattr(reconcile, "process_query", _make_fake_process_query(calls))
    await _seed_stale_run(r, "c1")

    first = await reconcile.reconcile_stalled_runs_core(r, engine=None)
    second = await reconcile.reconcile_stalled_runs_core(r, engine=None)

    assert first == ["c1"]
    assert second == []  # no stale run remains → no second generation
    assert len(calls) == 1
