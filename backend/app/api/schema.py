"""Schema cache API endpoints.

All endpoints are workspace-scoped — the ``workspace_id`` is extracted
from the authenticated user's JWT via the ``WorkspaceID`` dependency.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.auth.dependencies import CurrentUser, WorkspaceID
from backend.app.auth.rbac import require_role
from backend.app.auth.models import Role
from backend.app.schema_discovery.cache import (
    get_cache_ttl,
    get_schema,
    invalidate_schema,
    invalidate_workspace,
    set_schema,
)
from backend.app.schema_discovery.models import SchemaSnapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schema", tags=["schema"])


# ── Cache read ─────────────────────────────────────────────────────────────


@router.get(
    "/cache/{db_config_id}",
    response_model=SchemaSnapshot | None,
    summary="Get cached schema snapshot",
)
async def get_cached_schema(
    db_config_id: str,
    workspace_id: WorkspaceID,
    _user: CurrentUser,
) -> SchemaSnapshot | None:
    """Retrieve a cached schema snapshot for a database configuration.

    Returns ``null`` if no cache entry exists or the TTL has expired.
    """
    snapshot = await get_schema(workspace_id, db_config_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No cached schema for db_config={db_config_id} in workspace={workspace_id}",
        )
    return snapshot


@router.get(
    "/cache/{db_config_id}/ttl",
    summary="Get remaining cache TTL",
)
async def get_schema_cache_ttl(
    db_config_id: str,
    workspace_id: WorkspaceID,
    _user: CurrentUser,
) -> dict:
    """Return the remaining TTL (seconds) for a cached schema."""
    ttl = await get_cache_ttl(workspace_id, db_config_id)
    if ttl == -2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No cached schema for db_config={db_config_id}",
        )
    return {
        "db_config_id": db_config_id,
        "workspace_id": workspace_id,
        "ttl_seconds": ttl,
        "expired": ttl <= 0,
    }


# ── Cache write ────────────────────────────────────────────────────────────


@router.post(
    "/cache",
    status_code=status.HTTP_201_CREATED,
    summary="Cache a schema snapshot",
)
async def cache_schema(
    snapshot: SchemaSnapshot,
    workspace_id: WorkspaceID,
    _user: CurrentUser,
) -> dict:
    """Store a schema snapshot in Redis.

    The ``workspace_id`` from the authenticated user overrides any
    value in the request body to enforce tenant isolation.
    """
    # Enforce workspace isolation: always use the JWT-derived workspace_id
    snapshot.workspace_id = workspace_id

    await set_schema(snapshot)
    return {
        "status": "cached",
        "workspace_id": workspace_id,
        "db_config_id": snapshot.db_config_id,
        "table_count": snapshot.table_count,
    }


# ── Cache invalidation ─────────────────────────────────────────────────────


@router.delete(
    "/cache/{db_config_id}",
    summary="Invalidate cached schema",
)
async def delete_cached_schema(
    db_config_id: str,
    workspace_id: WorkspaceID,
    _user: CurrentUser,
) -> dict:
    """Delete a cached schema snapshot from Redis."""
    deleted = await invalidate_schema(workspace_id, db_config_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No cached schema for db_config={db_config_id}",
        )
    return {
        "status": "invalidated",
        "db_config_id": db_config_id,
        "workspace_id": workspace_id,
    }


@router.delete(
    "/cache",
    summary="Invalidate all cached schemas for workspace",
)
async def delete_workspace_cache(
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> dict:
    """Invalidate all cached schema snapshots for the current workspace.

    Requires admin role.
    """
    count = await invalidate_workspace(workspace_id)
    return {
        "status": "invalidated",
        "workspace_id": workspace_id,
        "keys_deleted": count,
        "initiated_by": user.user_id,
    }
