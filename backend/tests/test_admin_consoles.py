"""Admin service-console registry — /api/admin/consoles.

Surfaces the infra web consoles (MinIO, LiteLLM, Traefik, Langfuse, Keycloak) to
the admin panel so they can be embedded (or opened in a new tab when a console
blocks framing). Admin-only. URLs come from settings (env-overridable per deploy);
the `embeddable` flag reflects whether the console can be iframed.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.api.endpoints.admin import consoles as consoles_api

pytestmark = pytest.mark.asyncio


class _Admin:
    can_admin = True


class _NonAdmin:
    can_admin = False


async def test_lists_all_consoles_for_admin():
    result = await consoles_api.list_consoles(current_user=_Admin())
    by_key = {c.key: c for c in result}

    assert set(by_key) == {"minio", "litellm", "traefik", "langfuse", "keycloak"}
    # All have a non-empty URL + display name.
    assert all(c.url and c.name for c in result)


async def test_embeddable_flags_match_measured_reality():
    by_key = {c.key: c for c in await consoles_api.list_consoles(current_user=_Admin())}
    # Frameable (X-Frame-Options stripped, no CSP frame-ancestors block).
    assert by_key["minio"].embeddable is True
    assert by_key["litellm"].embeddable is True
    assert by_key["traefik"].embeddable is True
    # Blocked by their own CSP frame-ancestors → open in a new tab.
    assert by_key["langfuse"].embeddable is False
    assert by_key["keycloak"].embeddable is False


async def test_non_admin_is_forbidden():
    with pytest.raises(HTTPException) as exc:
        await consoles_api.list_consoles(current_user=_NonAdmin())
    assert exc.value.status_code == 403
