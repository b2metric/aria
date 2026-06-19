"""Chat query API endpoint with SSE streaming.

POST /api/query — stream NL→SQL→chart pipeline via Server-Sent Events.
GET  /api/conversations — list recent conversations.
GET  /api/conversations/{id} — get conversation details.
DELETE /api/conversations/{id} — delete a conversation.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine
from sse_starlette.sse import EventSourceResponse

from backend.app.auth.dependencies import CurrentUser, WorkspaceID
from backend.app.core.config import get_settings
from backend.app.query import QueryRequest
from backend.app.query.conversation import (
    delete_conversation,
    get_conversation,
    list_conversations,
)
from backend.app.query.pipeline import process_query
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

    async def event_generator():
        try:
            async for event in process_query(
                redis=redis,
                engine=engine,
                request=body,
                workspace_id=workspace_id,
                user_id=user.user_id,
                team_id=user.team_id,
            ):
                if await request.is_disconnected():
                    logger.info("Client disconnected during SSE stream")
                    break
                yield event
        except Exception as exc:
            logger.exception("Unhandled error in query pipeline")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(exc)}),
            }
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
