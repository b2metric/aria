"""LiteLLM admin client — per-customer virtual-key minting (TIER 3 item 27, BYOK Phase 2).

The shared LiteLLM proxy is configured with a master key + key store, so it can
mint scoped *virtual keys* via its key-management API. Minting one per customer
(scoped to their allowed model, optional budget) gives real per-customer isolation
— spend tracking, rate limits, model access — at the proxy, instead of passing the
customer's raw upstream key straight through.

Backward-compatible: when no master key is configured, :func:`provision_virtual_key`
falls back to the Phase-1 passthrough (store the upstream key as the proxy key), so
existing deployments are unaffected until the master key is provisioned.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT_S = 10.0


async def mint_virtual_key(
    *,
    api_base: str,
    master_key: str,
    key_alias: str,
    models: list[str],
    max_budget: float | None = None,
) -> str:
    """Mint a scoped LiteLLM virtual key via ``POST /key/generate``.

    Authenticated with the proxy *master_key*. Returns the new virtual key
    (``sk-...``). Raises on a non-2xx response or a malformed body.
    """
    payload: dict = {"key_alias": key_alias, "models": models}
    if max_budget is not None:
        payload["max_budget"] = max_budget

    async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
        resp = await client.post(
            f"{api_base.rstrip('/')}/key/generate",
            headers={"Authorization": f"Bearer {master_key}"},
            json=payload,
        )
        resp.raise_for_status()
        key = resp.json().get("key")
    if not key:
        raise ValueError("LiteLLM /key/generate returned no 'key'")
    return key


async def delete_virtual_key(*, api_base: str, master_key: str, key: str) -> None:
    """Delete a previously-minted virtual key via ``POST /key/delete``.

    Best-effort: used on rotation so superseded keys do not accumulate. Failures
    are logged, not raised — a dangling key is not worth failing a config save.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.post(
                f"{api_base.rstrip('/')}/key/delete",
                headers={"Authorization": f"Bearer {master_key}"},
                json={"keys": [key]},
            )
            resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — cleanup is best-effort
        logger.warning("Failed to delete LiteLLM virtual key (alias cleanup): %s", exc)


async def provision_virtual_key(
    *,
    api_base: str,
    master_key: str | None,
    customer_slug: str,
    upstream_key: str,
    model: str,
) -> str:
    """Resolve the proxy key to store for a customer at LLM-config save time.

    - master key configured → mint a per-customer virtual key (``aria-{slug}``,
      scoped to *model*) and return it (Phase 2 — isolation).
    - master key absent → return *upstream_key* unchanged (Phase 1 passthrough).
    - mint failure → fall back to *upstream_key* so a proxy hiccup never blocks a
      config save (logged loudly).
    """
    if not master_key:
        return upstream_key
    try:
        return await mint_virtual_key(
            api_base=api_base,
            master_key=master_key,
            key_alias=f"aria-{customer_slug}",
            models=[model] if model else [],
        )
    except Exception as exc:  # noqa: BLE001 — graceful degrade to passthrough
        logger.warning(
            "Failed to mint LiteLLM virtual key for %s; falling back to upstream passthrough: %s",
            customer_slug,
            exc,
        )
        return upstream_key
