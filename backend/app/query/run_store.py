"""Durable run event log backed by Redis Streams.

A "run" is one assistant turn (one pipeline execution) for a conversation.
Its events are appended to a Redis Stream so any process can replay/tail them,
which is what makes an in-flight answer survive a client refresh.
"""

from __future__ import annotations

from redis.asyncio import Redis

STREAM_PREFIX = "aria:run:"
META_PREFIX = "aria:run_meta:"
LOCK_PREFIX = "aria:run_lock:"

# A producer must finish within this; safety against leaked locks. Sized to
# cover long-running queries. True lock renewal/heartbeat (so an in-flight run
# can outlive even this) is deferred to Plan 2 (Prefect deploy-durability).
LOCK_TTL_S = 900
STREAM_TTL_S = 3600  # keep the event log ~1h after the run ends (replay window)

RUNNING = "running"
COMPLETE = "complete"
ERROR = "error"


def _stream_key(cid: str) -> str:
    return f"{STREAM_PREFIX}{cid}"


def _meta_key(cid: str) -> str:
    return f"{META_PREFIX}{cid}"


def _lock_key(cid: str) -> str:
    return f"{LOCK_PREFIX}{cid}"


async def acquire_run(redis: Redis, cid: str, run_id: str) -> bool:
    """Try to start a run for *cid*. Returns False if one is already active.

    Uses SET NX as a one-run-per-conversation lock so a refresh-triggered
    request can never start a duplicate generation.
    """
    acquired = await redis.set(_lock_key(cid), run_id, nx=True, ex=LOCK_TTL_S)
    if not acquired:
        return False
    await redis.hset(_meta_key(cid), mapping={"run_id": run_id, "status": RUNNING})
    await redis.expire(_meta_key(cid), STREAM_TTL_S)
    return True


async def finish_run(redis: Redis, cid: str, status: str) -> None:
    """Mark a run terminal (*complete* or *error*) and release its lock."""
    await redis.hset(_meta_key(cid), "status", status)
    await redis.expire(_meta_key(cid), STREAM_TTL_S)
    await redis.expire(_stream_key(cid), STREAM_TTL_S)
    await redis.delete(_lock_key(cid))


async def get_status(redis: Redis, cid: str) -> str | None:
    """Return the run status for *cid*, or None if there is no run record."""
    status = await redis.hget(_meta_key(cid), "status")
    return status  # decode_responses=True → already str | None


async def append_event(redis: Redis, cid: str, event: dict) -> None:
    """Append one SSE event to the run's stream.

    *event* is the pipeline's event dict: {"event": str, "data": json-str}.
    """
    await redis.xadd(
        _stream_key(cid),
        {"event": event["event"], "data": event["data"]},
    )


async def read_events(
    redis: Redis, cid: str, last_id: str = "0", block_ms: int = 15000
) -> tuple[list[dict], str]:
    """Read events appended after *last_id*.

    ``last_id="0"`` replays the whole stream (used on connect/resume);
    a returned id fed back in tails only new events. ``block_ms`` blocks for
    that long waiting for new entries (0 = non-blocking, for tests).
    Returns (events, new_last_id). new_last_id is unchanged when nothing new.
    """
    result = await redis.xread({_stream_key(cid): last_id}, block=block_ms or None)
    if not result:
        return [], last_id
    # result: [(stream_key, [(entry_id, {field: val}), ...])]
    _key, entries = result[0]
    events = [{"event": fields["event"], "data": fields["data"]} for _id, fields in entries]
    new_last_id = entries[-1][0]
    return events, new_last_id
