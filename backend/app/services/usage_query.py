"""Daily token/cost aggregates derived from ``token_usage_events``.

Replaces the ``token_usage_daily`` rollup: the event table is a superset (per
operation / conversation / priced), so every daily figure is a SUM query here.
All figures are scoped to a UTC calendar day via ``created_at`` (a timestamptz).
Cost sums over all rows — unpriced (self-hosted) rows contribute 0, so the cost
total stays priced-only naturally.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Date as SA_Date
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.token import TokenUsageEvent


def _day_bounds(on_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(on_date, time.min, tzinfo=UTC)
    return start, start + timedelta(days=1)


async def daily_tokens_cost(
    session: AsyncSession,
    *,
    customer_id: uuid.UUID,
    on_date: date,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Return ``{"tokens": int, "cost": Decimal}`` for ``customer_id`` on ``on_date``.

    Scope by ``user_id`` for the per-user dashboard figures; omit it for the
    workspace-wide totals (which then also include system ops, matching Task 18).
    """
    start, end = _day_bounds(on_date)
    conds = [
        TokenUsageEvent.customer_id == customer_id,
        TokenUsageEvent.created_at >= start,
        TokenUsageEvent.created_at < end,
    ]
    if user_id is not None:
        conds.append(TokenUsageEvent.user_id == user_id)

    tokens = (
        await session.scalar(select(func.sum(TokenUsageEvent.total_tokens)).where(*conds)) or 0
    )
    cost = await session.scalar(select(func.sum(TokenUsageEvent.cost_usd)).where(*conds)) or 0
    return {"tokens": int(tokens), "cost": Decimal(str(cost))}


async def recent_daily_rows(
    session: AsyncSession,
    *,
    customer_id: uuid.UUID,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Per-(day, user, model) rollup rows for the admin usage table — the
    events-derived replacement for listing ``token_usage_daily`` rows."""
    day = cast(TokenUsageEvent.created_at, SA_Date)
    result = await session.execute(
        select(
            TokenUsageEvent.user_id,
            day.label("usage_date"),
            TokenUsageEvent.model,
            func.sum(TokenUsageEvent.total_tokens),
            func.sum(TokenUsageEvent.cost_usd),
        )
        .where(TokenUsageEvent.customer_id == customer_id)
        .group_by(TokenUsageEvent.user_id, day, TokenUsageEvent.model)
        .order_by(day.desc())
        .limit(limit)
    )
    return [
        {
            "user_id": str(uid) if uid else None,
            "usage_date": str(d),
            "model": model,
            "tokens_used": int(tok or 0),
            "cost_usd": float(cost or 0),
        }
        for uid, d, model, tok, cost in result.all()
    ]
