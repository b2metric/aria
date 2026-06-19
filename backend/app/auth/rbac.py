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


def require_sql_access(user: CurrentUser) -> None:
    """Require the user to have SQL visibility (``can_view_sql``).

    By default only ``admin`` and ``analyst`` roles have this permission.
    """
    if not user.can_view_sql:
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
