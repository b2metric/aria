"""Admin: registry of infra service consoles surfaced in the admin panel.

Returns the web-console links (MinIO, LiteLLM, Traefik, Langfuse, Keycloak) so the
frontend can embed the frameable ones in an iframe and open the rest in a new tab.
Admin-only. URLs come from settings (env-overridable per deploy).

The ``embeddable`` flag reflects measured reality: MinIO/LiteLLM/Traefik allow
framing once Traefik strips X-Frame-Options (see infra/traefik-dynamic.yml), while
Langfuse and Keycloak set their own ``CSP frame-ancestors`` that a header strip
cannot override — those open in a new tab until their app-level config is changed.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.auth.dependencies import get_current_user
from backend.app.core.config import get_settings

router = APIRouter()


class ConsoleLink(BaseModel):
    """A single infra console surfaced in the admin panel."""

    key: str
    name: str
    url: str
    embeddable: bool


@router.get("", response_model=list[ConsoleLink])
async def list_consoles(current_user: Any = Depends(get_current_user)) -> list[ConsoleLink]:
    """List infra service consoles for the admin panel (admin-only)."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    s = get_settings()
    return [
        ConsoleLink(key="minio", name="MinIO Console", url=s.console_minio_url, embeddable=True),
        ConsoleLink(key="litellm", name="LiteLLM UI", url=s.console_litellm_url, embeddable=True),
        ConsoleLink(
            key="traefik", name="Traefik Dashboard", url=s.console_traefik_url, embeddable=True
        ),
        ConsoleLink(
            key="langfuse", name="Langfuse", url=s.console_langfuse_url, embeddable=False
        ),
        ConsoleLink(
            key="keycloak", name="Keycloak Admin", url=s.console_keycloak_url, embeddable=False
        ),
    ]
