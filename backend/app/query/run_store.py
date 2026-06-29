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


# ── Plan 2: deploy-durability (heartbeat + fencing-token reclaim) ────────────
# The lock value IS the run_id, so it doubles as a fencing token: only the run
# that holds it may renew it, and a reconciler can only reclaim a run whose lock
# has EXPIRED (its producer died). This makes an in-flight answer survive a
# backend restart — a scheduled reconcile (Prefect) re-runs the stalled run.

async def heartbeat_run(redis: Redis, cid: str, run_id: str) -> bool:
    """Renew the run lock while the producer is alive. Returns False if the
    caller no longer owns the lock (it expired and was reclaimed elsewhere).

    Ownership is re-checked before renewing so a producer that already lost its
    lock cannot extend a successor's. (Reclaim safety — the fencing guarantee —
    is enforced atomically by ``reclaim_stale_run``'s SET NX, not here.)
    """
    if (await redis.get(_lock_key(cid))) != run_id:
        return False
    await redis.expire(_lock_key(cid), LOCK_TTL_S)
    return True


async def reclaim_stale_run(redis: Redis, cid: str, new_run_id: str) -> bool:
    """Try to take over a STALE run (status still ``running`` but its lock has
    expired → producer died). Returns True if this caller won the takeover.

    Fail-safe: ``SET NX`` only succeeds when the lock is gone, so a still-alive
    producer (lock present) is never stolen from.
    """
    if (await redis.hget(_meta_key(cid), "status")) != RUNNING:
        return False
    acquired = await redis.set(_lock_key(cid), new_run_id, nx=True, ex=LOCK_TTL_S)
    return bool(acquired)


async def find_running_cids(redis: Redis) -> list[str]:
    """Return the cids whose run meta is still ``running`` (reconcile candidates)."""
    out: list[str] = []
    async for key in redis.scan_iter(match=f"{META_PREFIX}*"):
        if (await redis.hget(key, "status")) == RUNNING:
            out.append(key[len(META_PREFIX) :])
    return out


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
