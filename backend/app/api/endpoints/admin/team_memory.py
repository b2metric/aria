"""Admin: Team memory (business conventions, glossary) management.

Team memories are workspace-wide definitions that apply to all team members:
- Business term definitions ("active subscriber" = last 30 days transaction)
- Metric formulas ("churn rate" = lost / total)
- Data conventions ("revenue" always means TOPUP_AMOUNT)
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.auth.dependencies import get_current_user
from backend.app.memory.service import MemoryService, MemoryType

log = logging.getLogger("aria.admin")
router = APIRouter()


class TeamMemoryCreate(BaseModel):
    """Create a new team memory entry."""
    
    content: str = Field(..., min_length=5, max_length=1000, description="Business rule or definition")
    team_id: str = Field(default="default", description="Team identifier")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata (term, formula, etc.)")


class TeamMemoryResponse(BaseModel):
    """Team memory entry response."""
    
    id: str | None
    content: str
    team_id: str
    metadata: dict[str, Any] | None
    created_at: str | None


@router.get("")
async def list_team_memories(
    team_id: str = "default",
    current_user: Any = Depends(get_current_user),
) -> list[dict]:
    """List all team memories for a workspace.
    
    Admin/team_lead can view team conventions.
    """
    if not getattr(current_user, "can_admin", False) and not getattr(current_user, "can_manage_team", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or team_lead role required",
        )

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    
    try:
        svc = MemoryService.get_instance()
        # Get all team memories (team_id is used as user_id in the composite key)
        mems = svc.get_all_memories(
            user_id=team_id,
            workspace_id=workspace_id,
            memory_type=MemoryType.TEAM,
        )
    except Exception as exc:
        log.warning("admin.team_memory: Mem0/Qdrant lookup failed: %s", exc)
        return []

    return [
        {
            "id": m.get("id"),
            "content": m.get("memory") or m.get("data") or "",
            "team_id": team_id,
            "metadata": m.get("metadata"),
            "created_at": m.get("created_at"),
        }
        for m in mems
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_team_memory(
    body: TeamMemoryCreate,
    current_user: Any = Depends(get_current_user),
) -> TeamMemoryResponse:
    """Create a new team memory entry (business rule/convention).
    
    Only admin/team_lead can create team memories.
    
    Examples:
    - "Active subscriber means customer with transaction in last 30 days"
    - "Revenue should always use TOPUP_AMOUNT column from fct_prep_recharge"
    - "Churn rate formula: lost subscribers / total subscribers * 100"
    """
    if not getattr(current_user, "can_admin", False) and not getattr(current_user, "can_manage_team", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or team_lead role required",
        )

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    
    try:
        svc = MemoryService.get_instance()
        memory_id = svc.store(
            content=body.content,
            memory_type=MemoryType.TEAM,
            user_id=body.team_id,  # For TEAM type, this becomes the team identifier
            workspace_id=workspace_id,
            team_id=body.team_id,
            metadata=body.metadata,
        )
        
        log.info(
            "admin.team_memory: Created team memory for %s/%s: %s",
            workspace_id,
            body.team_id,
            body.content[:50],
        )
        
        return TeamMemoryResponse(
            id=memory_id,
            content=body.content,
            team_id=body.team_id,
            metadata=body.metadata,
            created_at=None,  # Mem0 doesn't return this on create
        )
        
    except Exception as exc:
        log.error("admin.team_memory: Failed to create: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create team memory: {exc}",
        ) from exc


@router.delete("/{memory_id}")
async def delete_team_memory(
    memory_id: str,
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Delete a team memory entry.
    
    Only admin can delete team memories.
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    try:
        svc = MemoryService.get_instance()
        success = svc.delete_memory(memory_id)
        
        if success:
            log.info("admin.team_memory: Deleted memory %s", memory_id)
            return {"deleted": True, "id": memory_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found or already deleted",
            )
            
    except HTTPException:
        raise
    except Exception as exc:
        log.error("admin.team_memory: Failed to delete %s: %s", memory_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete team memory: {exc}",
        ) from exc
