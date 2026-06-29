"""TIER 3 item 27 — BYOK Phase 2: per-customer LiteLLM virtual-key minting.

The shared LiteLLM proxy is configured for virtual keys (master_key + DB). These
tests pin the ARIA-side admin client + the save-time provisioning policy:
mint a budget/model-scoped virtual key when a master key is configured, and fall
back to passing the upstream key through (Phase-1 behavior) when it is not — so
the change is backward-compatible.
"""

from __future__ import annotations

import pytest

from backend.app.services import litellm_admin

pytestmark = pytest.mark.asyncio


class _FakeResponse:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeClient:
    """Minimal httpx.AsyncClient stand-in capturing the last POST."""

    last = {}

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **kwargs):
        _FakeClient.last = {"url": url, **kwargs}
        if url.endswith("/key/generate"):
            return _FakeResponse({"key": "sk-virtual-minted"})
        return _FakeResponse({})


async def test_mint_virtual_key_posts_to_generate_with_master_bearer(monkeypatch):
    monkeypatch.setattr(litellm_admin.httpx, "AsyncClient", _FakeClient)
    key = await litellm_admin.mint_virtual_key(
        api_base="http://litellm:4000",
        master_key="sk-master",
        key_alias="aria-acme",
        models=["gpt-4o"],
        max_budget=25.0,
    )
    assert key == "sk-virtual-minted"
    sent = _FakeClient.last
    assert sent["url"] == "http://litellm:4000/key/generate"
    assert sent["headers"]["Authorization"] == "Bearer sk-master"
    assert sent["json"]["key_alias"] == "aria-acme"
    assert sent["json"]["models"] == ["gpt-4o"]
    assert sent["json"]["max_budget"] == 25.0


async def test_provision_passes_through_when_no_master_key(monkeypatch):
    called = False

    async def _should_not_call(*a, **k):
        nonlocal called
        called = True
        return "sk-virtual"

    monkeypatch.setattr(litellm_admin, "mint_virtual_key", _should_not_call)
    out = await litellm_admin.provision_virtual_key(
        api_base="http://litellm:4000",
        master_key=None,  # not configured → Phase-1 passthrough
        customer_slug="acme",
        upstream_key="sk-customer-upstream",
        model="gpt-4o",
    )
    assert out == "sk-customer-upstream"
    assert called is False


async def test_provision_mints_when_master_key_set(monkeypatch):
    seen = {}

    async def _fake_mint(*, api_base, master_key, key_alias, models, max_budget=None):
        seen.update(key_alias=key_alias, models=models)
        return "sk-virtual-minted"

    monkeypatch.setattr(litellm_admin, "mint_virtual_key", _fake_mint)
    out = await litellm_admin.provision_virtual_key(
        api_base="http://litellm:4000",
        master_key="sk-master",
        customer_slug="acme",
        upstream_key="sk-customer-upstream",
        model="gpt-4o",
    )
    assert out == "sk-virtual-minted"
    assert seen["key_alias"] == "aria-acme"
    assert seen["models"] == ["gpt-4o"]


async def test_provision_falls_back_to_passthrough_on_mint_error(monkeypatch):
    async def _boom(*a, **k):
        raise RuntimeError("litellm down")

    monkeypatch.setattr(litellm_admin, "mint_virtual_key", _boom)
    out = await litellm_admin.provision_virtual_key(
        api_base="http://litellm:4000",
        master_key="sk-master",
        customer_slug="acme",
        upstream_key="sk-customer-upstream",
        model="gpt-4o",
    )
    # Graceful: a proxy hiccup must not break config save — keep the upstream key.
    assert out == "sk-customer-upstream"
