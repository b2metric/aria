"""Admin: tenant configuration (real token quota from the token_quotas table)."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.auth.dependencies import get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.token import TokenQuota

DEFAULT_DAILY_TOKEN_LIMIT = 50000
DEFAULT_MAX_ROW_LIMIT = 1000

log = logging.getLogger("aria.admin")
router = APIRouter()


@router.get("")
async def get_tenant_config(current_user: Any = Depends(get_current_user)) -> dict:
    """Tenant limits. Daily token limit comes from the active TokenQuota (real);
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

    return {
        "daily_token_limit": quota.token_limit if quota else DEFAULT_DAILY_TOKEN_LIMIT,
        "max_row_limit": DEFAULT_MAX_ROW_LIMIT,
        "source": "db" if quota else "default",
    }
