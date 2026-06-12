"""Admin: list agent memory entries (real data from Mem0 + Qdrant)."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.auth.dependencies import get_current_user
from backend.app.memory.service import MemoryService

log = logging.getLogger("aria.admin")
router = APIRouter()


@router.get("")
async def get_all_memories(current_user: Any = Depends(get_current_user)) -> list[dict]:
    """Agent memory entries for the admin's workspace/user (admin only).

    Agent memory persistence lives in **Qdrant via Mem0** (LOCKED-DECISIONS #1) — this
    reads the actual memories there, NOT the (currently unused) Postgres memory_entries
    table. Returns [] if Mem0/Qdrant is unavailable.
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    user_id = getattr(current_user, "user_id", None) or ""
    try:
        mems = MemoryService.get_instance().get_all_memories(
            user_id=user_id, workspace_id=workspace_id
        )
    except Exception as exc:  # noqa: BLE001 — admin view must not 500 on a memory backend hiccup
        log.warning("admin.memory: Mem0/Qdrant lookup failed: %s", exc)
        return []

    return [
        {
            "id": m.get("id"),
            "entity_id": user_id,
            "content": m.get("memory") or m.get("content") or "",
            "created_at": m.get("created_at"),
            "metadata": m.get("metadata"),
        }
        for m in mems
    ]
