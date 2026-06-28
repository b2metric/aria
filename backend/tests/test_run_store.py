"""Unit tests for the durable run event log (Redis Streams)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis

from backend.app.query import run_store

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def redis():
    r = FakeRedis(decode_responses=True)
    yield r
    await r.flushall()
    await r.aclose()


async def test_acquire_run_returns_true_first_time(redis):
    assert await run_store.acquire_run(redis, "cid-1", "run-a") is True
    assert await run_store.get_status(redis, "cid-1") == "running"


async def test_acquire_run_returns_false_while_locked(redis):
    assert await run_store.acquire_run(redis, "cid-1", "run-a") is True
    assert await run_store.acquire_run(redis, "cid-1", "run-b") is False


async def test_finish_run_sets_terminal_status_and_releases_lock(redis):
    await run_store.acquire_run(redis, "cid-1", "run-a")
    await run_store.finish_run(redis, "cid-1", "complete")
    assert await run_store.get_status(redis, "cid-1") == "complete"
    assert await run_store.acquire_run(redis, "cid-1", "run-b") is True


async def test_get_status_none_when_unknown(redis):
    assert await run_store.get_status(redis, "nope") is None


async def test_append_and_read_events_replays_in_order(redis):
    await run_store.acquire_run(redis, "cid-1", "run-a")
    await run_store.append_event(
        redis, "cid-1", {"event": "status", "data": '{"status":"thinking"}'}
    )
    await run_store.append_event(redis, "cid-1", {"event": "sql", "data": '{"sql":"SELECT 1"}'})

    events, last_id = await run_store.read_events(redis, "cid-1", "0", block_ms=0)

    assert [e["event"] for e in events] == ["status", "sql"]
    assert events[1]["data"] == '{"sql":"SELECT 1"}'
    assert last_id != "0"


async def test_read_events_from_last_id_returns_only_new(redis):
    await run_store.acquire_run(redis, "cid-1", "run-a")
    await run_store.append_event(redis, "cid-1", {"event": "status", "data": "{}"})
    first, last_id = await run_store.read_events(redis, "cid-1", "0", block_ms=0)

    await run_store.append_event(redis, "cid-1", {"event": "done", "data": "{}"})
    second, _ = await run_store.read_events(redis, "cid-1", last_id, block_ms=0)

    assert [e["event"] for e in second] == ["done"]


async def test_read_events_empty_when_nothing_new(redis):
    await run_store.acquire_run(redis, "cid-1", "run-a")
    events, last_id = await run_store.read_events(redis, "cid-1", "$", block_ms=0)
    assert events == []
