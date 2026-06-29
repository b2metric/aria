"""The chart-type LLM must honor the per-customer/per-operation 'chart' model.

Gap: _build_chart hard-coded the platform default (settings.llm_model) for the
chart-type picker, so a customer's `operation_models["chart"]` override was
silently ignored (unlike sql_generation / insight / suggestion, which resolve
per-op). _build_chart now accepts the resolved chart LLM and forwards its
model / api_base / api_key, falling back to the platform default when none.
"""

from __future__ import annotations

import pytest

from agents.chart_types import AxisConfig, ChartConfig, ChartType
from backend.app.query import pipeline as P


class _FakePipelineResult:
    def __init__(self):
        self.config = ChartConfig(
            chart_type=ChartType.BAR,
            x=AxisConfig(column="REVENUE_BUCKET"),
            y=AxisConfig(column="NUM_LINES"),
            title="t",
            confidence=0.9,
        )
        self.png_bytes = None  # skip MinIO upload path
        self.csv_content = ""
        self.errors: list[str] = []


def _patch_run(monkeypatch):
    captured: dict = {}

    def _fake_run(*args, **kwargs):
        captured.update(kwargs)
        return _FakePipelineResult()

    monkeypatch.setattr(P, "run_chart_pipeline_sync", _fake_run)
    return captured


_ROWS = [{"REVENUE_BUCKET": "Same", "NUM_LINES": 1}]


class _ResolvedLLM:
    """Duck-typed stand-in for services.llm_resolver.ResolvedLLM."""

    def __init__(self, model, api_base, api_key):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key


def test_build_chart_uses_resolved_chart_model(monkeypatch):
    captured = _patch_run(monkeypatch)
    chart_llm = _ResolvedLLM(model="acme-chart-model", api_base="http://proxy:4000", api_key="vk-123")

    P._build_chart(rows=_ROWS, question="q", conversation_id="cid", chart_llm=chart_llm)

    assert captured["model_name"] == "acme-chart-model"
    assert captured["llm_base_url"] == "http://proxy:4000"
    assert captured["llm_api_key"] == "vk-123"


def test_build_chart_falls_back_to_platform_default(monkeypatch):
    captured = _patch_run(monkeypatch)
    from backend.app.core.config import get_settings

    s = get_settings()

    P._build_chart(rows=_ROWS, question="q", conversation_id="cid", chart_llm=None)

    assert captured["model_name"] == s.llm_model
    assert captured["llm_base_url"] == s.litellm_api_base


def test_build_chart_empty_resolved_key_falls_back(monkeypatch):
    # BYOK passthrough may leave api_key="" — must fall back, not send an empty key.
    captured = _patch_run(monkeypatch)
    from backend.app.core.config import get_settings

    s = get_settings()
    chart_llm = _ResolvedLLM(model="acme-chart-model", api_base="http://proxy:4000", api_key="")

    P._build_chart(rows=_ROWS, question="q", conversation_id="cid", chart_llm=chart_llm)

    assert captured["model_name"] == "acme-chart-model"
    assert captured["llm_api_key"] == (s.litellm_api_key or "sk-placeholder")
