"""Token quota enforcement and usage tracking service.

Provides atomic Redis-based counters with PostgreSQL persistence.
Integrates into the query pipeline to block over-quota requests and
record token consumption after LLM calls.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.token import TokenQuota, TokenUsageDaily

logger = logging.getLogger(__name__)

# ── Default limits (fall back when no DB quota row exists) ──────────────

DEFAULT_SESSION_LIMIT = 100_000
DEFAULT_USER_LIMIT = 500_000
DEFAULT_TEAM_LIMIT = 2_000_000
DEFAULT_CUSTOMER_LIMIT = 10_000_000

# How long Redis counters live before expiring (seconds). 48 h is
# longer than a calendar day so the counter never vanishes mid-day.
_REDIS_TTL = 172_800  # 48 hours


class QuotaExceededError(Exception):
    """Raised when a token quota is exceeded."""

    def __init__(self, level: str, target_id: str, limit: int) -> None:
        self.level = level
        self.target_id = target_id
        self.limit = limit
        super().__init__(f"{level} {target_id} exceeded token limit ({limit:,})")


class TokenService:
    """Atomic token-quota checker and usage recorder.

    Designed to be instantiated per-request (or per-pipeline-run) with a
    database session and a shared Redis connection::

        svc = TokenService(db=session, redis=redis_client)
        if not await svc.check_quota(...):
            raise HTTPException(429)

    Redis counters are the source of truth for *rate limiting*; PostgreSQL
    rows serve as the durable audit / analytics store.
    """

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _redis_key(level: str, target_id: str, date_str: str) -> str:
        """Build a scoped Redis key: ``aria:tokens:user:<uuid>:2026-06-13``."""
        return f"aria:tokens:{level}:{target_id}:{date_str}"

    @staticmethod
    def _today_str() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @staticmethod
    def _today_date() -> date:
        return datetime.now(timezone.utc).date()

    # ── quota lookup ─────────────────────────────────────────────────

    async def get_quotas(
        self,
        customer_id: uuid.UUID,
        user_id: uuid.UUID,
        team_id: uuid.UUID | None = None,
    ) -> dict[str, int]:
        """Return effective token limits for every level.

        DB rows override the defaults.  Precedence (highest wins):
        user-specific → team-specific → customer-wide → hard-coded default.
        """
        quotas: dict[str, int] = {
            "session": DEFAULT_SESSION_LIMIT,
            "user": DEFAULT_USER_LIMIT,
            "team": DEFAULT_TEAM_LIMIT,
            "customer": DEFAULT_CUSTOMER_LIMIT,
        }

        result = await self.db.execute(
            select(TokenQuota).where(
                TokenQuota.customer_id == customer_id,
                TokenQuota.is_active == True,  # noqa: E712
            )
        )
        for q in result.scalars().all():
            # Only honour DAILY quotas for now (plan focuses on daily limits)
            if q.period.value != "daily":
                continue
            if q.user_id is not None and q.user_id == user_id:
                quotas["user"] = q.token_limit
            elif q.team_id is not None and team_id is not None and q.team_id == team_id:
                quotas["team"] = q.token_limit
            elif q.user_id is None and q.team_id is None:
                quotas["customer"] = q.token_limit

        return quotas

    # ── quota enforcement ────────────────────────────────────────────

    async def check_quota(
        self,
        customer_id: uuid.UUID,
        user_id: uuid.UUID,
        team_id: uuid.UUID | None = None,
        session_id: str = "",
    ) -> bool:
        """Return *True* if the request is within all applicable limits.

        Checks session → user → team → customer, failing fast at the first
        exhausted level.
        """
        date_str = self._today_str()
        quotas = await self.get_quotas(customer_id, user_id, team_id)

        # Build Redis keys in check order
        keys: list[tuple[str, str, int]] = []  # (level, redis_key, limit)
        if session_id:
            keys.append(
                ("session", self._redis_key("session", session_id, date_str), quotas["session"])
            )
        keys.append(("user", self._redis_key("user", str(user_id), date_str), quotas["user"]))
        if team_id:
            keys.append(("team", self._redis_key("team", str(team_id), date_str), quotas["team"]))
        keys.append(
            (
                "customer",
                self._redis_key("customer", str(customer_id), date_str),
                quotas["customer"],
            )
        )

        # Single pipeline GET for all counters
        pipe = self.redis.pipeline()
        for _, key, _ in keys:
            pipe.get(key)
        results = await pipe.execute()

        for (level, key, limit), raw in zip(keys, results):
            used = int(raw) if raw else 0
            if used >= limit:
                logger.warning(
                    "%s %s exhausted: %s/%s tokens used (limit %s)",
                    level,
                    key,
                    f"{used:,}",
                    f"{limit:,}",
                    f"{limit:,}",
                )
                return False

        return True

    # ── usage recording ──────────────────────────────────────────────

    async def record_usage(
        self,
        *,
        customer_id: uuid.UUID,
        user_id: uuid.UUID,
        team_id: uuid.UUID | None = None,
        session_id: str = "",
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """Increment Redis counters and persist a row to PostgreSQL.

        Redis increment is atomic (``INCRBY``).  DB write uses an upsert
        (``INSERT ... ON CONFLICT DO UPDATE``) so the daily aggregate stays
        correct even under concurrent requests.
        """
        total_tokens = prompt_tokens + completion_tokens
        if total_tokens <= 0:
            return

        date_str = self._today_str()
        date_obj = self._today_date()

        # ── 1. Redis counters (fast, atomic) ─────────────────────────
        redis_keys: list[str] = []
        if session_id:
            redis_keys.append(self._redis_key("session", session_id, date_str))
        redis_keys.append(self._redis_key("user", str(user_id), date_str))
        if team_id:
            redis_keys.append(self._redis_key("team", str(team_id), date_str))
        redis_keys.append(self._redis_key("customer", str(customer_id), date_str))

        pipe = self.redis.pipeline()
        for key in redis_keys:
            pipe.incrby(key, total_tokens)
            pipe.expire(key, _REDIS_TTL, nx=True)
        await pipe.execute()

        # ── 2. PostgreSQL persistence (durable) ──────────────────────
        try:
            stmt = insert(TokenUsageDaily).values(
                customer_id=customer_id,
                user_id=user_id,
                usage_date=date_obj,
                tokens_used=total_tokens,
                model=model,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["customer_id", "user_id", "usage_date"],
                set_={
                    "tokens_used": TokenUsageDaily.tokens_used + total_tokens,
                    "model": model,  # keep last-used model
                },
            )
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception:
            logger.exception("Failed to persist token usage to DB – counters still in Redis")
            await self.db.rollback()
