"""Deploy-durability reconcile flow (TIER 3 item 18, Plan 2).

When the worker producing a chat answer dies mid-flight (deploy/crash), its run
is left ``running`` in Redis but its lock lapses (no more heartbeats). This flow,
scheduled on the prod Prefect worker (~60s), scans for such stalled runs, takes
each one over via the fencing token, and re-runs generation idempotently using
the run's persisted context (NOT a JWT) so the in-flight answer still completes.

Fencing safety (why this can't double-run a live query):
  * ``reclaim_stale_run`` is an atomic ``SET NX`` — it only succeeds when the
    lock is gone (producer dead). A live producer (lock held + heartbeat) is
    never reclaimable, so its run is never re-run in parallel.
  * The re-run passes ``resume=True`` so the user message is not duplicated.

The orchestration core (:func:`reconcile_stalled_runs_core`) is pure async with
no Prefect dependency, so it is unit-tested directly with fakeredis. The Prefect
decoration is applied lazily so importing this module never requires a Prefect
server.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.app.query import QueryRequest, run_store
from backend.app.query.pipeline import process_query

logger = logging.getLogger(__name__)


async def _rerun_stalled(
    redis: Redis, engine: AsyncEngine | None, *, cid: str, run_id: str, ctx: dict
) -> None:
    """Re-run a reclaimed stale run, streaming its events into the run store.

    Mirrors the POST producer's drive loop but with ``resume=True`` (no user
    message re-append) and a heartbeat task so this re-run, too, keeps its
    reclaimed lock alive while it works.
    """
    body = QueryRequest(
        question=ctx["question"],
        conversation_id=cid,
        db_config_id=ctx["db_config_id"],
    )
    heartbeat = asyncio.create_task(run_store.maintain_heartbeat(redis, cid, run_id))
    try:
        async for event in process_query(
            redis=redis,
            engine=engine,
            request=body,
            workspace_id=ctx["workspace_id"],
            user_id=ctx["user_id"],
            team_id=ctx["team_id"],
            sql_visible=ctx["sql_visible"],
            resume=True,
        ):
            await run_store.append_event(redis, cid, event)
        await run_store.finish_run(redis, cid, run_store.COMPLETE)
    except Exception as exc:  # noqa: BLE001 — surface as a terminal error event
        logger.exception("Reconcile re-run failed for conversation %s", cid)
        await run_store.append_event(
            redis, cid, {"event": "error", "data": json.dumps({"error": str(exc)})}
        )
        await run_store.finish_run(redis, cid, run_store.ERROR)
    finally:
        heartbeat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat


async def reconcile_stalled_runs_core(redis: Redis, engine: AsyncEngine | None) -> list[str]:
    """Scan for stalled runs, reclaim each, and re-run it. Returns reclaimed cids.

    A run is stalled when its meta is still ``running`` but its lock has lapsed
    (producer died). ``reclaim_stale_run`` enforces this atomically, so a live
    run is skipped and never duplicated.
    """
    reclaimed: list[str] = []
    for cid in await run_store.find_running_cids(redis):
        new_run_id = uuid.uuid4().hex
        if not await run_store.reclaim_stale_run(redis, cid, new_run_id):
            # Lock still held (live producer) or another reconciler won the
            # takeover — either way, do NOT run a second generation.
            continue
        ctx = await run_store.get_run_context(redis, cid)
        if ctx is None:
            # No persisted context ⇒ we cannot faithfully reproduce the original
            # run. Fail it terminally rather than re-run blind or leave it
            # "running" forever (which would re-trip every reconcile pass).
            logger.warning("Reconcile: run %s has no persisted context; failing it", cid)
            await run_store.append_event(
                redis,
                cid,
                {"event": "error", "data": json.dumps({"error": "reconcile: missing run context"})},
            )
            await run_store.finish_run(redis, cid, run_store.ERROR)
            continue
        await _rerun_stalled(redis, engine, cid=cid, run_id=new_run_id, ctx=ctx)
        reclaimed.append(cid)
    return reclaimed


async def reconcile_stalled_runs() -> list[str]:
    """Flow entrypoint: build Redis + engine and run the reconcile core.

    Imported lazily from the API layer's connection factories so this module
    stays import-light (no FastAPI/engine at import time).
    """
    from backend.app.api.query import _get_engine, _get_redis

    redis = await _get_redis()
    engine = await _get_engine()
    try:
        reclaimed = await reconcile_stalled_runs_core(redis, engine)
        if reclaimed:
            logger.info("Reconcile reclaimed %d stalled run(s): %s", len(reclaimed), reclaimed)
        return reclaimed
    finally:
        await redis.aclose()
        await engine.dispose()


def get_reconcile_flow():
    """Return the Prefect-decorated reconcile flow (for deployment registration).

    Prefect is imported here, not at module top, so unit tests that exercise the
    core never need a Prefect install/server.
    """
    from prefect import flow

    return flow(name="reconcile-stalled-runs", log_prints=True)(reconcile_stalled_runs)
