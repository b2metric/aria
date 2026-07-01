"""Code-level metering for the mem0 embedder (the LiteLLM-bypass blind spot).

mem0's ``embedding_model.embed`` returns only the vector — no token/cost info —
and, when the embedder is a self-hosted / HuggingFace model, bypasses the LiteLLM
proxy entirely, so those calls appear in NEITHER ``LiteLLM_SpendLogs`` NOR
``token_usage_events``. This module wraps ``embed`` so each call records a
best-effort ``token_usage_events`` row (operation=``mem0_embedding``,
tenant-attributed, ``user_id=NULL``) WITHOUT changing the vector mem0 gets back.

mem0 discards the real usage, so input tokens are estimated (chars/4) and priced
from a single configurable rate — default 0 → ``priced=False`` (self-hosted),
counted but not billed (Task 18). Metering is fire-and-forget via the background
loop (``metering_bridge``) and can never break embedding or recall.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from backend.app.services.metering_bridge import submit_metering

logger = logging.getLogger(__name__)

# Set by MemoryService around a lookup/store so the (otherwise tenant-less)
# embed() call can attribute the tokens to a workspace. embed() runs in the same
# thread / copied context as the enclosing lookup/store, so it reads what they set.
current_workspace: ContextVar[str | None] = ContextVar("mem0_embed_workspace", default=None)

MEM0_EMBEDDING_OP = "mem0_embedding"
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: Any) -> int:
    """Rough input-token estimate for an embed call (mem0 discards the real usage).

    Uses a chars/4 heuristic with ceiling, so any non-empty text counts as ≥ 1
    token. Accepts a single string or a batch (list/tuple of strings).
    """
    if text is None:
        return 0
    chars = sum(len(str(t)) for t in text) if isinstance(text, (list, tuple)) else len(str(text))
    return (chars + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN


def build_embedding_response(text: Any, *, model: str, cost_per_token: float) -> dict[str, Any]:
    """Build a synthetic ``response`` for ``record_system_llm_usage``.

    Shapes the estimated usage the way ``extract_usage`` / ``extract_cost`` expect
    (raw-dict form). Cost is ``cost_per_token × tokens``; a rate of 0 emits
    ``_response_cost='0'`` — a real *unpriced* signal (``Decimal('0')``, not
    ``None``) so ``record_llm_usage`` marks it ``priced=False`` instead of falling
    back to LiteLLM pricing. A positive rate marks it priced.
    """
    tokens = estimate_tokens(text)
    cost = cost_per_token * tokens if cost_per_token and cost_per_token > 0 else 0
    return {
        "model": model,
        "usage": {"prompt_tokens": tokens, "completion_tokens": 0},
        "_response_cost": str(cost) if cost else "0",
    }


def wrap_embedding_model(
    embedding_model: Any,
    *,
    get_workspace: Callable[[], str | None],
    model_name: str,
    cost_per_token: float,
) -> bool:
    """Install a metering wrapper around ``embedding_model.embed``.

    Returns ``True`` if it wrapped, ``False`` if there is nothing to wrap or it was
    already wrapped (singleton re-init guard). The wrapper is a pure passthrough
    for the vector; metering is best-effort and fire-and-forget and can never break
    embedding or recall.
    """
    if embedding_model is None or not hasattr(embedding_model, "embed"):
        return False
    original_embed = embedding_model.embed
    if getattr(original_embed, "_aria_metered", False):
        return False

    def metered_embed(*args: Any, **kwargs: Any) -> Any:
        vector = original_embed(*args, **kwargs)
        try:
            workspace_id = get_workspace()
            if workspace_id:
                text = args[0] if args else kwargs.get("text")
                response = build_embedding_response(
                    text, model=model_name, cost_per_token=cost_per_token
                )
                # Imported lazily to avoid a memory→services import cycle at load.
                from backend.app.services.token import record_system_llm_usage

                coro = record_system_llm_usage(
                    workspace_id=workspace_id,
                    operation=MEM0_EMBEDDING_OP,
                    response=response,
                )
                try:
                    submit_metering(coro)
                except Exception:
                    coro.close()  # don't leak an un-awaited coroutine
                    raise
        except Exception:  # noqa: BLE001 — metering must never break embedding/recall
            logger.debug("mem0 embed metering skipped", exc_info=True)
        return vector

    metered_embed._aria_metered = True  # type: ignore[attr-defined]
    embedding_model.embed = metered_embed
    return True
