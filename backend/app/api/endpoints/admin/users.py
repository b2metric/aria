"""Admin: manage users within a customer workspace.

List users and update their role/team assignment, scoped to the
customer identified via the workspace slug in the current user's JWT claims.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import UserContext, get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.organization import Customer, User
from backend.app.schemas.organization import UserResponse, UserUpdate, UserCreate
from backend.app.services.keycloak_admin import KeycloakAdminService

log = logging.getLogger("aria.admin.users")
router = APIRouter()


# ── Slug → customer_id helper ───────────────────────────────────────


async def resolve_customer_id(
    current_user: UserContext, db: AsyncSession
) -> uuid.UUID:
    """Resolve the customer UUID from the workspace slug in the JWT.

    Follows the same pattern as `audit.py`: looks up `Customer.id`
    by `Customer.slug` matching `current_user.workspace_id`.
    """
    workspace_slug = getattr(current_user, "workspace_id", None)

    if workspace_slug:
        result = await db.execute(
            select(Customer.id).where(Customer.slug == workspace_slug)
        )
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )

    customer_id = await resolve_customer_id(current_user, db)

    result = await db.execute(
        select(User)
        .where(User.customer_id == customer_id)
        .order_by(User.display_name, User.email)
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("", response_model=UserResponse)
async def create_user(
    body: UserCreate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user within the current workspace."""
    if not current_user.can_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )

    customer_id = await resolve_customer_id(current_user, db)

    # Check for existing email in DB first
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists"
        )

    # 1. Create in Keycloak
    kc_service = KeycloakAdminService()
    workspace_slug = current_user.workspace_id or "default"
    kc_user_id, db_user_id = await kc_service.create_user(
        email=body.email,
        display_name=body.display_name,
        role=body.role,
        workspace_id=workspace_slug
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
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    log.info("Created user %s (id=%s) in customer_id=%s", user.email, user.id, customer_id)
    return UserResponse.model_validate(user)

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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
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

    await db.commit()
    await db.refresh(user)

    log.info(
        "Updated user %s (id=%s): role=%s, team_id=%s",
        user.email, user.id, user.role, user.team_id,
    )
    return UserResponse.model_validate(user)
