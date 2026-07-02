"""Token quota enforcement and usage tracking service.

Provides atomic Redis-based counters with PostgreSQL persistence.
Integrates into the query pipeline to block over-quota requests and
record token consumption after LLM calls.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.token import TokenQuota, TokenUsageDaily, TokenUsageEvent

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
        return datetime.now(UTC).strftime("%Y-%m-%d")

    @staticmethod
    def _today_date() -> date:
        return datetime.now(UTC).date()

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
            # Only honour DAILY quotas for now (plan focuses on daily limits).
            # The native PG ENUM column comes back as a plain str at runtime (not the
            # QuotaPeriod enum), so read the value defensively — a bare ``.value`` here
            # raised AttributeError and, now that the token path actually runs (identity
            # fix), fail-closed every query.
            period = q.period.value if hasattr(q.period, "value") else q.period
            if period != "daily":
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

        for (level, key, limit), raw in zip(keys, results, strict=False):
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
        user_id: uuid.UUID | None,
        team_id: uuid.UUID | None = None,
        session_id: str = "",
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        operation: str = "sql_generation",
        conversation_id: str | None = None,
        cost_usd: Decimal | float | int = 0,
        priced: bool = True,
    ) -> None:
        """Increment Redis counters + persist a granular ``TokenUsageEvent`` and the
        daily rollup.

        Redis increment is atomic (``INCRBY``). The daily rollup upsert
        (``INSERT ... ON CONFLICT DO UPDATE``) keeps the aggregate correct under
        concurrency. The event row is the granular source of truth (per operation /
        model / conversation / cost). ``user_id`` may be ``None`` for system/vault ops
        that are not attributed to a user — those write the event but skip the
        user-keyed Redis counter and the (NOT NULL) daily rollup.
        """
        total_tokens = prompt_tokens + completion_tokens
        if total_tokens <= 0:
            return

        cost = Decimal(str(cost_usd or 0))
        date_str = self._today_str()
        date_obj = self._today_date()

        # ── 1. Redis counters (fast, atomic) ─────────────────────────
        redis_keys: list[str] = []
        if session_id:
            redis_keys.append(self._redis_key("session", session_id, date_str))
        if user_id:
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
            # 2a. Granular event (always) — source of truth for breakdowns.
            self.db.add(
                TokenUsageEvent(
                    id=uuid.uuid4(),
                    customer_id=customer_id,
                    user_id=user_id,
                    team_id=team_id,
                    conversation_id=conversation_id or None,
                    operation=operation,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost,
                    priced=priced,
                )
            )

            # 2b. Daily rollup (user-attributed ops only; user_id is NOT NULL there).
            if user_id is not None:
                stmt = insert(TokenUsageDaily).values(
                    customer_id=customer_id,
                    user_id=user_id,
                    usage_date=date_obj,
                    tokens_used=total_tokens,
                    cost_usd=cost,
                    model=model,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["customer_id", "user_id", "usage_date"],
                    set_={
                        "tokens_used": TokenUsageDaily.tokens_used + total_tokens,
                        "cost_usd": TokenUsageDaily.cost_usd + cost,
                        "model": model,  # keep last-used model
                    },
                )
                await self.db.execute(stmt)

            await self.db.commit()
        except Exception:
            logger.exception("Failed to persist token usage to DB – counters still in Redis")
            await self.db.rollback()


async def record_llm_usage(
    *,
    db: AsyncSession,
    redis: Redis,
    customer_uuid: uuid.UUID | None,
    user_uuid: uuid.UUID | None,
    team_uuid: uuid.UUID | None,
    conversation_id: str | None,
    operation: str,
    response: Any,
) -> None:
    """One-liner metering for any LLM call site: extract usage from ``response``,
    price it, and record a ``TokenUsageEvent`` (+ daily rollup) tagged with
    ``operation`` and ``conversation_id``. Never raises — metering must not break a
    turn. No-op when there is no customer to attribute to or no tokens were used.
    """
    if customer_uuid is None:
        return
    try:
        from backend.app.services.llm_cost import compute_cost, extract_cost, extract_usage

        usage = extract_usage(response)
        prompt = usage["prompt_tokens"]
        completion = usage["completion_tokens"]
        if prompt + completion <= 0:
            return

        # Cost source of truth: LiteLLM's response_cost (Task 12/13). Only fall back to the
        # local estimate when the proxy reported nothing. A reported 0 (self-hosted model) is
        # honoured as unpriced — tokens are still recorded, priced=False.
        rc = extract_cost(response)
        if rc is not None:
            cost = rc
            priced = rc > 0
        else:
            cost = compute_cost(usage["model"], prompt, completion)
            priced = cost > 0

        await TokenService(db=db, redis=redis).record_usage(
            customer_id=customer_uuid,
            user_id=user_uuid,
            team_id=team_uuid,
            session_id=conversation_id or "",
            model=usage["model"],
            prompt_tokens=prompt,
            completion_tokens=completion,
            operation=operation,
            conversation_id=conversation_id,
            cost_usd=cost,
            priced=priced,
        )
    except Exception:  # noqa: BLE001 — metering is best-effort, never break the turn
        logger.exception("record_llm_usage failed for operation=%s", operation)


# Lazily-created engines for background/system metering, cached PER EVENT LOOP.
# Metering runs both inline on the main loop (vault retrieval) and on the
# dedicated `aria-metering-loop` thread (submit_metering); asyncpg connections
# are bound to the loop that created them, so a single shared engine/pool would
# hand a foreign-loop connection to the other loop and die with "got Future
# attached to a different loop". Weak keys let a dead loop's entry be collected.
_meter_engines: Any = None


def _get_meter_engine():
    global _meter_engines
    import asyncio
    import weakref

    if _meter_engines is None:
        _meter_engines = weakref.WeakKeyDictionary()
    loop = asyncio.get_running_loop()
    eng = _meter_engines.get(loop)
    if eng is None:
        from sqlalchemy.ext.asyncio import create_async_engine

        from backend.app.core.config import get_settings

        eng = create_async_engine(get_settings().database_url, echo=False, pool_pre_ping=True)
        _meter_engines[loop] = eng
    return eng


async def record_system_llm_usage(
    *,
    workspace_id: str | None,
    operation: str,
    response: Any,
) -> None:
    """Meter a background/system LLM call that is not tied to a user or conversation
    (vault enrichment / suggestions / join-keys / embeddings). Resolves the customer
    from ``workspace_id`` and opens its own short-lived session on a shared engine.
    Best-effort: never raises, no-op when the workspace can't be resolved.
    """
    if not workspace_id:
        return
    redis = None
    try:
        from sqlalchemy import text as _text

        from backend.app.core.config import get_settings

        eng = _get_meter_engine()
        async with AsyncSession(eng) as s:
            customer_uuid = (
                await s.execute(
                    _text("SELECT id FROM customers WHERE slug = :w"), {"w": workspace_id}
                )
            ).scalar_one_or_none()
        if customer_uuid is None:
            return
        redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
        async with AsyncSession(eng) as s:
            await record_llm_usage(
                db=s,
                redis=redis,
                customer_uuid=customer_uuid,
                user_uuid=None,
                team_uuid=None,
                conversation_id=None,
                operation=operation,
                response=response,
            )
    except Exception:  # noqa: BLE001 — best-effort; never break the vault flow
        logger.exception("record_system_llm_usage failed for operation=%s", operation)
    finally:
        if redis is not None:
            await redis.aclose()
