"""Admin: manage teams within a customer workspace.

CRUD operations for teams, scoped to the customer identified via
the workspace slug in the current user's JWT claims.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import UserContext, get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.organization import Customer, Team
from backend.app.schemas.organization import TeamCreate, TeamResponse
from backend.app.services.keycloak_admin import KeycloakAdminService

log = logging.getLogger("aria.admin.teams")
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


@router.get("", response_model=list[TeamResponse])
async def list_teams(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TeamResponse]:
    """List all teams belonging to the current workspace's customer."""
    if not current_user.can_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    customer_id = await resolve_customer_id(current_user, db)

    result = await db.execute(
        select(Team).where(Team.customer_id == customer_id).order_by(Team.name)
    )
    teams = result.scalars().all()
    return [TeamResponse.model_validate(t) for t in teams]


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    body: TeamCreate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    """Create a new team for the current workspace's customer."""
    if not current_user.can_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    customer_id = await resolve_customer_id(current_user, db)

    team = Team(name=body.name, customer_id=customer_id)

    # Create the backing Keycloak group so team-scoped JWT `groups` claims (SSO/RLS)
    # resolve, and store its id (item 30). Resilient: if Keycloak is unreachable the
    # team is still created with kc_group_id=None and can be re-synced later — KC
    # availability must not block tenant team management.
    kc_service = KeycloakAdminService()
    try:
        team.kc_group_id = await kc_service.create_team_group(body.name)
    except Exception as e:  # noqa: BLE001 — degrade gracefully, never block create
        log.warning(
            "Could not create Keycloak group for team %s; creating without it: %s",
            body.name,
            e,
        )

    db.add(team)
    await db.commit()
    await db.refresh(team)

    log.info(
        "Created team %s (id=%s, kc_group_id=%s) for customer %s",
        team.name,
        team.id,
        team.kc_group_id,
        customer_id,
    )
    return TeamResponse.model_validate(team)


@router.post("/sync-groups")
async def sync_team_groups(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Backfill Keycloak groups for this customer's teams that have none (item 30).

    Teams created before the kc_group_id wiring — or while Keycloak was down — have
    ``kc_group_id IS NULL``, so their team-scoped JWT ``groups`` claims never resolve.
    This creates the missing group per team and stores its id. Per-team resilient: a
    single Keycloak failure is recorded and skipped, never aborting the rest, so the
    operation is safely repeatable (only NULL teams are ever touched).
    """
    if not current_user.can_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    customer_id = await resolve_customer_id(current_user, db)

    result = await db.execute(
        select(Team).where(Team.customer_id == customer_id, Team.kc_group_id.is_(None))
    )
    pending = result.scalars().all()

    synced = 0
    failed = 0
    kc_service = KeycloakAdminService()
    for team in pending:
        try:
            team.kc_group_id = await kc_service.create_team_group(team.name)
            synced += 1
        except Exception as e:  # noqa: BLE001 — record + skip, never abort the batch
            failed += 1
            log.warning("Could not backfill Keycloak group for team %s: %s", team.name, e)

    await db.commit()
    log.info(
        "Synced Keycloak groups for customer %s: %d created, %d failed",
        customer_id,
        synced,
        failed,
    )
    return {"synced": synced, "failed": failed}


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a team (must belong to the current workspace's customer)."""
    if not current_user.can_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    customer_id = await resolve_customer_id(current_user, db)

    result = await db.execute(
        select(Team).where(Team.id == team_id, Team.customer_id == customer_id)
    )
    team = result.scalar_one_or_none()

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found or does not belong to this workspace",
        )

    # Delete the backing Keycloak group by its STORED id (item 30). The old code
    # passed str(team.id) — the local team UUID, never a KC group id — so it never
    # actually deleted the group. Skip cleanly when no KC group was linked.
    if team.kc_group_id:
        kc_service = KeycloakAdminService()
        try:
            await kc_service.delete_team_group(team.kc_group_id)
        except Exception as e:  # noqa: BLE001 — best-effort cleanup
            log.warning("Failed to delete team group %s in Keycloak: %s", team.kc_group_id, e)

    await db.delete(team)
    await db.commit()

    log.info("Deleted team %s (id=%s)", team.name, team.id)
