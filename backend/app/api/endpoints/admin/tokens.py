"""Admin API for managing token quotas and tracking usage."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.auth.dependencies import UserContext, get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.token import TokenQuota, TokenUsageDaily, TokenUsageEvent
from backend.app.schemas.token import TokenQuotaCreate, TokenQuotaResponse, TokenQuotaUpdate

log = logging.getLogger("aria.admin.tokens")
router = APIRouter()


async def get_db() -> AsyncSession:  # type: ignore[misc, reportReturnType]
    maker: async_sessionmaker[AsyncSession] = get_sessionmaker()
    async with maker() as session:
        yield session  # pyright: ignore[reportReturnType]


async def resolve_customer_id(current_user: UserContext, db: AsyncSession) -> uuid.UUID:
    """Resolve the customer UUID from the workspace slug in the JWT."""
    from backend.app.models.organization import Customer

    workspace_slug = getattr(current_user, "workspace_id", None)
    if workspace_slug:
        result = await db.execute(select(Customer.id).where(Customer.slug == workspace_slug))
        customer_uuid = result.scalar_one_or_none()
        if customer_uuid:
            return customer_uuid

        try:
            return uuid.UUID(str(workspace_slug))
        except (ValueError, AttributeError):
            pass

    raise HTTPException(
        status_code=400,
        detail="Cannot resolve customer from workspace context",
    )


@router.get("/quotas", response_model=list[TokenQuotaResponse])
async def list_quotas(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all token quotas for the workspace."""
    if not current_user.can_admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    customer_id = await resolve_customer_id(current_user, db)

    result = await db.execute(select(TokenQuota).where(TokenQuota.customer_id == customer_id))
    return result.scalars().all()


@router.post("/quotas", response_model=TokenQuotaResponse)
async def create_quota(
    payload: TokenQuotaCreate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new token quota."""
    if not current_user.can_admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    # Only DAILY quotas are enforced (the Redis counters are day-keyed). Reject
    # non-daily periods loudly instead of silently ignoring them at check time.
    period_value = str(getattr(payload.period, "value", payload.period)).lower()
    if period_value != "daily":
        raise HTTPException(
            status_code=422,
            detail=(
                f"Token quota period '{period_value}' is not enforced yet — only 'daily' "
                "is supported. Create a daily quota (monthly enforcement is a follow-up)."
            ),
        )

    customer_id = await resolve_customer_id(current_user, db)

    # Ensure no duplicate (same scope) exists
    query = select(TokenQuota).where(
        TokenQuota.customer_id == customer_id,
        TokenQuota.team_id == payload.team_id,
        TokenQuota.user_id == payload.user_id,
        TokenQuota.period == payload.period,
    )
    result = await db.execute(query)
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="Quota for this scope already exists")

    quota = TokenQuota(
        customer_id=customer_id,
        team_id=payload.team_id,
        user_id=payload.user_id,
        period=payload.period,
        token_limit=payload.token_limit,
        is_active=payload.is_active,
    )
    db.add(quota)
    await db.commit()
    await db.refresh(quota)
    return quota


@router.patch("/quotas/{quota_id}", response_model=TokenQuotaResponse)
async def update_quota(
    quota_id: uuid.UUID,
    payload: TokenQuotaUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing token quota."""
    if not current_user.can_admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    customer_id = await resolve_customer_id(current_user, db)

    result = await db.execute(
        select(TokenQuota).where(TokenQuota.id == quota_id, TokenQuota.customer_id == customer_id)
    )
    quota = result.scalars().first()

    if not quota:
        raise HTTPException(status_code=404, detail="Quota not found")

    if payload.token_limit is not None:
        quota.token_limit = payload.token_limit
    if payload.is_active is not None:
        quota.is_active = payload.is_active

    await db.commit()
    await db.refresh(quota)
    return quota


@router.delete("/quotas/{quota_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quota(
    quota_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a token quota."""
    if not current_user.can_admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    customer_id = await resolve_customer_id(current_user, db)

    result = await db.execute(
        select(TokenQuota).where(TokenQuota.id == quota_id, TokenQuota.customer_id == customer_id)
    )
    quota = result.scalars().first()

    if not quota:
        raise HTTPException(status_code=404, detail="Quota not found")

    await db.delete(quota)
    await db.commit()


@router.get("/usage")
async def get_token_usage(
    limit: int = 100,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get daily token usage records for the workspace."""
    if not current_user.can_admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    customer_id = await resolve_customer_id(current_user, db)

    result = await db.execute(
        select(TokenUsageDaily)
        .where(TokenUsageDaily.customer_id == customer_id)
        .order_by(TokenUsageDaily.usage_date.desc(), TokenUsageDaily.created_at.desc())
        .limit(limit)
    )
    records = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id),
            "usage_date": str(r.usage_date),
            "tokens_used": r.tokens_used,
            "model": r.model,
            "cost_usd": float(r.cost_usd or 0),
        }
        for r in records
    ]


@router.get("/usage/summary")
async def get_token_usage_summary(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Priced vs unpriced token subtotals (+ priced cost) for the workspace.

    Aggregated from the granular ``token_usage_events`` table grouped by ``priced``
    so unpriced / self-hosted calls (which cost $0, and for system ops carry
    ``user_id=NULL``) are still counted. ``cost_usd`` sums over priced rows only.
    """
    if not current_user.can_admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    customer_id = await resolve_customer_id(current_user, db)

    result = await db.execute(
        select(
            TokenUsageEvent.priced,
            func.sum(TokenUsageEvent.total_tokens),
            func.sum(TokenUsageEvent.cost_usd),
        )
        .where(TokenUsageEvent.customer_id == customer_id)
        .group_by(TokenUsageEvent.priced)
    )

    priced_tokens = 0
    unpriced_tokens = 0
    cost = 0.0
    for is_priced, tokens, row_cost in result.all():
        tokens = int(tokens or 0)
        if is_priced:
            priced_tokens = tokens
            cost += float(row_cost or 0)  # cost is priced-only
        else:
            unpriced_tokens = tokens

    return {
        "priced_tokens": priced_tokens,
        "unpriced_tokens": unpriced_tokens,
        "total_tokens": priced_tokens + unpriced_tokens,
        "cost_usd": cost,
    }
