"""Tests for insight/suggestions generation credential handling.

Regression guard for the bug where a resolved LLM with an empty ``api_key``
caused ``litellm.acompletion`` (forced ``custom_llm_provider="openai"``) to fail
client-side with "Missing credentials", silently degrading every answer to the
fallback summary "Data retrieved successfully." with no suggestions.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.query.llm_insight import generate_insight_and_suggestions
from backend.app.services.llm_resolver import ResolvedLLM

pytestmark = pytest.mark.asyncio


def _resolved(api_key: str) -> ResolvedLLM:
    return ResolvedLLM(
        api_base="http://litellm:4000",
        api_key=api_key,
        model="deepseek-chat",
        custom_llm_provider="litellm",
        source="customer_byok",
        temperature=0.0,
        max_tokens=1000,
        operation="insight",
    )


def _completion(content: str) -> MagicMock:
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=content))]
    return resp


async def test_empty_resolved_key_falls_back_to_a_usable_key():
    """A ResolvedLLM with an empty api_key must NOT be sent verbatim — the call
    must receive a non-empty key (settings key / placeholder), like the SQL path."""
    payload = json.dumps({"summary": "ok", "suggestions": ["a", "b", "c"]})
    with patch(
        "backend.app.query.llm_insight.litellm.acompletion",
        new=AsyncMock(return_value=_completion(payload)),
    ) as mock_call:
        await generate_insight_and_suggestions(
            question="q", sql="SELECT 1", data_rows=[{"n": 1}], llm=_resolved("")
        )
    sent_key = mock_call.call_args.kwargs["api_key"]
    assert sent_key, "empty api_key must be replaced with a usable fallback key"


async def test_happy_path_returns_parsed_summary_and_three_suggestions():
    payload = json.dumps(
        {"summary": "Revenue grew.", "suggestions": ["a", "b", "c", "d"]}
    )
    with patch(
        "backend.app.query.llm_insight.litellm.acompletion",
        new=AsyncMock(return_value=_completion(payload)),
    ):
        out = await generate_insight_and_suggestions(
            question="q", sql="s", data_rows=[{"x": 1}], llm=_resolved("sk-real")
        )
    assert out["summary"] == "Revenue grew."
    assert out["suggestions"] == ["a", "b", "c"]  # capped at 3


async def test_llm_failure_returns_graceful_fallback():
    with patch(
        "backend.app.query.llm_insight.litellm.acompletion",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        out = await generate_insight_and_suggestions(
            question="q", sql="s", data_rows=[], llm=_resolved("sk-real")
        )
    assert out["summary"] == "Data retrieved successfully."
    assert out["suggestions"] == []
