"""Admin: manage team conventions/business rules (TEAM memory type)."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.auth.dependencies import get_current_user
from backend.app.memory.service import MemoryService, MemoryType

log = logging.getLogger("aria.admin")
router = APIRouter()


class TeamMemoryCreate(BaseModel):
    content: str
    team_id: str = "default"


class TeamMemoryUpdate(BaseModel):
    content: str | None = None
    ttl_days: int | None = None


@router.get("")
async def list_team_memories(
    team_id: str = "default",
    current_user: Any = Depends(get_current_user),
) -> list[dict]:
    """List all team conventions for a team."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"

    try:
        svc = MemoryService.get_instance()
        memories = svc.get_all_memories(
            user_id=team_id,
            workspace_id=workspace_id,
            memory_type=MemoryType.TEAM,
        )

        return [
            {
                "id": m.get("id"),
                "content": m.get("memory") or m.get("data") or "",
                "team_id": team_id,
                "created_at": m.get("created_at"),
                "metadata": m.get("metadata"),
            }
            for m in memories
        ]

    except Exception as exc:
        log.error("team_memory.list failed: %s", exc)
        return []


@router.post("")
async def create_team_memory(
    payload: TeamMemoryCreate,
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Create a new team convention/business rule."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"

    try:
        svc = MemoryService.get_instance()
        memory_id = svc.store(
            content=payload.content,
            memory_type=MemoryType.TEAM,
            user_id="admin",
            workspace_id=workspace_id,
            team_id=payload.team_id,
            metadata={
                "created_by": getattr(current_user, "user_id", "admin"),
                # New conventions start pending — only approved ones feed the LLM.
                "status": "pending",
            },
        )

        if memory_id:
            log.info("team_memory.create: Created %s for team %s", memory_id, payload.team_id)
            return {
                "created": True,
                "id": memory_id,
                "content": payload.content,
                "team_id": payload.team_id,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create team memory")

    except HTTPException:
        raise
    except Exception as exc:
        log.error("team_memory.create failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to create: {exc}") from exc


class TeamMemoryStatusUpdate(BaseModel):
    status: str  # "approved" | "rejected" | "pending"
    team_id: str = "default"


@router.patch("/{memory_id}/status")
async def set_team_memory_status(
    memory_id: str,
    payload: TeamMemoryStatusUpdate,
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Approve / reject a team convention (admin or team_lead review workflow).

    Only `approved` conventions feed the LLM context; new ones start `pending`.
    """
    can_review = getattr(current_user, "can_admin", False) or getattr(
        current_user, "can_manage_team", False
    )
    if not can_review:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin or team_lead role required"
        )
    if payload.status not in ("approved", "rejected", "pending"):
        raise HTTPException(status_code=422, detail="status must be approved|rejected|pending")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    try:
        svc = MemoryService.get_instance()
        ok = svc.set_memory_status(
            memory_id, payload.status, workspace_id=workspace_id, team_id=payload.team_id
        )
        if ok:
            log.info("team_memory.status: %s -> %s", memory_id, payload.status)
            return {"id": memory_id, "status": payload.status}
        raise HTTPException(status_code=404, detail="Team memory not found")
    except HTTPException:
        raise
    except Exception as exc:
        log.error("team_memory.status failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to update status: {exc}") from exc


@router.delete("/{memory_id}")
async def delete_team_memory(
    memory_id: str,
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Delete a team convention."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    try:
        svc = MemoryService.get_instance()
        success = svc.delete_memory(memory_id)

        if success:
            log.info("team_memory.delete: Deleted %s", memory_id)
            return {"deleted": True, "id": memory_id}
        else:
            raise HTTPException(status_code=404, detail="Team memory not found")

    except HTTPException:
        raise
    except Exception as exc:
        log.error("team_memory.delete failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to delete: {exc}") from exc
