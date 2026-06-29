"""Admin: manage users within a customer workspace.

List users and update their role/team assignment, scoped to the
customer identified via the workspace slug in the current user's JWT claims.
"""

from __future__ import annotations

import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import UserContext, get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.organization import Customer, User
from backend.app.schemas.organization import (
    UserCreate,
    UserCreateResponse,
    UserResponse,
    UserUpdate,
)
from backend.app.services.keycloak_admin import KeycloakAdminService

log = logging.getLogger("aria.admin.users")
router = APIRouter()


# ── Slug → customer_id helper ───────────────────────────────────────


async def resolve_customer_id(current_user: UserContext, db: AsyncSession) -> uuid.UUID:
    """Resolve the customer UUID from the workspace slug in the JWT.

    Follows the same pattern as `audit.py`: looks up `Customer.id`
    by `Customer.slug` matching `current_user.workspace_id`.
    """
    workspace_slug = getattr(current_user, "workspace_id", None)

    if workspace_slug:
        result = await db.execute(select(Customer.id).where(Customer.slug == workspace_slug))
        customer_uuid = result.scalar_one_or_none()
        if customer_uuid:
            return customer_uuid

        # Fallback: try parsing workspace_id as a raw UUID
        try:
            return uuid.UUID(str(workspace_slug))
        except (ValueError, AttributeError):
            pass

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Cannot resolve customer from workspace context",
    )


# ── Database session dependency ─────────────────────────────────────


async def get_db() -> AsyncSession:  # type: ignore[misc]
    maker = get_sessionmaker()
    async with maker() as session:
        yield session  # pyright: ignore[reportReturnType]


# ── Endpoints ───────────────────────────────────────────────────────


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """List all users belonging to the current workspace's customer."""
    if not current_user.can_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    customer_id = await resolve_customer_id(current_user, db)

    result = await db.execute(
        select(User).where(User.customer_id == customer_id).order_by(User.display_name, User.email)
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("", response_model=UserCreateResponse)
async def create_user(
    body: UserCreate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserCreateResponse:
    """Create a new user within the current workspace.

    A cryptographically-random one-time password is generated and returned ONCE
    (the user is created ``temporary`` and must reset it on first login). No shared
    default password is ever used.
    """
    if not current_user.can_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    customer_id = await resolve_customer_id(current_user, db)

    # Check for existing email in DB first
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists"
        )

    # 1. Create in Keycloak with a random temp password (force reset on first login)
    temp_password = secrets.token_urlsafe(16)
    kc_service = KeycloakAdminService()
    workspace_slug = current_user.workspace_id or "default"
    kc_user_id, db_user_id = await kc_service.create_user(
        email=body.email,
        display_name=body.display_name,
        password=temp_password,
        role=body.role,
        workspace_id=workspace_slug,
        temporary=True,
    )

    # 2. Add to DB
    user = User(
        id=uuid.UUID(db_user_id),
        external_id=kc_user_id,
        customer_id=customer_id,
        email=body.email,
        display_name=body.display_name,
        role=body.role,
        team_id=body.team_id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    log.info("Created user %s (id=%s) in customer_id=%s", user.email, user.id, customer_id)
    return UserCreateResponse(
        **UserResponse.model_validate(user).model_dump(), temporary_password=temp_password
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a user, propagating the removal to Keycloak (item 30, follow-on b).

    Removes the local row AND deletes the backing Keycloak account by the stored
    ``external_id``. Best-effort on the IdP side: a Keycloak outage (or a 404 — the
    account is already gone) must not block the local delete, mirroring the resilient
    team-delete path. An admin cannot delete their own account (self-lockout guard).
    """
    if not current_user.can_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    # Guard against an admin deleting themselves (would lock them out of admin).
    if str(user_id) == str(getattr(current_user, "user_id", "")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete your own account"
        )

    customer_id = await resolve_customer_id(current_user, db)

    result = await db.execute(
        select(User).where(User.id == user_id, User.customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or does not belong to this workspace",
        )

    # Propagate to Keycloak by the STORED external_id; skip cleanly if unlinked.
    if user.external_id:
        kc_service = KeycloakAdminService()
        try:
            await kc_service.delete_user(user.external_id)
        except Exception as e:  # noqa: BLE001 — best-effort cleanup, never block local delete
            log.warning("Failed to delete user %s in Keycloak: %s", user.external_id, e)

    await db.delete(user)
    await db.commit()

    log.info("Deleted user %s (id=%s) from customer_id=%s", user.email, user.id, customer_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update a user's role and/or team assignment.

    Verifies the user belongs to the current workspace's customer.
    """
    if not current_user.can_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    customer_id = await resolve_customer_id(current_user, db)

    result = await db.execute(
        select(User).where(User.id == user_id, User.customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or does not belong to this workspace",
        )

    # 1. Update in Keycloak
    kc_service = KeycloakAdminService()
    kc_updates = {}
    if body.role is not None:
        kc_updates["role"] = body.role
    if hasattr(body, "team_id") and "team_id" in body.model_fields_set:
        kc_updates["team_id"] = body.team_id

    if kc_updates and user.external_id:
        try:
            await kc_service.update_user(user.external_id, kc_updates)
        except Exception as e:
            log.warning("Failed to update user in Keycloak, but will update local DB: %s", e)

    # 2. Apply partial updates to DB
    if body.role is not None:
        user.role = body.role
    if hasattr(body, "team_id") and "team_id" in body.model_fields_set:
        user.team_id = body.team_id
    # Per-user SQL-visibility override: only touch it when explicitly present in
    # the request body (so omitting the field leaves the existing value intact,
    # and an explicit null resets to "inherit role default").
    if "sql_visibility" in body.model_fields_set:
        user.sql_visibility = body.sql_visibility

    await db.commit()
    await db.refresh(user)

    log.info(
        "Updated user %s (id=%s): role=%s, team_id=%s, sql_visibility=%s",
        user.email,
        user.id,
        user.role,
        user.team_id,
        user.sql_visibility,
    )
    return UserResponse.model_validate(user)
