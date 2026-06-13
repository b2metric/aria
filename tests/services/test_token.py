"""Unit tests for TokenService (token quota enforcement & tracking)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.token import (
    DEFAULT_CUSTOMER_LIMIT,
    DEFAULT_SESSION_LIMIT,
    DEFAULT_TEAM_LIMIT,
    DEFAULT_USER_LIMIT,
    TokenService,
)


# ── helpers ────────────────────────────────────────────────────────────


def _make_uuid() -> uuid.UUID:
    return uuid.uuid4()


# ── Redis key format ───────────────────────────────────────────────────


class TestRedisKeyFormat:
    """Verify Redis key construction."""

    def test_session_key(self):
        key = TokenService._redis_key("session", "abc123", "2026-06-14")
        assert key == "aria:tokens:session:abc123:2026-06-14"

    def test_user_key(self):
        uid = str(_make_uuid())
        key = TokenService._redis_key("user", uid, "2026-06-14")
        assert key == f"aria:tokens:user:{uid}:2026-06-14"

    def test_team_key(self):
        tid = str(_make_uuid())
        key = TokenService._redis_key("team", tid, "2026-06-14")
        assert key == f"aria:tokens:team:{tid}:2026-06-14"

    def test_customer_key(self):
        cid = str(_make_uuid())
        key = TokenService._redis_key("customer", cid, "2026-06-14")
        assert key == f"aria:tokens:customer:{cid}:2026-06-14"


# ── get_quotas ─────────────────────────────────────────────────────────


class TestGetQuotas:
    """Quota lookups with DB fallback."""

    @pytest.mark.asyncio
    async def test_defaults_when_no_db_rows(self):
        """When no TokenQuota rows exist, defaults are returned."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        # Simulate empty DB result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        svc = TokenService(db=mock_db, redis=mock_redis)
        customer_id = _make_uuid()
        user_id = _make_uuid()

        quotas = await svc.get_quotas(customer_id, user_id)

        assert quotas == {
            "session": DEFAULT_SESSION_LIMIT,
            "user": DEFAULT_USER_LIMIT,
            "team": DEFAULT_TEAM_LIMIT,
            "customer": DEFAULT_CUSTOMER_LIMIT,
        }

    @pytest.mark.asyncio
    async def test_user_quota_overrides_default(self):
        """A user-specific TokenQuota row overrides the default."""
        from backend.app.models.token import TokenQuota
        from backend.app.models.enums import QuotaPeriod

        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        customer_id = _make_uuid()
        user_id = _make_uuid()

        q = TokenQuota(
            customer_id=customer_id,
            user_id=user_id,
            period=QuotaPeriod.DAILY,
            token_limit=200_000,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [q]
        mock_db.execute.return_value = mock_result

        svc = TokenService(db=mock_db, redis=mock_redis)
        quotas = await svc.get_quotas(customer_id, user_id)

        assert quotas["user"] == 200_000
        assert quotas["session"] == DEFAULT_SESSION_LIMIT  # unchanged

    @pytest.mark.asyncio
    async def test_team_quota_overrides_default(self):
        """A team-specific TokenQuota row overrides the default."""
        from backend.app.models.token import TokenQuota
        from backend.app.models.enums import QuotaPeriod

        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        customer_id = _make_uuid()
        user_id = _make_uuid()
        team_id = _make_uuid()

        q = TokenQuota(
            customer_id=customer_id,
            team_id=team_id,
            period=QuotaPeriod.DAILY,
            token_limit=3_000_000,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [q]
        mock_db.execute.return_value = mock_result

        svc = TokenService(db=mock_db, redis=mock_redis)
        quotas = await svc.get_quotas(customer_id, user_id, team_id=team_id)

        assert quotas["team"] == 3_000_000
        assert quotas["user"] == DEFAULT_USER_LIMIT  # unchanged

    @pytest.mark.asyncio
    async def test_customer_wide_quota(self):
        """A customer-wide (no user/team) quota overrides the customer default."""
        from backend.app.models.token import TokenQuota
        from backend.app.models.enums import QuotaPeriod

        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        customer_id = _make_uuid()
        user_id = _make_uuid()

        q = TokenQuota(
            customer_id=customer_id,
            user_id=None,
            team_id=None,
            period=QuotaPeriod.DAILY,
            token_limit=5_000_000,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [q]
        mock_db.execute.return_value = mock_result

        svc = TokenService(db=mock_db, redis=mock_redis)
        quotas = await svc.get_quotas(customer_id, user_id)

        assert quotas["customer"] == 5_000_000

    @pytest.mark.asyncio
    async def test_user_quota_skips_non_matching_user(self):
        """A quota targeting a different user is not applied."""
        from backend.app.models.token import TokenQuota
        from backend.app.models.enums import QuotaPeriod

        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        customer_id = _make_uuid()
        user_id = _make_uuid()
        other_user = _make_uuid()

        q = TokenQuota(
            customer_id=customer_id,
            user_id=other_user,  # different user
            period=QuotaPeriod.DAILY,
            token_limit=999,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [q]
        mock_db.execute.return_value = mock_result

        svc = TokenService(db=mock_db, redis=mock_redis)
        quotas = await svc.get_quotas(customer_id, user_id)

        # Quota is for a different user, so defaults apply
        assert quotas["user"] == DEFAULT_USER_LIMIT
        assert quotas["customer"] == DEFAULT_CUSTOMER_LIMIT


# ── check_quota ────────────────────────────────────────────────────────


class TestCheckQuota:
    """Quota enforcement (Redis counter checks)."""

    @pytest.mark.asyncio
    async def test_allowed_when_under_limits(self):
        """Returns True when all counters are well below limits."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        # Empty DB → defaults
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Redis pipeline returns zeros
        mock_pipe = MagicMock()
        mock_pipe.get.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(return_value=[None, None, None, None])
        mock_redis.pipeline.return_value = mock_pipe

        svc = TokenService(db=mock_db, redis=mock_redis)
        customer_id = _make_uuid()
        user_id = _make_uuid()
        team_id = _make_uuid()

        allowed = await svc.check_quota(customer_id, user_id, team_id=team_id, session_id="sess-1")

        assert allowed is True

    @pytest.mark.asyncio
    async def test_blocked_when_user_exceeds(self):
        """Returns False when user-level counter exceeds the limit."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # session=0, user=LIMIT+1, team=0, customer=0
        mock_pipe = MagicMock()
        mock_pipe.get.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(
            return_value=[
                None,  # session
                str(DEFAULT_USER_LIMIT + 1),  # user
                None,  # team
                None,  # customer
            ]
        )
        mock_redis.pipeline.return_value = mock_pipe

        svc = TokenService(db=mock_db, redis=mock_redis)
        customer_id = _make_uuid()
        user_id = _make_uuid()

        allowed = await svc.check_quota(customer_id, user_id, session_id="sess-1")

        assert allowed is False

    @pytest.mark.asyncio
    async def test_blocked_when_team_exceeds(self):
        """Returns False when team-level counter exceeds the limit."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        mock_pipe = MagicMock()
        mock_pipe.get.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(
            return_value=[
                None,  # session
                None,  # user
                str(DEFAULT_TEAM_LIMIT),  # team (exactly at limit)
                None,  # customer
            ]
        )
        mock_redis.pipeline.return_value = mock_pipe

        svc = TokenService(db=mock_db, redis=mock_redis)
        customer_id = _make_uuid()
        user_id = _make_uuid()
        team_id = _make_uuid()

        allowed = await svc.check_quota(customer_id, user_id, team_id=team_id, session_id="sess-1")

        assert allowed is False

    @pytest.mark.asyncio
    async def test_allowed_exactly_at_limit(self):
        """Exactly at the limit is blocked (>= check)."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        mock_pipe = MagicMock()
        mock_pipe.get.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(
            return_value=[
                str(DEFAULT_SESSION_LIMIT),  # session exactly at limit
                None,
                None,
                None,
            ]
        )
        mock_redis.pipeline.return_value = mock_pipe

        svc = TokenService(db=mock_db, redis=mock_redis)
        customer_id = _make_uuid()
        user_id = _make_uuid()

        allowed = await svc.check_quota(customer_id, user_id, session_id="sess-1")

        assert allowed is False  # exactly at limit = blocked

    @pytest.mark.asyncio
    async def test_no_session_id_skips_session_check(self):
        """When session_id is empty, session check is skipped entirely."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Only 3 keys: user, team, customer
        mock_pipe = MagicMock()
        mock_pipe.get.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(return_value=[None, None, None])
        mock_redis.pipeline.return_value = mock_pipe

        svc = TokenService(db=mock_db, redis=mock_redis)
        customer_id = _make_uuid()
        user_id = _make_uuid()
        team_id = _make_uuid()

        allowed = await svc.check_quota(customer_id, user_id, team_id=team_id, session_id="")

        assert allowed is True
        # Verify exactly 3 keys were fetched
        assert mock_pipe.get.call_count == 3


# ── record_usage ───────────────────────────────────────────────────────


class TestRecordUsage:
    """Usage recording (Redis + DB)."""

    @pytest.mark.asyncio
    async def test_increments_redis_and_persists_db(self):
        """Happy path: Redis INCRBY and DB upsert both succeed."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        mock_pipe = MagicMock()
        mock_pipe.incrby.return_value = mock_pipe
        mock_pipe.expire.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(return_value=[100, 200, 300, 400])
        mock_redis.pipeline.return_value = mock_pipe

        svc = TokenService(db=mock_db, redis=mock_redis)
        customer_id = _make_uuid()
        user_id = _make_uuid()
        team_id = _make_uuid()

        await svc.record_usage(
            customer_id=customer_id,
            user_id=user_id,
            team_id=team_id,
            session_id="sess-1",
            model="gpt-4",
            prompt_tokens=50,
            completion_tokens=30,
        )

        # Redis pipeline was executed
        mock_pipe.execute.assert_awaited_once()

        # 4 keys × 2 commands (incrby + expire) = 8 pipeline calls
        assert mock_pipe.incrby.call_count == 4
        assert mock_pipe.expire.call_count == 4

        # DB was executed and committed
        mock_db.execute.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_zero_tokens_skips_everything(self):
        """Zero or negative token usage is a no-op."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        svc = TokenService(db=mock_db, redis=mock_redis)
        customer_id = _make_uuid()
        user_id = _make_uuid()

        await svc.record_usage(
            customer_id=customer_id,
            user_id=user_id,
            model="gpt-4",
            prompt_tokens=0,
            completion_tokens=0,
        )

        # No Redis or DB calls
        mock_redis.pipeline.assert_not_called()
        mock_db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_db_persist_failure_is_handled_gracefully(self):
        """When the DB upsert fails, the error is logged and rolled back."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.side_effect = RuntimeError("DB down")
        mock_redis = AsyncMock(spec=Redis)

        mock_pipe = MagicMock()
        mock_pipe.incrby.return_value = mock_pipe
        mock_pipe.expire.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(return_value=[1, 2])
        mock_redis.pipeline.return_value = mock_pipe

        svc = TokenService(db=mock_db, redis=mock_redis)
        customer_id = _make_uuid()
        user_id = _make_uuid()

        # Should NOT raise — error is swallowed
        await svc.record_usage(
            customer_id=customer_id,
            user_id=user_id,
            model="gpt-4",
            prompt_tokens=10,
            completion_tokens=5,
        )

        # Redis still worked
        mock_pipe.execute.assert_awaited_once()
        # DB was rolled back
        mock_db.rollback.assert_awaited_once()
        # DB was NOT committed
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_session_skips_session_key(self):
        """Empty session_id omits the Redis session counter."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        mock_pipe = MagicMock()
        mock_pipe.incrby.return_value = mock_pipe
        mock_pipe.expire.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(return_value=[1, 2, 3])
        mock_redis.pipeline.return_value = mock_pipe

        svc = TokenService(db=mock_db, redis=mock_redis)
        customer_id = _make_uuid()
        user_id = _make_uuid()

        await svc.record_usage(
            customer_id=customer_id,
            user_id=user_id,
            session_id="",
            model="gpt-4",
            prompt_tokens=10,
            completion_tokens=5,
        )

        # 3 keys (user, customer only — no team, no session) → 3 incrby + 3 expire
        assert mock_pipe.incrby.call_count == 2  # user + customer
        assert mock_pipe.expire.call_count == 2

    @pytest.mark.asyncio
    async def test_no_team_skips_team_key(self):
        """None team_id omits the Redis team counter."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_redis = AsyncMock(spec=Redis)

        mock_pipe = MagicMock()
        mock_pipe.incrby.return_value = mock_pipe
        mock_pipe.expire.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(return_value=[1, 2, 3])
        mock_redis.pipeline.return_value = mock_pipe

        svc = TokenService(db=mock_db, redis=mock_redis)
        customer_id = _make_uuid()
        user_id = _make_uuid()

        await svc.record_usage(
            customer_id=customer_id,
            user_id=user_id,
            team_id=None,
            session_id="sess-1",
            model="gpt-4",
            prompt_tokens=10,
            completion_tokens=5,
        )

        # session + user + customer = 3 keys
        assert mock_pipe.incrby.call_count == 3
        assert mock_pipe.expire.call_count == 3
