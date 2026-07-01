"""Regression: the LLM-config default must be a model that actually exists on the
LiteLLM proxy. It used to hardcode "gpt-4" (absent on the proxy), so any workspace
without an explicit config — or one saved from the UI's default — routed
insight/chart/suggestion to gpt-4 → 400 → silent fallbacks.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.app.api.endpoints.admin import llm_config as mod
from backend.app.core.config import get_settings


@pytest.mark.asyncio
async def test_default_llm_config_uses_valid_platform_model(monkeypatch):
    # Force the DB lookup to fail → endpoint returns its default representation.
    def _raise():
        raise RuntimeError("no db")

    monkeypatch.setattr(mod, "get_sessionmaker", _raise)

    user = MagicMock()
    user.can_admin = True
    user.workspace_id = "acme"

    resp = await mod.get_llm_config(current_user=user)

    # Must default to the valid platform model, never the dead "gpt-4" alias.
    assert resp.model_name != "gpt-4"
    assert resp.model_name == get_settings().llm_model
