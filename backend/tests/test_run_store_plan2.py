"""TIER 3 item 18 (Plan 2 foundation) — heartbeat + fencing-token reclaim.

These pin the deploy-durability primitives the reconcile flow will use: only the
lock owner can renew it, and a stale run (status running, lock expired) can be
reclaimed exactly once while a live run cannot be stolen.
"""

from __future__ import annotations

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
