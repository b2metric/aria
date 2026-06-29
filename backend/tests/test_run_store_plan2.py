"""TIER 3 item 18 (Plan 2 foundation) — heartbeat + fencing-token reclaim.

These pin the deploy-durability primitives the reconcile flow will use: only the
lock owner can renew it, and a stale run (status running, lock expired) can be
reclaimed exactly once while a live run cannot be stolen.
"""

from __future__ import annotations

import asyncio

import pytest
from fakeredis.aioredis import FakeRedis

from backend.app.query import run_store as rs


@pytest.mark.asyncio
async def test_heartbeat_renews_only_for_owner():
    r = FakeRedis(decode_responses=True)
    assert await rs.acquire_run(r, "c1", "run-A")
    assert await rs.heartbeat_run(r, "c1", "run-A") is True  # owner renews
    assert await rs.heartbeat_run(r, "c1", "run-B") is False  # non-owner cannot


@pytest.mark.asyncio
async def test_reclaim_only_when_lock_expired():
    r = FakeRedis(decode_responses=True)
    await rs.acquire_run(r, "c1", "run-A")  # status running, lock held
    # A live run (lock present) must NOT be reclaimable.
    assert await rs.reclaim_stale_run(r, "c1", "run-R") is False
    # Simulate producer death: the lock expires but meta stays "running".
    await r.delete(rs._lock_key("c1"))
    assert await rs.reclaim_stale_run(r, "c1", "run-R") is True
    # Second reclaimer loses (lock now held by run-R).
    assert await rs.reclaim_stale_run(r, "c1", "run-S") is False


@pytest.mark.asyncio
async def test_reclaim_skips_finished_runs():
    r = FakeRedis(decode_responses=True)
    await rs.acquire_run(r, "c2", "run-A")
    await rs.finish_run(r, "c2", "complete")
    assert await rs.reclaim_stale_run(r, "c2", "run-R") is False


@pytest.mark.asyncio
async def test_find_running_cids():
    r = FakeRedis(decode_responses=True)
    await rs.acquire_run(r, "c1", "run-A")
    await rs.acquire_run(r, "c2", "run-B")
    await rs.finish_run(r, "c2", "complete")
    cids = set(await rs.find_running_cids(r))
    assert "c1" in cids
    assert "c2" not in cids


# ── Run context (so a reconcile re-run reuses the ORIGINAL security context) ──


@pytest.mark.asyncio
async def test_acquire_run_persists_and_reads_back_context():
    """A reconcile re-run has no JWT, so the run's full gating context is stored
    on acquire and read back verbatim — no re-derivation, no security drift."""
    r = FakeRedis(decode_responses=True)
    ctx = {
        "question": "How many orders last month?",
        "db_config_id": "db-7",
        "workspace_id": "ws-1",
        "user_id": "user-1",
        "team_id": "team-1",
        "sql_visible": True,
    }
    assert await rs.acquire_run(r, "c1", "run-A", context=ctx) is True
    got = await rs.get_run_context(r, "c1")
    assert got == ctx
    # status still tracked alongside the context
    assert await rs.get_status(r, "c1") == rs.RUNNING


@pytest.mark.asyncio
async def test_get_run_context_roundtrips_none_optionals_and_false_visibility():
    r = FakeRedis(decode_responses=True)
    ctx = {
        "question": "q",
        "db_config_id": None,
        "workspace_id": "ws-1",
        "user_id": "user-1",
        "team_id": None,
        "sql_visible": False,
    }
    await rs.acquire_run(r, "c2", "run-B", context=ctx)
    got = await rs.get_run_context(r, "c2")
    assert got["db_config_id"] is None
    assert got["team_id"] is None
    assert got["sql_visible"] is False


@pytest.mark.asyncio
async def test_get_run_context_returns_none_when_no_context_stored():
    r = FakeRedis(decode_responses=True)
    await rs.acquire_run(r, "c3", "run-C")  # no context
    assert await rs.get_run_context(r, "c3") is None


# ── Heartbeat maintenance loop (keeps a long live run's lock alive) ──────────


@pytest.mark.asyncio
async def test_maintain_heartbeat_renews_then_exits_when_ownership_lost():
    r = FakeRedis(decode_responses=True)
    await rs.acquire_run(r, "c1", "run-A")
    task = asyncio.create_task(rs.maintain_heartbeat(r, "c1", "run-A", interval_s=0.01))
    await asyncio.sleep(0.03)  # a couple of renewals while still the owner
    assert not task.done()
    # Another producer reclaims the lock (simulated): the loop must notice it no
    # longer owns the lock and exit — never extend a successor's lock.
    await r.set(rs._lock_key("c1"), "run-B")
    await asyncio.sleep(0.04)
    assert task.done()
    await task  # propagate any error
