import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, text
from datetime import datetime, timezone, timedelta
from typing import Any

from backend.app.auth.dependencies import get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.organization import User, Team
from backend.app.models.governance import DataAuditLog
from backend.app.models.token import TokenUsageDaily

log = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def get_dashboard_metrics(current_user: Any = Depends(get_current_user)):
    """Get high-level metrics for the admin dashboard."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
        
    sessionmaker = get_sessionmaker()
    metrics = {
        "total_users": 0,
        "active_teams": 0,
        "queries_today": 0,
        "tokens_used_today": 0
    }
    
    try:
        async with sessionmaker() as session:
            # Total Users
            metrics["total_users"] = await session.scalar(select(func.count(User.id)))
            
            # Active Teams
            metrics["active_teams"] = await session.scalar(select(func.count(Team.id)))
            
            # Queries Today
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            metrics["queries_today"] = await session.scalar(
                select(func.count(DataAuditLog.id)).where(
                    DataAuditLog.action == "query",
                    DataAuditLog.timestamp >= today
                )
            )
            
            # Tokens Used Today
            tokens = await session.scalar(
                select(func.sum(TokenUsageDaily.tokens_used)).where(TokenUsageDaily.usage_date == today.date())
            )
            metrics["tokens_used_today"] = tokens or 0
            
    except Exception as exc:
        log.error("Failed to fetch dashboard metrics: %s", exc)
        # Continue with zeros rather than failing the whole dashboard
        
    return metrics
