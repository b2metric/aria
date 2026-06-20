"""Admin: list and query data-access audit logs.

Every data-access event (queries, exports, vault reads, schema discoveries,
policy evaluations) produces an immutable audit-log entry in ``data_audit_logs``.
This endpoint allows workspace admins to search, filter, and paginate those
entries for governance and compliance purposes.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.auth.dependencies import UserContext, get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.services.audit import AuditService

log = logging.getLogger("aria.admin.audit")
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


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("")
async def list_audit_logs(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = Query(None, alias="resource_type"),
    success: bool | None = Query(None, description="Filter by details.success (true/false)"),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List audit logs with filtering and pagination.

    Filters (all optional):
    * **user_id**    – show logs for a specific user UUID
    * **action**     – filter by action name (``query``, ``export``,
                       ``policy_evaluation``, etc.)
    * **resource_type** – filter by resource type (``table``, ``query``,
                           ``artifact``, etc.)

    Results are ordered newest-first.
    """
    if not current_user.can_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    try:
        from sqlalchemy import select as sa_select

        from backend.app.models.organization import Customer

        customer_id_raw = getattr(current_user, "workspace_id", None)

        # Look up the actual customer UUID from the slug
        result = await db.execute(sa_select(Customer.id).where(Customer.slug == customer_id_raw))
        customer_uuid = result.scalar_one_or_none()

        if customer_uuid:
            customer_id = customer_uuid
        elif customer_id_raw and customer_id_raw != "stc-kuwait":
            customer_id = uuid.UUID(str(customer_id_raw))
        else:
            # Fallback for old requests
            customer_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workspace UUID: {exc}",
        ) from exc

    user_uuid: uuid.UUID | None = None
    if user_id:
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid user_id UUID format: {exc}"
            ) from exc

    try:
        svc = AuditService(db)
        logs = await svc.get_logs(
            customer_id=customer_id,
            user_id=user_uuid,
            action=action,
            resource_type=resource_type,
            success=success,
            limit=limit,
            offset=offset,
        )

        total_count = await svc.count_logs(
            customer_id=customer_id,
            user_id=user_uuid,
            action=action,
            resource_type=resource_type,
            success=success,
        )

        return {
            "data": [
                {
                    "id": str(log.id),
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "details": log.details,
                    "user_id": str(log.user_id) if log.user_id else None,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }
    except Exception as exc:
        log.error("audit.list failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to list audit logs: {exc}") from exc
