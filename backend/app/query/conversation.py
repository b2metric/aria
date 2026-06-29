"""Conversation storage backed by Redis."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from redis.asyncio import Redis

from backend.app.query import Conversation, ConversationMessage, _utcnow_iso

logger = logging.getLogger(__name__)

CONVERSATION_PREFIX = "aria:conv:"
CONVERSATION_LIST_PREFIX = "aria:conv_list:"
CONVERSATION_TTL = 60 * 60 * 24 * 30  # 30 days


def _conv_key(workspace_id: str, conversation_id: str) -> str:
    return f"{CONVERSATION_PREFIX}{workspace_id}:{conversation_id}"


def _list_key(workspace_id: str, user_id: str) -> str:
    return f"{CONVERSATION_LIST_PREFIX}{workspace_id}:{user_id}"


async def get_conversation(
    redis: Redis, workspace_id: str, conversation_id: str
) -> Conversation | None:
    """Retrieve a conversation from Redis."""
    key = _conv_key(workspace_id, conversation_id)
    raw = await redis.get(key)
    if raw is None:
        return None
    return Conversation.model_validate_json(raw)


async def save_conversation(redis: Redis, conversation: Conversation) -> None:
    """Save a conversation to Redis."""
    key = _conv_key(conversation.workspace_id, conversation.id)
    conversation.updated_at = _utcnow_iso()
    await redis.set(key, conversation.model_dump_json(), ex=CONVERSATION_TTL)
    # Add to user's conversation list. Use an aware UTC timestamp: naive
    # utcnow().timestamp() is interpreted as LOCAL time, producing a wrong epoch
    # score (off by the host's UTC offset).
    list_key = _list_key(conversation.workspace_id, conversation.user_id)
    await redis.zadd(list_key, {conversation.id: datetime.now(UTC).timestamp()})


async def append_message(
    redis: Redis,
    workspace_id: str,
    conversation_id: str,
    message: ConversationMessage,
) -> Conversation:
    """Append a message to an existing conversation."""
    conv = await get_conversation(redis, workspace_id, conversation_id)
    if conv is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    conv.messages.append(message)
    # Auto-generate title from first user message
    if len(conv.messages) == 1 and message.role == "user":
        conv.title = message.content[:80] + ("..." if len(message.content) > 80 else "")
    await save_conversation(redis, conv)
    return conv


async def list_conversations(
    redis: Redis, workspace_id: str, user_id: str, limit: int = 20
) -> list[Conversation]:
    """List recent conversations for a user, newest first."""
    list_key = _list_key(workspace_id, user_id)
    conv_ids = await redis.zrevrange(list_key, 0, limit - 1)
    if not conv_ids:
        return []

    pipeline = redis.pipeline()
    for cid in conv_ids:
        pipeline.get(_conv_key(workspace_id, cid.decode() if isinstance(cid, bytes) else cid))
    results = await pipeline.execute()

    conversations: list[Conversation] = []
    for raw in results:
        if raw:
            conversations.append(Conversation.model_validate_json(raw))
    return conversations


async def list_workspace_conversations(
    redis: Redis, workspace_id: str, limit: int = 50
) -> list[Conversation]:
    """List every conversation in a workspace, newest first (admin debug view).

    Scans ``aria:conv:{workspace_id}:*`` so it spans all users in the workspace
    (the per-user list keys are intentionally not used here). The trailing colon
    delimiter prevents a prefix-colliding workspace slug from leaking in.
    """
    pattern = f"{CONVERSATION_PREFIX}{workspace_id}:*"
    conversations: list[Conversation] = []
    async for key in redis.scan_iter(match=pattern):
        raw = await redis.get(key)
        if raw:
            conversations.append(Conversation.model_validate_json(raw))
    conversations.sort(key=lambda c: c.updated_at, reverse=True)
    return conversations[:limit]


async def delete_conversation(
    redis: Redis, workspace_id: str, conversation_id: str, user_id: str
) -> bool:
    """Delete a conversation and remove from user's list."""
    key = _conv_key(workspace_id, conversation_id)
    list_key = _list_key(workspace_id, user_id)
    deleted = await redis.delete(key)
    # Ensure zrem succeeds whether conversation_id is passed directly or needs decoding if fetched raw
    zrem_res = await redis.zrem(list_key, conversation_id)
    return deleted > 0 or zrem_res > 0
