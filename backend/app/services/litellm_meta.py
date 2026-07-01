"""Attribution metadata for LiteLLM proxy calls (Sprint 2.5 Task 14).

The proxy already meters cost per request; passing ``user`` + ``metadata.tags`` on every call
gives it the missing dimensions so spend can be sliced by application, tenant, and operation
(via ``/spend/tags``, ``LiteLLM_DailyTagSpend``, ``/customer/*``) — shared across ARIA and, later,
cockpit (which just tags ``app:cockpit``).

Tags MUST travel as the ``x-litellm-tags`` request header (comma-separated) — the proxy ignores
a body ``metadata.tags`` on raw OpenAI-compatible calls (verified live). ``user`` goes in the body
and populates ``end_user``.

Usage — spread into an SDK call (``user`` + ``extra_headers`` are both accepted):

    await litellm.acompletion(..., **litellm_meta("insight", tenant=workspace_id))

For a raw httpx call, take the pieces apart:

    m = litellm_meta("sql_generation", tenant=workspace_id)
    headers={..., **m["extra_headers"]}; json={..., "user": m["user"]}
"""

from __future__ import annotations

from typing import Any

APP = "aria"


def litellm_tags(operation: str, tenant: str | None = None, app: str = APP) -> str:
    """Comma-separated tag string for the ``x-litellm-tags`` header."""
    tags = [f"app:{app}", f"operation:{operation}"]
    if tenant:
        tags.append(f"tenant:{tenant}")
    return ",".join(tags)


def litellm_meta(
    operation: str, tenant: str | None = None, user: str | None = None, app: str = APP
) -> dict[str, Any]:
    """Build ``{"user": ..., "extra_headers": {"x-litellm-tags": "..."}}`` for a proxied call.

    - ``operation`` — pipeline step (sql_generation / insight / chart / vault_* / mem0_embedding).
    - ``tenant`` — workspace slug; added as a ``tenant:`` tag when known.
    - ``user`` — end-user id; defaults to the tenant (tenant-level attribution), then the app.
    """
    return {
        "user": user or tenant or app,
        "extra_headers": {"x-litellm-tags": litellm_tags(operation, tenant, app)},
    }
