"""Unit tests for the record_llm_usage metering wrapper (Sprint 1)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services import token as token_svc


@pytest.mark.asyncio
async def test_get_quotas_tolerates_str_period() -> None:
    """REGRESSION: the native PG enum ``period`` column comes back as a plain str at
    runtime, so ``q.period.value`` raised AttributeError. Once the identity fix made
    the token path actually run, that fail-closed EVERY query. get_quotas must read
    the period defensively and still apply the DB quota."""

    class _Quota:
        period = "daily"  # str, not QuotaPeriod
        user_id = None
        team_id = None
        token_limit = 12345

    scalars = MagicMock()
    scalars.all.return_value = [_Quota()]
    result = MagicMock()
    result.scalars.return_value = scalars
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    svc = token_svc.TokenService(db=db, redis=AsyncMock())
    quotas = await svc.get_quotas(uuid.uuid4(), uuid.uuid4(), None)
    assert quotas["customer"] == 12345  # applied, no AttributeError


@pytest.mark.asyncio
async def test_record_llm_usage_meters_with_operation_and_cost() -> None:
    # 1M prompt tokens of deepseek-chat @ 0.27 USD/1M → cost 0.27.
    resp = {"model": "deepseek-chat", "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 0}}
    with patch.object(token_svc.TokenService, "record_usage", new=AsyncMock()) as rec:
        await token_svc.record_llm_usage(
            db=AsyncMock(),
            redis=AsyncMock(),
            customer_uuid=uuid.uuid4(),
            user_uuid=uuid.uuid4(),
            team_uuid=None,
            conversation_id="cid-1",
            operation="insight",
            response=resp,
        )
    rec.assert_awaited_once()
    kwargs = rec.await_args.kwargs
    assert kwargs["operation"] == "insight"
    assert kwargs["conversation_id"] == "cid-1"
    assert kwargs["model"] == "deepseek-chat"
    assert kwargs["prompt_tokens"] == 1_000_000
    assert kwargs["cost_usd"] == Decimal("0.27")


@pytest.mark.asyncio
async def test_record_llm_usage_noop_without_customer() -> None:
    with patch.object(token_svc.TokenService, "record_usage", new=AsyncMock()) as rec:
        await token_svc.record_llm_usage(
            db=AsyncMock(),
            redis=AsyncMock(),
            customer_uuid=None,
            user_uuid=None,
            team_uuid=None,
            conversation_id=None,
            operation="chart",
            response={"usage": {"prompt_tokens": 5, "completion_tokens": 5}, "model": "x"},
        )
    rec.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_llm_usage_noop_on_zero_tokens() -> None:
    with patch.object(token_svc.TokenService, "record_usage", new=AsyncMock()) as rec:
        await token_svc.record_llm_usage(
            db=AsyncMock(),
            redis=AsyncMock(),
            customer_uuid=uuid.uuid4(),
            user_uuid=uuid.uuid4(),
            team_uuid=None,
            conversation_id="c",
            operation="chart",
            response={"usage": {"prompt_tokens": 0, "completion_tokens": 0}, "model": "x"},
        )
    rec.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_llm_usage_swallows_errors() -> None:
    # A metering failure must never bubble into the turn.
    with patch.object(
        token_svc.TokenService, "record_usage", new=AsyncMock(side_effect=RuntimeError("boom"))
    ):
        await token_svc.record_llm_usage(
            db=AsyncMock(),
            redis=AsyncMock(),
            customer_uuid=uuid.uuid4(),
            user_uuid=uuid.uuid4(),
            team_uuid=None,
            conversation_id="c",
            operation="insight",
            response={"usage": {"prompt_tokens": 1, "completion_tokens": 1}, "model": "deepseek-chat"},
        )  # must not raise
