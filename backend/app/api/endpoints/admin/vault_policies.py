"""Admin: manage team-level vault access policies (RLS).

Every workspace can define per-team (or default) rules that control
which vault tables are visible and which columns are masked.  This
endpoint lets workspace admins list and update those policies.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.auth.dependencies import CurrentUser, get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.governance import TeamVaultPolicy

log = logging.getLogger("aria.admin.vault_policies")
router = APIRouter()


# ── Database session dependency ──────────────────────────────────────


async def get_db() -> AsyncSession:  # type: ignore[misc, reportReturnType]
    """Yield a per-request async database session.

    Uses the cached sessionmaker from ``backend.app.db.session`` so every
    request reuses the global engine / pool.  The session is automatically
    closed when the request scope ends.
    """
    maker: async_sessionmaker[AsyncSession] = get_sessionmaker()
    async with maker() as session:
        yield session  # pyright: ignore[reportReturnType]


# ── Request / Response schemas ───────────────────────────────────────


class VaultPolicyUpdate(BaseModel):
    """Payload for creating or updating a team vault policy."""

    allowed_tables: list[str] = Field(
        default_factory=list,
        description="Whitelist of table names the team may query",
    )
    deny_columns: dict[str, list[str]] | None = Field(
        default=None,
        description=(
            "Per-table column deny-lists, e.g. "
            '{"sales": ["revenue", "margin"]}'
        ),
    )
    name: str | None = Field(
        default=None,
        description="Human-readable policy name (defaults to team_id if omitted)",
    )


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("")
async def get_team_policies(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get all vault policies for the current workspace.

    Returns every policy scoped to the workspace (both team-specific
    and the default / org-wide policy where ``team_id`` is NULL).
    """
    if not current_user.can_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    customer_id_raw = current_user.workspace_id or "stc-kuwait"

    try:
        customer_id = uuid.UUID(customer_id_raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workspace UUID '{customer_id_raw}': {exc}",
        ) from exc

    try:
        result = await db.execute(
            select(TeamVaultPolicy).where(
                TeamVaultPolicy.customer_id == customer_id
            )
        )
        policies = result.scalars().all()

        return [
            {
                "id": str(p.id),
                "team_id": str(p.team_id) if p.team_id else "default",
                "name": p.name,
                "allowed_tables": p.allowed_tables,
                "deny_columns": p.deny_columns,
                "is_active": p.is_active,
            }
            for p in policies
        ]
    except Exception as exc:
        log.error("vault_policies.get failed: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Failed to get policies: {exc}"
        ) from exc


@router.put("/{team_id}")
async def update_team_policy(
    team_id: str,
    payload: VaultPolicyUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create or update the vault access policy for a team.

    *team_id* can be ``"default"`` to target the workspace-wide default
    policy (stored with ``team_id == NULL``).
    """
    if not current_user.can_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    customer_id_raw = current_user.workspace_id or "stc-kuwait"

    try:
        customer_id = uuid.UUID(customer_id_raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workspace UUID '{customer_id_raw}': {exc}",
        ) from exc

    # Resolve team_uuid: NULL for the "default" sentinel.
    team_uuid: uuid.UUID | None = None
    if team_id != "default":
        try:
            team_uuid = uuid.UUID(team_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid team_id UUID format: {exc}",
            ) from exc

    try:
        # Look up an existing policy for this customer + team.
        query = select(TeamVaultPolicy).where(
            TeamVaultPolicy.customer_id == customer_id,
            TeamVaultPolicy.team_id == team_uuid,
        )
        result = await db.execute(query)
        policy = result.scalars().first()

        if policy:
            # Update existing policy
            policy.allowed_tables = payload.allowed_tables
            if payload.deny_columns is not None:
                policy.deny_columns = payload.deny_columns
            if payload.name is not None:
                policy.name = payload.name
        else:
            # Create new policy
            policy_name = payload.name or f"vault-policy-{team_id}"
            policy = TeamVaultPolicy(
                customer_id=customer_id,
                team_id=team_uuid,
                name=policy_name,
                allowed_tables=payload.allowed_tables,
                deny_columns=payload.deny_columns or {},
            )
            db.add(policy)

        await db.commit()

        return {
            "success": True,
            "team_id": team_id,
            "name": policy.name,
            "allowed_tables": policy.allowed_tables,
            "deny_columns": policy.deny_columns,
        }

    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        log.error("vault_policies.update failed: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"Failed to update policy: {exc}"
        ) from exc
