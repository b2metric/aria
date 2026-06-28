"""Chat query API endpoint with SSE streaming.

POST /api/query — stream NL→SQL→chart pipeline via Server-Sent Events.
GET  /api/conversations — list recent conversations.
GET  /api/conversations/{id} — get conversation details.
DELETE /api/conversations/{id} — delete a conversation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine
from sse_starlette.sse import EventSourceResponse

from backend.app.auth.dependencies import CurrentUser, WorkspaceID
from backend.app.core.config import get_settings
from backend.app.query import Conversation, QueryRequest, run_store
from backend.app.query.conversation import (
    delete_conversation,
    get_conversation,
    list_conversations,
    save_conversation,
)
from backend.app.query.pipeline import process_query
from backend.app.query.sql_visibility import resolve_effective_sql_visibility
from backend.app.services.rate_limit import RateLimitExceeded, check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])


async def _get_redis() -> Redis:
    """Get a Redis connection from settings."""
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def _get_engine() -> AsyncEngine:
    """Get a SQLAlchemy async engine."""
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False)


async def _resolve_sql_visible(engine: AsyncEngine, user: CurrentUser) -> bool:
    """Resolve effective SQL visibility for *user*.

    ``get_current_user`` is JWT-only, so the per-user override
    (``users.sql_visibility``) is read here from the metadata DB.  The override
    wins when set; otherwise we fall back to the role default
    (``resolve_effective_sql_visibility(role, None)``).

    Fail CLOSED: any error reading the override resolves to ``False`` (hide
    SQL).  A user explicitly set ``sql_visibility=False`` who then hits a
    transient DB error must NOT silently become visible again — that would be
    an information leak — so the secure direction on failure is to deny.
    """
    from sqlalchemy import text as _text

    if not user.user_id:
        return resolve_effective_sql_visibility(user.role, sql_visibility=None)

    # users.id is UUID. Compare on id::text so a non-UUID identifier (legacy
    # `admin-001` custom claim, `unknown-user` auth fallback) binds as TEXT and
    # simply matches no row — instead of crashing asyncpg's UUID encoder. The DB
    # lookup STILL runs so the per-user override is respected and a transient DB
    # error still fails closed (security invariant — never silently grant).
    try:
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    _text("SELECT sql_visibility FROM users WHERE id::text = :uid"),
                    {"uid": str(user.user_id)},
                )
            ).fetchone()
        override = row[0] if row is not None else None
    except Exception:
        # Fail closed: deny SQL visibility when the override cannot be read.
        logger.warning(
            "Failed to read per-user sql_visibility for user_id=%s; failing closed (SQL hidden)",
            user.user_id,
            exc_info=True,
        )
        return False

    return resolve_effective_sql_visibility(user.role, sql_visibility=override)


# ── Durable run: producer + tailer ────────────────────────────────────────

# Hold strong references to detached producer tasks so they are not GC'd
# mid-flight (asyncio only keeps weak refs to bare tasks).
_PRODUCERS: set[asyncio.Task] = set()


async def _run_producer(
    *,
    redis: Redis,
    engine: AsyncEngine,
    body: QueryRequest,
    workspace_id: str,
    user_id: str,
    team_id: str | None,
    sql_visible: bool,
    cid: str,
) -> None:
    """Drive the (already SQL-visibility-gated) pipeline into the run stream.

    Runs detached from the HTTP request, so a client disconnect does not kill
    generation. Every event is appended to ``aria:run:{cid}``; the run is then
    marked terminal and its lock released.
    """
    try:
        async for event in process_query(
            redis=redis,
            engine=engine,
            request=body,
            workspace_id=workspace_id,
            user_id=user_id,
            team_id=team_id,
            sql_visible=sql_visible,
        ):
            await run_store.append_event(redis, cid, event)
        await run_store.finish_run(redis, cid, run_store.COMPLETE)
    except asyncio.CancelledError:
        # Deploy/shutdown cancelled the detached task: mark the run terminal so
        # it is not left RUNNING until the lock TTL expires, then re-raise so
        # cancellation propagates correctly.
        await run_store.finish_run(redis, cid, run_store.ERROR)
        raise
    except Exception as exc:  # noqa: BLE001 — surface as a terminal error event
        logger.exception("Producer failed for conversation %s", cid)
        await run_store.append_event(
            redis, cid, {"event": "error", "data": json.dumps({"error": str(exc)})}
        )
        await run_store.finish_run(redis, cid, run_store.ERROR)


async def _tail_events(redis: Redis, cid: str, request: Request):
    """Yield SSE events from the run stream until the run is terminal.

    Replays from the start (id ``0``) so a reconnecting client sees the whole
    in-flight turn, then live-tails. Stops on a ``done``/``error`` event, or
    when the run record is terminal and the stream is drained.
    """
    last_id = "0"
    while True:
        if await request.is_disconnected():
            return
        events, last_id = await run_store.read_events(redis, cid, last_id, block_ms=15000)
        for event in events:
            yield event
            if event["event"] in ("done", "error"):
                return
        if not events:
            status = await run_store.get_status(redis, cid)
            # None ⇒ no run record (unknown / expired cid): there is nothing to
            # tail, so terminate instead of looping forever.
            if status in (run_store.COMPLETE, run_store.ERROR, None):
                return
            # Yield control so the detached producer task gets scheduled. Real
            # Redis XREAD blocks server-side and already yields; this only fires
            # after a block timeout / empty read (and under fakeredis, whose
            # XREAD does not truly block) so it is harmless in production.
            await asyncio.sleep(0)


# ── Query endpoint (SSE) ──────────────────────────────────────────────────


@router.post("/query", summary="Process a natural language query via SSE")
async def query(
    request: Request,
    body: QueryRequest,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> EventSourceResponse:
    """Submit a natural language question and receive streaming results via SSE.

    Events emitted:
        status  — {status: "thinking"|"generating_sql"|"sql_ready"|"rendering_chart"|"complete"}
        sql     — {sql: "...", explanation: "..."}
        chart   — {chart_spec: {type, title, colors}}
        error   — {error: "..."}
        done    — {conversation_id: "..."}

    The frontend should reconnect on connection loss and resume by passing
    the conversation_id from the last received ``done`` event.
    """
    redis = await _get_redis()

    # Check rate limit before proceeding (e.g. 20 queries per minute)
    try:
        await check_rate_limit(redis, user.user_id, limit=20, window=60)
    except RateLimitExceeded as e:
        await redis.aclose()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": e.message, "retry_after": e.retry_after},
            headers={"Retry-After": str(e.retry_after)},
        ) from e

    engine = await _get_engine()

    # Any failure during setup must release the request's redis+engine: the
    # event_generator's finally only runs if we reach the return below.
    try:
        # Resolve the per-user SQL-visibility override (DB) over the role default.
        sql_visible = await _resolve_sql_visible(engine, user)

        # Ensure we have a conversation id BEFORE spawning the producer, so the
        # run stream/lock can be keyed on it. A brand-new conversation is created
        # empty here; process_query() then loads it and appends the user message
        # (no dup).
        cid = body.conversation_id
        if not cid:
            conv = Conversation(workspace_id=workspace_id, user_id=user.user_id)
            await save_conversation(redis, conv)
            cid = conv.id
            body.conversation_id = cid

        # One run per conversation. If a run is already active (e.g. a duplicate
        # submit / refresh re-POST), do NOT start a second generation — just tail.
        run_id = uuid.uuid4().hex
        started = await run_store.acquire_run(redis, cid, run_id)

        if started:
            # Producer owns its OWN redis+engine: the request's connections close
            # when the tailer ends, but generation must outlive the request.
            prod_redis = await _get_redis()
            prod_engine = await _get_engine()

            async def _producer_with_cleanup():
                try:
                    await _run_producer(
                        redis=prod_redis, engine=prod_engine, body=body,
                        workspace_id=workspace_id, user_id=user.user_id,
                        team_id=user.team_id, sql_visible=sql_visible, cid=cid,
                    )
                finally:
                    await prod_redis.aclose()
                    await prod_engine.dispose()

            task = asyncio.create_task(_producer_with_cleanup())
            _PRODUCERS.add(task)
            task.add_done_callback(_PRODUCERS.discard)
    except Exception:
        await redis.aclose()
        await engine.dispose()
        raise

    async def event_generator():
        try:
            async for event in _tail_events(redis, cid, request):
                yield event
        finally:
            await redis.aclose()
            await engine.dispose()

    return EventSourceResponse(event_generator())


# ── Conversation endpoints ───────────────────────────────────────────────


@router.get("/conversations", summary="List recent conversations")
async def list_user_conversations(
    workspace_id: WorkspaceID,
    user: CurrentUser,
    limit: int = 20,
) -> list[dict]:
    """List recent conversations for the authenticated user."""
    redis = await _get_redis()
    try:
        conversations = await list_conversations(redis, workspace_id, user.user_id, limit)
        return [
            {
                "id": c.id,
                "title": c.title,
                "message_count": len(c.messages),
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in conversations
        ]
    finally:
        await redis.aclose()


@router.get("/conversations/{conversation_id}", summary="Get conversation details")
async def get_conversation_detail(
    conversation_id: str,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> dict:
    """Get full conversation with all messages."""
    redis = await _get_redis()
    try:
        conv = await get_conversation(redis, workspace_id, conversation_id)
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found",
            )
        return conv.model_dump()
    finally:
        await redis.aclose()


@router.get("/query/{conversation_id}/status", summary="Run status for a conversation")
async def get_run_status(
    conversation_id: str,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> dict:
    """Return {"status": "running"|"complete"|"error"|null}.

    The frontend uses this on load to decide: resume the live stream
    (running) or just render persisted history (complete/null).
    """
    redis = await _get_redis()
    try:
        # Ownership gate: only the conversation owner may read its run state.
        # Return 404 (not 403) on mismatch so we never confirm the cid exists.
        conv = await get_conversation(redis, workspace_id, conversation_id)
        if conv is None or conv.user_id != user.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return {"status": await run_store.get_status(redis, conversation_id)}
    finally:
        await redis.aclose()


@router.get("/query/{conversation_id}/stream", summary="Resume/tail a run's SSE stream")
async def resume_query_stream(
    conversation_id: str,
    request: Request,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> EventSourceResponse:
    """Re-attach to an in-flight (or just-finished) run and replay its events.

    Used by the frontend after a page refresh: it replays everything from the
    start of the run, then live-tails until the terminal event.
    """
    redis = await _get_redis()

    # Ownership gate: only the conversation owner may resume its stream. Return
    # 404 (not 403) on mismatch so we never confirm the cid exists, and never
    # replay gated SQL events to a non-owner.
    try:
        conv = await get_conversation(redis, workspace_id, conversation_id)
        if conv is None or conv.user_id != user.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
    except BaseException:
        await redis.aclose()
        raise

    async def event_generator():
        try:
            async for event in _tail_events(redis, conversation_id, request):
                yield event
        finally:
            await redis.aclose()

    return EventSourceResponse(event_generator())


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
)
async def delete_conversation_endpoint(
    conversation_id: str,
    workspace_id: WorkspaceID,
    user: CurrentUser,
):
    """Delete a conversation and its messages."""
    redis = await _get_redis()
    try:
        deleted = await delete_conversation(redis, workspace_id, conversation_id, user.user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found",
            )
    finally:
        await redis.aclose()
