"""TIER 2 item 9 — rate limiting (now also applied to public onboarding).

Pins the fixed-window limiter primitive that ``/api/onboarding/register`` uses
to throttle abusive self-registration by client IP.
"""

from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis

from backend.app.services.rate_limit import RateLimitExceeded, check_rate_limit


@pytest.mark.asyncio
async def test_blocks_after_limit_exceeded():
    r = FakeRedis(decode_responses=True)
    # 3 within the window are allowed; the 4th is rejected.
    for _ in range(3):
        await check_rate_limit(r, "ip-1", limit=3, window=60)
    with pytest.raises(RateLimitExceeded) as exc:
        await check_rate_limit(r, "ip-1", limit=3, window=60)
    assert exc.value.retry_after > 0


@pytest.mark.asyncio
async def test_independent_keys_do_not_share_budget():
    r = FakeRedis(decode_responses=True)
    for _ in range(3):
        await check_rate_limit(r, "ip-1", limit=3, window=60)
    # A different IP still has its full budget.
    await check_rate_limit(r, "ip-2", limit=3, window=60)
