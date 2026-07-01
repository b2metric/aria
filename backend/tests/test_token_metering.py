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
async def test_get_token_usage_includes_cost_usd(monkeypatch) -> None:
    """Sprint 2 Task 11: the /admin/tokens/usage rows expose ``cost_usd`` so the
    admin usage table can show a Cost column alongside tokens."""
    from backend.app.api.endpoints.admin import tokens as tokens_ep

    class _Row:
        id = uuid.uuid4()
        user_id = uuid.uuid4()
        usage_date = "2026-07-01"
        tokens_used = 9504
        model = "claude-sonnet"
        cost_usd = Decimal("0.0300")

    scalars = MagicMock()
    scalars.all.return_value = [_Row()]
    result = MagicMock()
    result.scalars.return_value = scalars
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    async def _fake_resolve(_user, _db):
        return uuid.uuid4()

    monkeypatch.setattr(tokens_ep, "resolve_customer_id", _fake_resolve)

    user = MagicMock()
    user.can_admin = True
    rows = await tokens_ep.get_token_usage(limit=10, current_user=user, db=db)
    assert rows[0]["tokens_used"] == 9504
    assert rows[0]["cost_usd"] == 0.03


@pytest.mark.asyncio
async def test_record_llm_usage_meters_with_operation_and_cost(monkeypatch) -> None:
    # No response_cost on the payload → falls back to compute_cost (LiteLLM's own pricing,
    # stubbed here for determinism after the local PRICING map was removed in Task 15).
    from backend.app.services import llm_cost

    monkeypatch.setattr(llm_cost, "_litellm_cost", lambda *a, **k: 0.27)
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
async def test_record_llm_usage_prefers_response_cost_and_marks_priced() -> None:
    # LiteLLM reported a real cost → use it verbatim, mark priced=True, ignore the local map.
    resp = {
        "model": "claude-sonnet",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        "_response_cost": "0.0304",
    }
    with patch.object(token_svc.TokenService, "record_usage", new=AsyncMock()) as rec:
        await token_svc.record_llm_usage(
            db=AsyncMock(), redis=AsyncMock(), customer_uuid=uuid.uuid4(),
            user_uuid=uuid.uuid4(), team_uuid=None, conversation_id="c",
            operation="sql_generation", response=resp,
        )
    kwargs = rec.await_args.kwargs
    assert kwargs["cost_usd"] == Decimal("0.0304")
    assert kwargs["priced"] is True


@pytest.mark.asyncio
async def test_record_llm_usage_zero_response_cost_is_unpriced_but_counted() -> None:
    # Self-hosted model routed via LiteLLM → response_cost 0 → tokens still recorded, priced=False.
    resp = {
        "model": "local-embed",
        "usage": {"prompt_tokens": 20, "completion_tokens": 0},
        "_response_cost": "0",
    }
    with patch.object(token_svc.TokenService, "record_usage", new=AsyncMock()) as rec:
        await token_svc.record_llm_usage(
            db=AsyncMock(), redis=AsyncMock(), customer_uuid=uuid.uuid4(),
            user_uuid=None, team_uuid=None, conversation_id=None,
            operation="mem0_embedding", response=resp,
        )
    rec.assert_awaited_once()
    kwargs = rec.await_args.kwargs
    assert kwargs["prompt_tokens"] == 20
    assert kwargs["cost_usd"] == Decimal("0")
    assert kwargs["priced"] is False


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
