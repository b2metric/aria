"""Unit tests for the LLM usage+cost util (Sprint 1)."""

from __future__ import annotations

from decimal import Decimal

from backend.app.services import llm_cost


def test_compute_cost_known_model_exact() -> None:
    # deepseek-chat seeded at (0.27, 1.10) USD / 1M tokens.
    cost = llm_cost.compute_cost("deepseek-chat", 1_000_000, 1_000_000)
    assert cost == Decimal("0.27") + Decimal("1.10")


def test_compute_cost_partial_tokens() -> None:
    # 500k prompt @0.27/1M = 0.135 ; 0 completion.
    cost = llm_cost.compute_cost("deepseek-chat", 500_000, 0)
    assert cost == Decimal("0.135")


def test_compute_cost_normalizes_alias_prefixes() -> None:
    # `custom:litellm:` and provider `deepseek/` prefixes resolve to the same price.
    base = llm_cost.compute_cost("deepseek-chat", 1_000_000, 0)
    assert llm_cost.compute_cost("custom:litellm:deepseek-chat", 1_000_000, 0) == base
    assert llm_cost.compute_cost("deepseek/deepseek-chat", 1_000_000, 0) == base


def test_compute_cost_unknown_model_is_zero(monkeypatch) -> None:
    # Unknown model + no LiteLLM fallback → 0 (never crash).
    monkeypatch.setattr(llm_cost, "_litellm_cost", lambda *a, **k: None)
    assert llm_cost.compute_cost("totally-unknown-xyz", 100, 100) == Decimal("0")


def test_compute_cost_falls_back_to_litellm(monkeypatch) -> None:
    monkeypatch.setattr(llm_cost, "_litellm_cost", lambda *a, **k: 0.5)
    assert llm_cost.compute_cost("some-openai-model", 10, 10) == Decimal("0.5")


def test_extract_usage_from_proxy_json() -> None:
    resp = {"model": "deepseek-chat", "usage": {"prompt_tokens": 12, "completion_tokens": 34}}
    assert llm_cost.extract_usage(resp) == {
        "prompt_tokens": 12,
        "completion_tokens": 34,
        "model": "deepseek-chat",
    }


def test_extract_usage_from_sdk_object() -> None:
    class _Usage:
        prompt_tokens = 5
        completion_tokens = 7

    class _Resp:
        usage = _Usage()
        model = "claude-opus"

    assert llm_cost.extract_usage(_Resp()) == {
        "prompt_tokens": 5,
        "completion_tokens": 7,
        "model": "claude-opus",
    }


def test_extract_usage_missing_usage_is_zeroed() -> None:
    assert llm_cost.extract_usage({}) == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "model": "unknown",
    }


# ── Sprint 2.5 Task 13: extract_cost (LiteLLM response_cost) ──────────────────


def test_extract_cost_from_sdk_hidden_params() -> None:
    class _Resp:
        _hidden_params = {"response_cost": 0.0304}

    assert llm_cost.extract_cost(_Resp()) == Decimal("0.0304")


def test_extract_cost_from_dict_response_cost_key() -> None:
    # httpx path: the x-litellm-response-cost header is stashed as `_response_cost`.
    assert llm_cost.extract_cost({"_response_cost": "2.1e-06"}) == Decimal("2.1e-06")


def test_extract_cost_from_dict_hidden_params() -> None:
    assert llm_cost.extract_cost({"_hidden_params": {"response_cost": 0.5}}) == Decimal("0.5")


def test_extract_cost_absent_returns_none() -> None:
    assert llm_cost.extract_cost({"usage": {"prompt_tokens": 5}}) is None
    assert llm_cost.extract_cost(object()) is None


def test_extract_cost_zero_is_returned_not_none() -> None:
    # A self-hosted model routed via LiteLLM reports response_cost 0.0 — that is a real
    # (unpriced) signal, distinct from "no cost field present".
    assert llm_cost.extract_cost({"_response_cost": "0"}) == Decimal("0")
