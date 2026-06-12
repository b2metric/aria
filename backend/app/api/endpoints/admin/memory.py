"""Admin: list and manage agent memory entries (Mem0 + Qdrant).

Supports viewing all memory types:
- USER: Personal preferences per user
- TEAM: Team conventions/business rules
- QUERY_CACHE: Cached NL→SQL mappings
"""
import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

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
    current_user: Any = Depends(get_current_user),
) -> list[dict]:
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
                all_memories.append({
                    "id": m.get("id"),
                    "entity_id": f"{workspace_id}:{user_id}",
                    "content": m.get("memory") or m.get("data") or "",
                    "type": "user",
                    "created_at": m.get("created_at"),
                    "metadata": m.get("metadata"),
                })
        
        # Fetch team memories (default team)
        if memory_type in ("all", "team"):
            team_mems = svc.get_all_memories(
                user_id="default",  # Default team
                workspace_id=workspace_id,
                memory_type=MemoryType.TEAM,
            )
            for m in team_mems:
                all_memories.append({
                    "id": m.get("id"),
                    "entity_id": f"{workspace_id}:team:default",
                    "content": m.get("memory") or m.get("data") or "",
                    "type": "team",
                    "created_at": m.get("created_at"),
                    "metadata": m.get("metadata"),
                })
        
        # Fetch query cache
        if memory_type in ("all", "cache"):
            cache_mems = svc.get_all_memories(
                user_id="query_cache",
                workspace_id=workspace_id,
                memory_type=MemoryType.QUERY_CACHE,
            )
            for m in cache_mems:
                all_memories.append({
                    "id": m.get("id"),
                    "entity_id": f"{workspace_id}:query_cache",
                    "content": m.get("memory") or m.get("data") or "",
                    "type": "cache",
                    "created_at": m.get("created_at"),
                    "metadata": m.get("metadata"),
                })
                
    except Exception as exc:
        log.warning("admin.memory: Mem0/Qdrant lookup failed: %s", exc)
        return []

    # Sort by created_at descending (newest first)
    all_memories.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    
    return all_memories


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
