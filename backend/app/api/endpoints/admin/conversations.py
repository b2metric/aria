"""Admin: conversation debug view (TIER 3 item 23 — QueryTrace).

Lets an admin list every conversation in their workspace and open one to inspect
its per-turn QueryTrace (model, row_count, sql_generated, memory context). This
is the Sprint-9 conversation-debug surface that was never built.

Workspace-scoped: an admin only sees conversations in their own workspace (the
slug from their JWT), preserving tenant isolation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis

from backend.app.auth.dependencies import CurrentUser
from backend.app.auth.models import Role
from backend.app.auth.rbac import require_role
from backend.app.core.config import get_settings
from backend.app.query.conversation import get_conversation, list_workspace_conversations

router = APIRouter()


def _get_redis() -> Redis:
    """Redis connection for conversation storage (patchable in tests)."""
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


@router.get("", summary="List all conversations in the workspace (admin debug)")
async def list_all_conversations(
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
    limit: int = 50,
) -> list[dict]:
    """List conversation summaries across all users in the admin's workspace."""
    redis = _get_redis()
    try:
        convs = await list_workspace_conversations(redis, user.workspace_id, limit=limit)
        return [
            {
                "id": c.id,
                "user_id": c.user_id,
                "title": c.title,
                "message_count": len(c.messages),
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in convs
        ]
    finally:
        await redis.aclose()


@router.get("/{conversation_id}", summary="Get a conversation with its QueryTraces (admin debug)")
async def get_conversation_detail_admin(
    conversation_id: str,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> dict:
    """Return a full conversation (messages include their per-turn ``trace``).

    Scoped to the admin's workspace: a cid in another tenant resolves to None →
    404, so an admin can never read another workspace's conversation.
    """
    redis = _get_redis()
    try:
        conv = await get_conversation(redis, user.workspace_id, conversation_id)
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found",
            )
        return conv.model_dump()
    finally:
        await redis.aclose()
