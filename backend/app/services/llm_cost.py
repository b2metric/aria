"""LLM usage + USD cost extraction (Sprint 1 metering; Sprint 2.5 convergence).

The LiteLLM proxy is the single source of truth for cost: it prices every call from
``infra/llm/config.yaml`` and reports the USD via ``response_cost`` (SDK ``_hidden_params``)
or the ``x-litellm-response-cost`` HTTP header. ARIA reads that (``extract_cost``) instead of
re-deriving it, so there is no local price map to drift.

- ``extract_usage(resp)`` — normalize prompt/completion tokens + model out of the two response
  shapes the codebase produces: the raw httpx proxy JSON (``{"usage": {...}, "model": ...}``,
  ``query/llm_sql.py``) and the ``litellm.acompletion()`` object (``resp.usage``, ``resp.model``).
- ``extract_cost(resp)`` — LiteLLM's authoritative ``response_cost`` (or ``None``).
- ``compute_cost(model, ...)`` — thin FALLBACK only, used when the proxy reported no cost:
  ``litellm.completion_cost()``, else ``0`` (logged once). Never crashes a turn.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

_seen_unpriced: set[str] = set()


def _litellm_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    """LiteLLM's built-in pricing. Isolated so tests can stub it. None on any failure."""
    try:
        import litellm

        usd = litellm.completion_cost(
            model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )
        return float(usd) if usd else None
    except Exception:  # noqa: BLE001 — pricing is best-effort; never break a turn
        return None


def compute_cost(model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    """Fallback USD cost when the proxy did not report ``response_cost`` — LiteLLM's own
    pricing, else 0 (logged once). The proxy value (``extract_cost``) is preferred upstream."""
    fallback = _litellm_cost(model, int(prompt_tokens or 0), int(completion_tokens or 0))
    if fallback is not None:
        return Decimal(str(fallback))

    key = (model or "").strip().lower()
    if key not in _seen_unpriced:
        _seen_unpriced.add(key)
        logger.warning(
            "No cost for model %r (no response_cost + no LiteLLM price) — recorded as 0. "
            "Add input/output_cost_per_token to infra/llm/config.yaml.",
            model,
        )
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
