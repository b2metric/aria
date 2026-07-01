"""Admin: conversation debug view (TIER 3 item 23 — QueryTrace).

Lets an admin list every conversation in their workspace and open one to inspect
its per-turn QueryTrace (model, row_count, sql_generated, memory context). This
is the Sprint-9 conversation-debug surface that was never built.

Workspace-scoped: an admin only sees conversations in their own workspace (the
slug from their JWT), preserving tenant isolation.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import func, select, text

from backend.app.auth.dependencies import CurrentUser
from backend.app.auth.models import Role
from backend.app.auth.rbac import require_role
from backend.app.core.config import get_settings
from backend.app.db.session import get_sessionmaker
from backend.app.models.token import TokenUsageEvent
from backend.app.query.conversation import get_conversation, list_workspace_conversations

log = logging.getLogger("aria.admin.conversations")
router = APIRouter()


def _get_redis() -> Redis:
    """Redis connection for conversation storage (patchable in tests)."""
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


def _with_token_totals(
    summaries: list[dict], totals: dict[str, dict]
) -> list[dict]:
    """Attach cumulative ``total_tokens`` + ``cost_usd`` + ``unpriced_tokens`` to each
    conversation summary.

    ``totals`` maps ``conversation_id`` → ``{"tokens": int, "cost": float, "unpriced": int}``
    (summed from ``token_usage_events``; ``unpriced`` is the self-hosted / $0-cost token
    share). A conversation with no LLM events yet — or an entry missing the ``unpriced``
    split — gets zeros, never a missing key, so the admin table can always render the
    columns.
    """
    return [
        {
            **s,
            "total_tokens": int(totals.get(s["id"], {}).get("tokens", 0) or 0),
            "cost_usd": float(totals.get(s["id"], {}).get("cost", 0) or 0),
            "unpriced_tokens": int(totals.get(s["id"], {}).get("unpriced", 0) or 0),
        }
        for s in summaries
    ]


async def _conversation_token_totals(
    workspace_id: str, conversation_ids: list[str]
) -> dict[str, dict]:
    """Sum tokens + USD cost per conversation from ``token_usage_events``.

    Tenant-scoped by the workspace's ``customer_id``. Best-effort: any failure (DB down,
    slug unresolved) returns an empty map so the conversation list still renders.
    """
    if not conversation_ids:
        return {}
    try:
        async with get_sessionmaker()() as session:
            row = (
                await session.execute(
                    text("SELECT id FROM customers WHERE slug = :slug"),
                    {"slug": workspace_id},
                )
            ).fetchone()
            if not row:
                return {}
            customer_id = row[0]

            result = await session.execute(
                select(
                    TokenUsageEvent.conversation_id,
                    TokenUsageEvent.priced,
                    func.sum(TokenUsageEvent.total_tokens),
                    func.sum(TokenUsageEvent.cost_usd),
                )
                .where(
                    TokenUsageEvent.customer_id == customer_id,
                    TokenUsageEvent.conversation_id.in_(conversation_ids),
                )
                .group_by(TokenUsageEvent.conversation_id, TokenUsageEvent.priced)
            )
            totals: dict[str, dict] = {}
            for cid, is_priced, tokens, cost in result.all():
                tokens = int(tokens or 0)
                entry = totals.setdefault(cid, {"tokens": 0, "cost": 0.0, "unpriced": 0})
                entry["tokens"] += tokens
                entry["cost"] += float(cost or 0)  # priced rows carry the cost
                if not is_priced:
                    entry["unpriced"] += tokens
            return totals
    except Exception as exc:  # noqa: BLE001 — totals are advisory, never break the list
        log.warning("Conversation token-total aggregation failed: %s", exc)
        return {}


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
        summaries = [
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

    totals = await _conversation_token_totals(
        user.workspace_id, [s["id"] for s in summaries]
    )
    return _with_token_totals(summaries, totals)


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
