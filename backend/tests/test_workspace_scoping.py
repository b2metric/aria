"""TIER 2 item 11 — no hardcoded cross-tenant workspace fallback.

``get_workspace_id`` must never fall back to the ``stc-kuwait`` tenant: a token
with no workspace must be denied, not silently scoped to another customer.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.auth.dependencies import get_workspace_id
from backend.app.auth.models import Role, UserContext


@pytest.mark.asyncio
async def test_returns_token_workspace():
    user = UserContext(sub="s", user_id="u", workspace_id="acme", role=Role.ANALYST)
    assert await get_workspace_id(user) == "acme"


@pytest.mark.asyncio
async def test_missing_workspace_denied_not_stc_kuwait():
    user = UserContext(sub="s", user_id="u", workspace_id=None, role=Role.ANALYST)
    with pytest.raises(HTTPException) as exc:
        await get_workspace_id(user)
    assert exc.value.status_code == 403
