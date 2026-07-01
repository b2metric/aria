"""Part B: derive daily token/cost aggregates from token_usage_events.

Replaces the token_usage_daily rollup. token_usage_events is a superset (per
operation / conversation / priced), so all daily figures are SUM queries here.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.services import usage_query


@pytest.mark.asyncio
async def test_daily_tokens_cost_sums_events() -> None:
    db = AsyncMock()
    # helper makes two scalar calls: SUM(total_tokens) then SUM(cost_usd)
    db.scalar = AsyncMock(side_effect=[12500, Decimal("0.0623")])
    out = await usage_query.daily_tokens_cost(
        db, customer_id=uuid.uuid4(), on_date=date(2026, 7, 1)
    )
    assert out["tokens"] == 12500
    assert out["cost"] == Decimal("0.0623")


@pytest.mark.asyncio
async def test_daily_tokens_cost_defaults_to_zero_when_no_events() -> None:
    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=[None, None])
    out = await usage_query.daily_tokens_cost(
        db, customer_id=uuid.uuid4(), on_date=date(2026, 7, 1), user_id=uuid.uuid4()
    )
    assert out["tokens"] == 0
    assert out["cost"] == Decimal("0")


@pytest.mark.asyncio
async def test_recent_daily_rows_groups_events_by_day_user_model() -> None:
    uid = uuid.uuid4()
    # (user_id, day, model, sum_tokens, sum_cost) as the GROUP BY yields
    rows = [(uid, date(2026, 7, 1), "deepseek-chat", 836, Decimal("0.000320"))]
    result = MagicMock()
    result.all.return_value = rows
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    out = await usage_query.recent_daily_rows(db, customer_id=uuid.uuid4(), limit=10)

    assert out[0]["user_id"] == str(uid)
    assert out[0]["usage_date"] == "2026-07-01"
    assert out[0]["model"] == "deepseek-chat"
    assert out[0]["tokens_used"] == 836
    assert out[0]["cost_usd"] == 0.00032
