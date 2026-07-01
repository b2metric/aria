"""LLM usage extraction + USD cost estimation (Sprint 1 — token metering).

Two responsibilities, both provider-agnostic:

- ``extract_usage(resp)`` — normalize prompt/completion tokens + model out of the two
  response shapes the codebase produces: the raw httpx LiteLLM-proxy JSON
  (``{"usage": {...}, "model": ...}``, used by ``query/llm_sql.py``) and the
  ``litellm.acompletion()`` response object (``resp.usage``, ``resp.model``).
- ``compute_cost(model, prompt_tokens, completion_tokens)`` — USD via a LOCAL price
  map first (authoritative for our custom model aliases like ``gemini-reasoner`` /
  ``deepseek-*`` that LiteLLM's built-in map may not know), falling back to
  ``litellm.completion_cost()`` for anything else, and ``0`` (logged once) when even
  that fails — so metering never crashes a turn.

Prices are USD per 1,000,000 tokens ``(prompt, completion)``. They mirror the proxy
catalog in ``infra/llm/config.yaml`` and are approximate public list prices — EDIT
them to match the real contracted rates; unknown models simply cost 0 until added.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

_MILLION = Decimal(1_000_000)

# model-alias → (prompt_usd_per_1M, completion_usd_per_1M). Matched case-insensitively
# by exact key then longest prefix, after stripping `custom:litellm:` and `<provider>/`.
PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "deepseek-chat": (Decimal("0.27"), Decimal("1.10")),
    "deepseek-reasoner": (Decimal("0.55"), Decimal("2.19")),
    "deepseek-v4-flash": (Decimal("0.14"), Decimal("0.28")),
    "deepseek-v4-pro": (Decimal("0.55"), Decimal("2.19")),
    "deepseek-pro": (Decimal("0.55"), Decimal("2.19")),
    "claude-haiku": (Decimal("0.80"), Decimal("4.00")),
    "claude-sonnet": (Decimal("3.00"), Decimal("15.00")),
    "claude-opus": (Decimal("15.00"), Decimal("75.00")),
    "gemini-chat": (Decimal("0.10"), Decimal("0.40")),
    "gemini-reasoner": (Decimal("1.25"), Decimal("10.00")),
    "glm-chat": (Decimal("0.60"), Decimal("2.20")),
    "glm-reasoner": (Decimal("0.60"), Decimal("2.20")),
    "glm-4": (Decimal("0.60"), Decimal("2.20")),
    "text-embedding-3-small": (Decimal("0.02"), Decimal("0.00")),
    "text-embedding-3-large": (Decimal("0.13"), Decimal("0.00")),
}

_PROVIDER_PREFIXES = ("openai/", "anthropic/", "deepseek/", "gemini/", "azure/", "vertex_ai/")
_seen_unpriced: set[str] = set()


def _normalize(model: str) -> str:
    m = (model or "").strip().lower()
    if m.startswith("custom:litellm:"):
        m = m[len("custom:litellm:") :]
    for prefix in _PROVIDER_PREFIXES:
        if m.startswith(prefix):
            m = m[len(prefix) :]
            break
    return m


def _match_price(model: str) -> tuple[Decimal, Decimal] | None:
    m = _normalize(model)
    if m in PRICING:
        return PRICING[m]
    best_key: str | None = None
    for key in PRICING:
        if m.startswith(key) and (best_key is None or len(key) > len(best_key)):
            best_key = key
    return PRICING[best_key] if best_key else None


def _litellm_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    """LiteLLM's built-in pricing (for models not in the local map). Isolated so tests
    can stub it. Returns None on any failure/unknown model."""
    try:
        import litellm

        usd = litellm.completion_cost(
            model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )
        return float(usd) if usd else None
    except Exception:  # noqa: BLE001 — pricing is best-effort; never break a turn
        return None


def compute_cost(model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    """USD cost for a call. Local price map first, LiteLLM fallback, else 0 (logged once)."""
    price = _match_price(model)
    if price is not None:
        prompt_price, completion_price = price
        return (
            Decimal(int(prompt_tokens or 0)) * prompt_price
            + Decimal(int(completion_tokens or 0)) * completion_price
        ) / _MILLION

    fallback = _litellm_cost(model, int(prompt_tokens or 0), int(completion_tokens or 0))
    if fallback is not None:
        return Decimal(str(fallback))

    key = _normalize(model)
    if key not in _seen_unpriced:
        _seen_unpriced.add(key)
        logger.warning("No pricing for model %r — cost recorded as 0. Add it to llm_cost.PRICING.", model)
    return Decimal("0")


def extract_cost(resp: Any) -> Decimal | None:
    """Return LiteLLM's authoritative ``response_cost`` (USD) for a call, or ``None`` when the
    proxy did not report one. Sources, in order:

    - SDK object (``litellm.acompletion``): ``resp._hidden_params["response_cost"]``.
    - raw httpx dict: ``resp["_response_cost"]`` — the ``x-litellm-response-cost`` header stashed
      by the call site (``query/llm_sql.py``) — or ``resp["_hidden_params"]["response_cost"]``.

    A reported ``0`` is returned as ``Decimal("0")`` (a real *unpriced* signal, e.g. a self-hosted
    model), distinct from ``None`` ("no cost field") so the caller can tell them apart.
    """
    raw: Any = None
    if isinstance(resp, dict):
        if "_response_cost" in resp and resp["_response_cost"] is not None:
            raw = resp["_response_cost"]
        else:
            raw = (resp.get("_hidden_params") or {}).get("response_cost")
    else:
        raw = (getattr(resp, "_hidden_params", None) or {}).get("response_cost")

    if raw is None or raw == "":
        return None
    try:
        return Decimal(str(raw))
    except (ArithmeticError, ValueError, TypeError):
        return None


def extract_usage(resp: Any) -> dict[str, Any]:
    """Return ``{prompt_tokens, completion_tokens, model}`` from a proxy JSON dict or a
    litellm/openai response object. Missing fields default to 0 / "unknown"."""
    if isinstance(resp, dict):
        usage = resp.get("usage") or {}
        return {
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "model": resp.get("model") or usage.get("model") or "unknown",
        }

    usage = getattr(resp, "usage", None)
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "model": getattr(resp, "model", None) or "unknown",
    }
