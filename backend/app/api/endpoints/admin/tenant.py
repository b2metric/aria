"""Admin: tenant configuration (token quotas, row limits).

Manages system-wide limits for the workspace/tenant.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from backend.app.auth.dependencies import get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.token import TokenQuota

DEFAULT_DAILY_TOKEN_LIMIT = 50000
DEFAULT_MAX_ROW_LIMIT = 1000

log = logging.getLogger("aria.admin")
router = APIRouter()


class TenantConfigUpdate(BaseModel):
    """Update tenant configuration."""
    
    daily_token_limit: int | None = Field(
        default=None,
        ge=1000,
        le=10_000_000,
        description="Daily token limit per user/team (1K - 10M)",
    )
    max_row_limit: int | None = Field(
        default=None,
        ge=100,
        le=1_000_000,
        description="Max rows per query (100 - 1M)",
    )


class TenantConfigResponse(BaseModel):
    """Tenant configuration response."""
    
    daily_token_limit: int
    max_row_limit: int
    source: str  # "db" or "default"


@router.get("")
async def get_tenant_config(
    current_user: Any = Depends(get_current_user),
) -> TenantConfigResponse:
    """Get tenant limits.
    
    Daily token limit comes from the active TokenQuota (real);
    the per-query row limit is a platform default until a per-tenant override exists.
    Degrades to defaults if the table is not yet migrated / DB is unavailable.
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    quota = None
    try:
        async with get_sessionmaker()() as session:
            quota = (
                await session.execute(
                    select(TokenQuota)
                    .where(TokenQuota.is_active.is_(True))
                    .order_by(TokenQuota.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
    except SQLAlchemyError as exc:
        log.warning("admin.tenant: query failed (table not migrated?): %s", exc)

    return TenantConfigResponse(
        daily_token_limit=quota.token_limit if quota else DEFAULT_DAILY_TOKEN_LIMIT,
        max_row_limit=DEFAULT_MAX_ROW_LIMIT,  # TODO: Add per-tenant row limit to DB
        source="db" if quota else "default",
    )


@router.patch("")
async def update_tenant_config(
    body: TenantConfigUpdate,
    current_user: Any = Depends(get_current_user),
) -> TenantConfigResponse:
    """Update tenant limits.
    
    Only admin can update tenant configuration.
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    if body.daily_token_limit is None and body.max_row_limit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided",
        )

    try:
        async with get_sessionmaker()() as session:
            # Get or create active quota
            quota = (
                await session.execute(
                    select(TokenQuota)
                    .where(TokenQuota.is_active.is_(True))
                    .order_by(TokenQuota.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            
            if quota:
                # Update existing quota
                if body.daily_token_limit is not None:
                    quota.token_limit = body.daily_token_limit
                await session.commit()
                log.info(
                    "admin.tenant: Updated quota %s: token_limit=%d",
                    quota.id,
                    quota.token_limit,
                )
            else:
                # Create new quota
                new_quota = TokenQuota(
                    token_limit=body.daily_token_limit or DEFAULT_DAILY_TOKEN_LIMIT,
                    is_active=True,
                )
                session.add(new_quota)
                await session.commit()
                quota = new_quota
                log.info(
                    "admin.tenant: Created new quota: token_limit=%d",
                    quota.token_limit,
                )

        return TenantConfigResponse(
            daily_token_limit=quota.token_limit,
            max_row_limit=body.max_row_limit or DEFAULT_MAX_ROW_LIMIT,
            source="db",
        )

    except SQLAlchemyError as exc:
        log.error("admin.tenant: Failed to update config: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant config: {exc}",
        ) from exc
