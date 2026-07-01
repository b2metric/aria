"""Unit tests for the LLM model-catalog mapping (Sprint 2)."""

from __future__ import annotations

from backend.app.api.endpoints.admin.llm_config import (
    ModelCatalogEntry,
    _infer_provider,
    _map_catalog,
    _provider_str,
)
from backend.app.models.enums import LLMProvider


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


def test_provider_str_handles_enum_and_raw_string() -> None:
    """The `provider` column is a native PG ENUM that SQLAlchemy hands back as a
    plain ``str`` at runtime — bare ``.value`` on it raises AttributeError and made
    GET /api/admin/llm-config silently fall back to the empty default. ``_provider_str``
    must accept both an ``LLMProvider`` enum and a raw string."""
    assert _provider_str(LLMProvider.OPENAI) == "openai"
    assert _provider_str("openai") == "openai"
    assert _provider_str("anthropic") == "anthropic"
