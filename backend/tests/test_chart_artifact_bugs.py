"""Regression tests for two chart-pipeline bugs seen in the live chat logs.

Bug 1 (chart_llm): the chart-type picker sent ``response_format={"type":
"json_object"}`` to DeepSeek, but neither prompt contained the word "json".
DeepSeek hard-rejects that combo ("Prompt must contain the word 'json' ..."),
so chart selection silently degraded to a plain table on every query.

Bug 2 (artifact_store): ``_ensure_bucket`` called ``make_bucket(bucket,
region=...)``. The minio 7.2.20 SDK signature is ``make_bucket(bucket,
location=..., object_lock=...)`` — passing ``region`` raises TypeError, which
``except S3Error`` does NOT catch, so the chart artifact upload blew up.
"""

from __future__ import annotations

import json

import pytest

from agents import artifact_store as artifact_store_mod
from agents import chart_llm as chart_llm_mod

pytestmark = pytest.mark.asyncio


# ── Bug 2: make_bucket must use `location`, not `region` ─────────────


class _FakeMinioClient:
    """Mirrors the real minio 7.2.20 signatures: make_bucket takes `location`."""

    def __init__(self):
        self.made = []

    def bucket_exists(self, bucket_name):
        return False

    def make_bucket(self, bucket_name, location=None, object_lock=False):
        # Real SDK has no `region` kwarg — passing it would TypeError here too.
        self.made.append((bucket_name, location))


def test_ensure_bucket_uses_location_kwarg_not_region():
    store = artifact_store_mod.ArtifactStore(
        endpoint="localhost:9000", bucket="aria-artifacts", region="us-east-1"
    )
    fake = _FakeMinioClient()
    store._client = fake

    # Must not raise TypeError("unexpected keyword argument 'region'").
    store._ensure_bucket()

    assert fake.made == [("aria-artifacts", "us-east-1")]


# ── Bug 1: the prompt sent to the LLM must contain the word "json" ──


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


async def test_chart_llm_prompt_contains_json_for_deepseek(monkeypatch):
    captured = {}

    async def _fake_acompletion(*args, **kwargs):
        captured["messages"] = kwargs["messages"]
        captured["response_format"] = kwargs.get("response_format")
        return _FakeResponse(
            json.dumps(
                {
                    "chart_type": "bar",
                    "x_column": "REVENUE_BUCKET",
                    "y_column": "CURRENT_REVENUE",
                    "title": "Revenue by bucket",
                    "labels": {},
                    "reasoning": "categorical + numeric",
                    "confidence": 0.9,
                }
            )
        )

    monkeypatch.setattr(chart_llm_mod.litellm, "acompletion", _fake_acompletion)

    choice = await chart_llm_mod._run_chart_llm("## User Question\nrevenue?\n")

    # DeepSeek requires the literal word "json" somewhere in the prompt when
    # response_format=json_object is set.
    combined = " ".join(m["content"] for m in captured["messages"]).lower()
    assert captured["response_format"] == {"type": "json_object"}
    assert "json" in combined

    # And the valid response parses into a real (non-fallback) choice.
    assert choice.chart_type == "bar"
    assert choice.confidence == 0.9
