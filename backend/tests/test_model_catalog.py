"""Unit tests for the LLM model-catalog mapping (Sprint 2)."""

from __future__ import annotations

from backend.app.api.endpoints.admin.llm_config import (
    ModelCatalogEntry,
    _infer_provider,
    _map_catalog,
)


def test_infer_provider() -> None:
    assert _infer_provider("claude-opus") == "anthropic"
    assert _infer_provider("deepseek-chat") == "deepseek"
    assert _infer_provider("gemini-reasoner") == "gemini"
    assert _infer_provider("glm-4") == "glm"
    assert _infer_provider("text-embedding-3-small") == "openai"
    assert _infer_provider("weird-model") == "other"


def test_map_catalog_dedupes_and_drops_custom_alias() -> None:
    raw = {
        "data": [
            {"id": "claude-opus"},
            {"id": "custom:litellm:claude-opus"},  # dropped
            {"id": "deepseek-chat"},
            {"id": "deepseek-chat"},  # dedup
            {"id": None},  # skipped
            "not-a-dict",  # skipped
        ]
    }
    out = _map_catalog(raw)
    # sorted by (provider, id): anthropic < deepseek
    assert [e.id for e in out] == ["claude-opus", "deepseek-chat"]
    assert all(isinstance(e, ModelCatalogEntry) for e in out)
    assert out[0].provider == "anthropic"


def test_map_catalog_empty() -> None:
    assert _map_catalog({}) == []
    assert _map_catalog({"data": None}) == []
