"""FastAPI dependency injection for authentication and authorization.

Every protected endpoint calls :func:`get_current_user` (or one of its
variants) which validates the Bearer token, extracts claims, and
returns a :class:`UserContext` scoped to the current request.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from backend.app.auth.jwt import (
    AuthError,
    InvalidTokenError,
    TokenExpiredError,
    decode_token,
)
from backend.app.auth.models import Role, TokenPayload, UserContext

# In-memory cache to avoid syncing the same user on every request
_synced_users = set()


logger = logging.getLogger(__name__)

# ── Header extraction ────────────────────────────────────────────────────


def _extract_bearer_token(authorization: str | None = Header(None)) -> str:
    """Pull the raw JWT from the ``Authorization`` header."""
    from backend.app.core.config import get_settings

    get_settings()

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


# ── Primary dependency ───────────────────────────────────────────────────


async def get_current_user(
    token: Annotated[str, Depends(_extract_bearer_token)],
) -> UserContext:
    """Validate the JWT and return the authenticated user.

    This is the **single entry-point** for authentication.  Every
    protected route depends on it (directly or through a role guard).

    Raises
    ------
    HTTPException
        401 if token is missing, invalid, or expired.
        403 if required claims (``workspace_id``, ``role``) are absent.
    """
    try:
        payload: TokenPayload = await decode_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # ── Resolve role ────────────────────────────────────────────────
    # Token payload may use standard Keycloak claims or our custom attributes
    role_str = getattr(payload, "role", None)
    if not role_str and hasattr(payload, "model_extra") and payload.model_extra:
        role_str = payload.model_extra.get("aria_role")

    if not role_str:
        # Deny by default — never assume admin when the token carries no role claim.
        logger.warning("Token missing 'role' claim — rejecting")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing 'role' claim")

    try:
        role = Role.from_string(role_str)
    except ValueError as exc:
        # Reject an unknown role rather than silently downgrading.
        logger.warning("Invalid role '%s' received — rejecting: %s", role_str, exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid role: {role_str}"
        ) from exc

    # ── Extract custom claims ───────────────────────────────────────
    # We only rely on Keycloak injecting these if the 'aria-claims' scope
    # was requested. If missing, we apply safe defaults.

    workspace_id = getattr(payload, "workspace_id", None)
    if not workspace_id or workspace_id == "default":
        # Deny by default — a token with no real workspace must not be silently scoped.
        logger.warning("Token missing 'workspace_id' claim — rejecting")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Missing 'workspace_id' claim"
        )

    user_id = getattr(payload, "user_id", None) or payload.sub
    team_id = getattr(payload, "team_id", None) or ""

    # ── Derive permissions from role ────────────────────────────────
    can_view_sql = _can_view_sql(role) if role else False
    can_manage_team = role in (Role.ADMIN, Role.TEAM_LEAD) if role else False
    can_manage_workspace = role == Role.ADMIN if role else False
    can_admin = role == Role.ADMIN if role else False

    user = UserContext(
        sub=getattr(payload, "sub", None) or "unknown-sub",
        user_id=user_id or "unknown-user",
        workspace_id=workspace_id,
        team_id=team_id or "platform",
        role=role or Role.VIEWER,
        email=getattr(payload, "email", None),
        name=getattr(payload, "name", None),
        preferred_username=getattr(payload, "preferred_username", None),
        can_view_sql=can_view_sql,
        can_manage_team=can_manage_team,
        can_manage_workspace=can_manage_workspace,
        can_admin=can_admin,
    )

    logger.debug(
        "Authenticated user sub=%s role=%s workspace=%s",
        user.sub,
        user.role.value if user.role else "none",
        user.workspace_id,
    )
    return user


# ── Derived dependencies ─────────────────────────────────────────────────


# Reusable type aliases for route signatures.
CurrentUser = Annotated[UserContext, Depends(get_current_user)]


async def get_workspace_id(user: CurrentUser) -> str:
    """Return the current user's ``workspace_id``.

    Convenience dependency for endpoints that only need workspace
    scoping and don't need the full user object.
    """
    return user.workspace_id or "stc-kuwait"


WorkspaceID = Annotated[str, Depends(get_workspace_id)]


# ── Permissions helpers ──────────────────────────────────────────────────


def _can_view_sql(role: Role) -> bool:
    """Determine whether the given role can view raw SQL.

    By default, only ``admin`` and ``analyst`` roles can see generated
    SQL.  This mapping is configurable — adjust here if business rules
    change.
    """
    return role in (Role.ADMIN, Role.ANALYST)
