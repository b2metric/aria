"""Admin: list and manage agent memory entries (Mem0 + Qdrant).

Supports viewing all memory types:
- USER: Personal preferences per user
- TEAM: Team conventions/business rules
- QUERY_CACHE: Cached NL→SQL mappings
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.app.auth.dependencies import get_current_user
from backend.app.memory.service import MemoryService, MemoryType

log = logging.getLogger("aria.admin")
router = APIRouter()


@router.get("")
async def get_all_memories(
    memory_type: Literal["all", "user", "team", "cache"] = Query(
        default="all",
        description="Filter by memory type: all, user, team, or cache",
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    current_user: Any = Depends(get_current_user),
) -> dict:
    """List all memory entries for the workspace.

    Agent memory persistence lives in **Qdrant via Mem0** (LOCKED-DECISIONS #1).

    Args:
        memory_type: Filter memories by type (all, user, team, cache)

    Returns:
        List of memory entries with id, entity_id, content, type, created_at
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    user_id = getattr(current_user, "user_id", None) or ""

    svc = MemoryService.get_instance()
    all_memories: list[dict] = []

    try:
        # Fetch user memories
        if memory_type in ("all", "user"):
            user_mems = svc.get_all_memories(
                user_id=user_id,
                workspace_id=workspace_id,
                memory_type=MemoryType.USER,
            )
            for m in user_mems:
                all_memories.append(
                    {
                        "id": m.get("id"),
                        "entity_id": f"{workspace_id}:{user_id}",
                        "content": m.get("memory") or m.get("data") or "",
                        "type": "user",
                        "created_at": m.get("created_at"),
                        "metadata": m.get("metadata"),
                    }
                )

        # Fetch team memories (default team)
        if memory_type in ("all", "team"):
            team_mems = svc.get_all_memories(
                user_id="default",  # Default team
                workspace_id=workspace_id,
                memory_type=MemoryType.TEAM,
            )
            for m in team_mems:
                all_memories.append(
                    {
                        "id": m.get("id"),
                        "entity_id": f"{workspace_id}:team:default",
                        "content": m.get("memory") or m.get("data") or "",
                        "type": "team",
                        "created_at": m.get("created_at"),
                        "metadata": m.get("metadata"),
                    }
                )

        # Fetch query cache
        if memory_type in ("all", "cache"):
            cache_mems = svc.get_all_memories(
                user_id="query_cache",
                workspace_id=workspace_id,
                memory_type=MemoryType.QUERY_CACHE,
            )
            for m in cache_mems:
                all_memories.append(
                    {
                        "id": m.get("id"),
                        "entity_id": f"{workspace_id}:query_cache",
                        "content": m.get("memory") or m.get("data") or "",
                        "type": "cache",
                        "created_at": m.get("created_at"),
                        "metadata": m.get("metadata"),
                    }
                )

    except Exception as exc:
        log.warning("admin.memory: Mem0/Qdrant lookup failed: %s", exc)
        return []

    # Sort by created_at descending (newest first)
    all_memories.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    total = len(all_memories)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit

    return {
        "items": all_memories[start_idx:end_idx],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
    }


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Delete a specific memory entry.

    Only admin can delete memories.
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    try:
        svc = MemoryService.get_instance()
        success = svc.delete_memory(memory_id)

        if success:
            log.info("admin.memory: Deleted memory %s", memory_id)
            return {"deleted": True, "id": memory_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found or already deleted",
            )

    except HTTPException:
        raise
    except Exception as exc:
        log.error("admin.memory: Failed to delete %s: %s", memory_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memory: {exc}",
        ) from exc


@router.post("/cleanup")
async def cleanup_expired_memories(
    cache_ttl_days: int = Query(default=7, ge=1, le=365, description="Days to keep query cache"),
    user_ttl_days: int = Query(default=90, ge=1, le=365, description="Days to keep user memories"),
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Trigger memory cleanup based on retention policy.

    Retention policy:
    - QUERY_CACHE: 7 days (default) - stale SQL mappings
    - USER: 90 days (default) - old preferences
    - TEAM: ∞ (never expires) - institutional knowledge

    Only admin can trigger cleanup.
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"

    try:
        svc = MemoryService.get_instance()
        result = svc.cleanup_expired_memories(
            workspace_id=workspace_id,
            cache_ttl_days=cache_ttl_days,
            user_ttl_days=user_ttl_days,
        )

        log.info(
            "admin.memory: Cleanup completed for workspace=%s: %s",
            workspace_id,
            result,
        )
        return {
            "status": "completed",
            "deleted": result,
            "policy": {
                "cache_ttl_days": cache_ttl_days,
                "user_ttl_days": user_ttl_days,
                "team_ttl": "never",
            },
        }

    except Exception as exc:
        log.error("admin.memory: Cleanup failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {exc}",
        ) from exc


class MemoryTTLUpdate(BaseModel):
    ttl_days: int | None = None


@router.patch("/{memory_id}")
async def update_memory_ttl(
    memory_id: str,
    update: MemoryTTLUpdate,
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Update TTL for a specific memory entry."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    try:
        svc = MemoryService.get_instance()

        if update.ttl_days == 0:
            success = svc.delete_memory(memory_id)
            if success:
                return {"deleted": True, "id": memory_id}
            raise HTTPException(status_code=404, detail="Memory not found")

        success = svc.update_memory_ttl(memory_id, update.ttl_days)

        if success:
            expires_at = None
            if update.ttl_days:
                expires_at = (datetime.now(UTC) + timedelta(days=update.ttl_days)).isoformat()

            log.info("admin.memory: Updated TTL for %s to %s days", memory_id, update.ttl_days)
            return {
                "updated": True,
                "id": memory_id,
                "ttl_days": update.ttl_days,
                "expires_at": expires_at,
            }
        else:
            raise HTTPException(status_code=404, detail="Memory not found or update failed")

    except HTTPException:
        raise
    except Exception as exc:
        log.error("admin.memory: Failed to update TTL for %s: %s", memory_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to update TTL: {exc}") from exc


@router.get("/stats")
async def get_memory_stats(
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Get memory statistics for the workspace."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"

    try:
        svc = MemoryService.get_instance()
        stats = svc.get_memory_stats(workspace_id)
        return stats
    except Exception as exc:
        log.error("admin.memory: Failed to get stats: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {exc}") from exc
