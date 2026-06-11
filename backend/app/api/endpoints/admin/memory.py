"""Admin: list agent memory entries (real data from the memory_entries table)."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.auth.dependencies import get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.memory import MemoryEntry

log = logging.getLogger("aria.admin")
router = APIRouter()


@router.get("")
async def get_all_memories(current_user: Any = Depends(get_current_user)) -> list[dict]:
    """Recent agent memory entries (admin only).

    Embedding vectors live in Qdrant (LOCKED-DECISIONS #1); this returns the
    relational entries (owner / key / content), capped at 200 most-recent.
    Degrades to [] if the table is not yet migrated / DB is unavailable.
    NOTE: returns instance-wide entries; scope by customer for multi-tenant prod.
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    try:
        async with get_sessionmaker()() as session:
            rows = (
                await session.execute(
                    select(MemoryEntry).order_by(MemoryEntry.created_at.desc()).limit(200)
                )
            ).scalars().all()
    except SQLAlchemyError as exc:
        log.warning("admin.memory: query failed (table not migrated?): %s", exc)
        return []

    return [
        {
            "id": str(m.id),
            "entity_id": str(m.user_id or m.customer_id or ""),
            "key": m.key,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]
