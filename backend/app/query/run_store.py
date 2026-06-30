"""Durable run event log backed by Redis Streams.

A "run" is one assistant turn (one pipeline execution) for a conversation.
Its events are appended to a Redis Stream so any process can replay/tail them,
which is what makes an in-flight answer survive a client refresh.
"""

from __future__ import annotations

import asyncio

from redis.asyncio import Redis

STREAM_PREFIX = "aria:run:"
META_PREFIX = "aria:run_meta:"
LOCK_PREFIX = "aria:run_lock:"

# A producer must finish within this; safety against leaked locks. Sized to
# cover long-running queries. A live run renews the lock via ``maintain_heartbeat``
# (Plan 2), so it can outlive a single TTL; only a DEAD producer lets the lock
# lapse, which is what makes its run reclaimable by the reconcile flow.
LOCK_TTL_S = 900
# Renew the lock well within its TTL so two consecutive missed renewals (e.g. a
# brief event-loop stall) still don't lapse a live run's lock.
HEARTBEAT_INTERVAL_S = 300
STREAM_TTL_S = 3600  # keep the event log ~1h after the run ends (replay window)

# Run-context fields persisted on acquire so a reconcile re-run (which has no
# JWT) can reuse the EXACT original gating context — no re-derivation, no drift.
_CONTEXT_FIELDS = ("question", "db_config_id", "workspace_id", "user_id", "team_id")

RUNNING = "running"
COMPLETE = "complete"
ERROR = "error"


def _stream_key(cid: str) -> str:
    return f"{STREAM_PREFIX}{cid}"


def _meta_key(cid: str) -> str:
    return f"{META_PREFIX}{cid}"


def _lock_key(cid: str) -> str:
    return f"{LOCK_PREFIX}{cid}"


async def acquire_run(
    redis: Redis, cid: str, run_id: str, context: dict | None = None
) -> bool:
    """Try to start a run for *cid*. Returns False if one is already active.

    Uses SET NX as a one-run-per-conversation lock so a refresh-triggered
    request can never start a duplicate generation.

    *context* (optional) is the run's gating context (question, db_config_id,
    workspace_id, user_id, team_id, sql_visible). It is persisted alongside the
    run so a reconcile re-run can reproduce the ORIGINAL run without a JWT —
    see :func:`get_run_context`.
    """
    acquired = await redis.set(_lock_key(cid), run_id, nx=True, ex=LOCK_TTL_S)
    if not acquired:
        return False
    # Start this run with a clean event log. The stream key is per-conversation
    # and accumulates across turns, but the tailer replays from id "0" and stops
    # at the first ``done`` — so a surviving prior turn would be replayed instead
    # of this run. Clearing it here restores the "stream holds only the current
    # turn" invariant the replay/resume logic depends on. (Conversation history
    # is persisted separately in the conversation store, not in this stream.)
    await redis.delete(_stream_key(cid))
    mapping: dict[str, str] = {"run_id": run_id, "status": RUNNING}
    if context is not None:
        # Redis hash values must be strings: None optionals → "", bool → "1"/"0".
        for field in _CONTEXT_FIELDS:
            mapping[field] = "" if context.get(field) is None else str(context[field])
        mapping["sql_visible"] = "1" if context.get("sql_visible") else "0"
    await redis.hset(_meta_key(cid), mapping=mapping)
    await redis.expire(_meta_key(cid), STREAM_TTL_S)
    return True


async def get_run_context(redis: Redis, cid: str) -> dict | None:
    """Return the persisted gating context for *cid*, or None if none was stored.

    Inverse of the serialization in :func:`acquire_run`: "" → None for the
    optional fields, "1"/"0" → bool for ``sql_visible``. Used by the reconcile
    flow to re-run a stalled run with its exact original security context.
    """
    meta = await redis.hgetall(_meta_key(cid))
    if not meta or "question" not in meta:
        return None
    return {
        "question": meta["question"],
        "db_config_id": meta.get("db_config_id") or None,
        "workspace_id": meta.get("workspace_id") or None,
        "user_id": meta.get("user_id") or None,
        "team_id": meta.get("team_id") or None,
        "sql_visible": meta.get("sql_visible") == "1",
    }


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


async def maintain_heartbeat(
    redis: Redis, cid: str, run_id: str, interval_s: float = HEARTBEAT_INTERVAL_S
) -> None:
    """Renew the run lock on a fixed cadence until ownership is lost.

    Run as a detached task for the lifetime of a producer: every *interval_s*
    it renews the lock so a long-but-alive run never lapses (and so never gets
    falsely reclaimed). The moment a renewal reports the lock is no longer ours
    (it expired and a reconciler took it over), the loop exits — a producer that
    already lost the race must never keep extending its successor's lock.
    """
    while True:
        await asyncio.sleep(interval_s)
        if not await heartbeat_run(redis, cid, run_id):
            return


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
