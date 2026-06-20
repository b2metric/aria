"""Role-Based Access Control (RBAC) guard dependencies.

This module provides FastAPI dependency factories that enforce minimum
role requirements on protected endpoints.

Usage::

    from backend.app.auth.dependencies import CurrentUser
    from backend.app.auth.rbac import require_role
    from backend.app.auth.models import Role


    @router.get("/admin/dashboard")
    async def admin_dashboard(
        user: CurrentUser,
        _: None = Depends(require_role(Role.ADMIN)),
    ): ...
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status

from backend.app.auth.dependencies import get_current_user
from backend.app.auth.models import Role, UserContext

CurrentUser = Annotated[UserContext, Depends(get_current_user)]


# ── Role guards ──────────────────────────────────────────────────────────


def require_role(minimum: Role) -> RoleGuard:
    """Require the user to have at least *minimum* role.

    Returns a FastAPI dependency that raises 403 if the user's role is
    insufficient.
    """

    async def guard(user: CurrentUser) -> None:
        if not user.role.can(minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{user.role.value}' is not permitted "
                    f"(requires at least '{minimum.value}')"
                ),
            )

    # Tag the guard so route introspection tools can see the required role.
    guard.__name__ = f"require_{minimum.value}"
    guard.__qualname__ = f"RoleGuard.require_{minimum.value}"
    return guard


async def require_sql_access(user: CurrentUser) -> None:
    """Require the user to have *effective* SQL visibility.

    Effective visibility honours the per-user override
    (``users.sql_visibility``) on top of the role default: an explicit
    True/False wins, NULL inherits the role default (admin/analyst only).
    ``get_current_user`` is JWT-only, so the override is read here from the
    metadata DB; a lookup failure falls back to the role default.
    """
    from sqlalchemy import text as _text

    from backend.app.db.session import get_sessionmaker
    from backend.app.query.sql_visibility import resolve_effective_sql_visibility

    override: bool | None = None
    if user.user_id:
        try:
            maker = get_sessionmaker()
            async with maker() as session:
                row = (
                    await session.execute(
                        _text("SELECT sql_visibility FROM users WHERE id = :uid"),
                        {"uid": user.user_id},
                    )
                ).fetchone()
            if row is not None:
                override = row[0]
        except Exception:
            override = None

    if override is not None:
        effective = override
    else:
        effective = resolve_effective_sql_visibility(user.role, sql_visibility=None) or bool(
            user.can_view_sql
        )

    if not effective:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SQL access is not available for your role",
        )


def require_team_management(user: CurrentUser) -> None:
    """Require the user to be able to manage team members."""
    if not user.can_manage_team:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team management requires admin or team_lead role",
        )


def require_workspace_admin(user: CurrentUser) -> None:
    """Require the user to be a workspace administrator."""
    if not user.can_manage_workspace:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace administration requires admin role",
        )


# ── Type alias for route signatures ──────────────────────────────────────

# This is used in the return type of require_role() to help type-checkers.
RoleGuard = type(lambda: None)  # pragma: no cover
