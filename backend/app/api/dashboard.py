import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select, text

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

    # ── Workspace-scoped stats (counted by customer_id) ──────────────────
    # In this environment the JWT ``sub`` is often a non-UUID legacy identifier,
    # so the per-user block above returns 0 even when real query activity exists
    # (those rows carry a valid customer_id but a NULL user_id). Counting by the
    # workspace's customer_id surfaces that activity. Best-effort: never break
    # the dashboard.
    ws_total = 0
    ws_today = 0
    ws_tokens_today = 0
    ws_active_users = 0
    ws_trend: list[dict] = []

    try:
        async with sessionmaker() as session:
            # Resolve customer UUID from the workspace slug (mirrors the audit
            # resolution in backend/app/query/pipeline.py).
            customer_id = None
            result = await session.execute(
                text("SELECT id FROM customers WHERE slug = :slug"),
                {"slug": workspace_id},
            )
            row = result.fetchone()
            if row:
                customer_id = row[0]

            if customer_id is not None:
                ws_total = (
                    await session.scalar(
                        select(func.count(DataAuditLog.id)).where(
                            DataAuditLog.customer_id == customer_id,
                            DataAuditLog.action == "query",
                        )
                    )
                    or 0
                )

                ws_today = (
                    await session.scalar(
                        select(func.count(DataAuditLog.id)).where(
                            DataAuditLog.customer_id == customer_id,
                            DataAuditLog.action == "query",
                            DataAuditLog.created_at >= today,
                        )
                    )
                    or 0
                )

                ws_tokens_today = (
                    await session.scalar(
                        select(func.sum(TokenUsageDaily.tokens_used)).where(
                            TokenUsageDaily.customer_id == customer_id,
                            TokenUsageDaily.usage_date == today.date(),
                        )
                    )
                    or 0
                )

                ws_active_users = (
                    await session.scalar(
                        select(func.count(distinct(DataAuditLog.user_id))).where(
                            DataAuditLog.customer_id == customer_id,
                            DataAuditLog.action == "query",
                            DataAuditLog.created_at >= today - timedelta(days=7),
                            DataAuditLog.user_id.isnot(None),
                        )
                    )
                    or 0
                )

                for i in range(6, -1, -1):
                    day = today - timedelta(days=i)
                    next_day = day + timedelta(days=1)

                    day_queries = (
                        await session.scalar(
                            select(func.count(DataAuditLog.id)).where(
                                DataAuditLog.customer_id == customer_id,
                                DataAuditLog.action == "query",
                                DataAuditLog.created_at >= day,
                                DataAuditLog.created_at < next_day,
                            )
                        )
                        or 0
                    )

                    day_str = day.strftime("%b %d")
                    ws_trend.append({"date": day_str, "queries": day_queries})
    except Exception as exc:
        log.warning("Workspace dashboard fetch failed: %s", exc)

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

    workspace_stats = [
        {"label": "Workspace Queries", "value": str(ws_total), "icon": "Database"},
        {
            "label": "Queries Today",
            "value": str(ws_today),
            "change": "Workspace",
            "changeType": "neutral",
            "icon": "Activity",
        },
        {"label": "Tokens Today", "value": f"{ws_tokens_today:,}", "icon": "Zap"},
        {"label": "Active Users (7d)", "value": str(ws_active_users), "icon": "Users"},
    ]

    return {
        "stats": stats,
        "workspaceStats": workspace_stats,
        "chartData": ws_trend or recent_trend,
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
