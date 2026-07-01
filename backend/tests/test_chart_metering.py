"""Unit tests: the chart LLM proposer surfaces token usage for metering."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from agents import chart_llm


@pytest.mark.asyncio
async def test_run_chart_llm_attaches_usage() -> None:
    class _Msg:
        content = json.dumps({"chart_type": "bar", "x_column": "a", "y_column": "b"})

    class _Choice:
        message = _Msg()

    class _Usage:
        prompt_tokens = 40
        completion_tokens = 12

    class _Resp:
        choices = [_Choice()]
        usage = _Usage()
        model = "gemini-chat"

    with patch.object(chart_llm, "litellm") as m:
        m.acompletion = AsyncMock(return_value=_Resp())
        choice = await chart_llm._run_chart_llm("prompt", model_name="gemini-chat")

    assert choice.usage == {
        "prompt_tokens": 40,
        "completion_tokens": 12,
        "model": "gemini-chat",
        "_response_cost": None,
    }


@pytest.mark.asyncio
async def test_propose_chart_llm_returns_config_and_usage() -> None:
    stub = chart_llm.LlmChartChoice(
        chart_type="bar", usage={"prompt_tokens": 1, "completion_tokens": 2, "model": "x"}
    )
    with patch.object(chart_llm, "_run_chart_llm", new=AsyncMock(return_value=stub)):
        config, usage = await chart_llm.propose_chart_llm([{"a": 1, "b": 2}], question="q")

    assert usage == {"prompt_tokens": 1, "completion_tokens": 2, "model": "x"}
    assert config.chart_type.value == "bar"


@pytest.mark.asyncio
async def test_run_chart_llm_failure_has_no_usage() -> None:
    with patch.object(chart_llm, "litellm") as m:
        m.acompletion = AsyncMock(side_effect=RuntimeError("boom"))
        choice = await chart_llm._run_chart_llm("prompt")
    assert choice.usage is None
    assert choice.chart_type == "table"
