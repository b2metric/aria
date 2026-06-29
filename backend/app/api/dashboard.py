import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from backend.app.auth.dependencies import UserContext, WorkspaceID, get_current_user
from backend.app.db.session import get_sessionmaker
from backend.app.models.governance import DataAuditLog
from backend.app.models.token import TokenUsageDaily

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def get_user_dashboard(
    workspace_id: WorkspaceID,
    current_user: UserContext = Depends(get_current_user),
):
    """Get dashboard stats for the current user."""
    sessionmaker = get_sessionmaker()

    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today - timedelta(days=today.weekday())

    # Defaults
    total_queries = 0
    queries_today = 0
    tokens_today = 0
    recent_trend = []

    try:
        user_uuid = uuid.UUID(str(current_user.user_id))
    except (ValueError, TypeError):
        user_uuid = None

    try:
        async with sessionmaker() as session:
            if user_uuid:
                # 1. Total Queries (All time for this user)
                total_queries = (
                    await session.scalar(
                        select(func.count(DataAuditLog.id)).where(
                            DataAuditLog.user_id == user_uuid, DataAuditLog.action == "query"
                        )
                    )
                    or 0
                )

                # 2. Queries Today
                queries_today = (
                    await session.scalar(
                        select(func.count(DataAuditLog.id)).where(
                            DataAuditLog.user_id == user_uuid,
                            DataAuditLog.action == "query",
                            DataAuditLog.created_at >= today,
                        )
                    )
                    or 0
                )

                # 3. Tokens Today
                tokens_today = (
                    await session.scalar(
                        select(func.sum(TokenUsageDaily.tokens_used)).where(
                            TokenUsageDaily.user_id == user_uuid,
                            TokenUsageDaily.usage_date == today.date(),
                        )
                    )
                    or 0
                )

                # 4. Chart Data (Last 7 Days)
                for i in range(6, -1, -1):
                    day = today - timedelta(days=i)
                    next_day = day + timedelta(days=1)

                    day_queries = (
                        await session.scalar(
                            select(func.count(DataAuditLog.id)).where(
                                DataAuditLog.user_id == user_uuid,
                                DataAuditLog.action == "query",
                                DataAuditLog.created_at >= day,
                                DataAuditLog.created_at < next_day,
                            )
                        )
                        or 0
                    )

                    day_str = day.strftime("%b %d")  # e.g. "Jun 15"
                    recent_trend.append({"date": day_str, "queries": day_queries})

    except Exception as exc:
        log.warning("User dashboard fetch failed: %s", exc)

    # Saved-queries count (best-effort; never break the dashboard).
    saved_queries_count = 0
    try:
        from redis.asyncio import Redis

        from backend.app.core.config import get_settings
        from backend.app.query.saved_queries import list_saved_queries

        _redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
        try:
            saved = await list_saved_queries(
                _redis, workspace_id=workspace_id, user_id=str(current_user.user_id)
            )
            saved_queries_count = len(saved)
        finally:
            await _redis.aclose()
    except Exception as exc:
        log.warning("Saved-queries count failed: %s", exc)

    stats = [
        {"label": "Total Queries", "value": str(total_queries), "icon": "Database"},
        {
            "label": "Queries Today",
            "value": str(queries_today),
            "change": "Active",
            "changeType": "up",
            "icon": "Activity",
        },
        {"label": "Tokens Used Today", "value": f"{tokens_today:,}", "icon": "Zap"},
        {
            "label": "Saved Queries",
            "value": str(saved_queries_count),
            "icon": "Save",
        },
    ]

    return {
        "stats": stats,
        "chartData": recent_trend,
        "chartConfig": {
            "type": "area",
            "xKey": "date",
            "yKeys": ["queries"],
            "title": "Query Volume (Last 7 Days)",
            "colors": ["#3b82f6"],
        },
        # These will be fetched/populated by the frontend
        "recentConversations": [],
        "savedQueries": [],
    }
