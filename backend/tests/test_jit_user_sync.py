"""TIER 2 item 10 — JIT user provisioning is wired into get_current_user.

``sync_user_from_token`` existed but had zero callers, so JWT-only users got no
local row. It is now called best-effort + cached from get_current_user; a sync
failure must never break authentication.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.auth import dependencies as deps
from backend.app.auth.models import TokenPayload


def _payload(sub: str) -> TokenPayload:
    return TokenPayload(sub=sub, workspace_id="ws1", role="analyst", user_id=sub)


@pytest.mark.asyncio
async def test_jit_sync_called_once_per_sub():
    deps._synced_users.discard("sub-1")
    with (
        patch.object(deps, "decode_token", AsyncMock(return_value=_payload("sub-1"))),
        patch("backend.app.auth.sync.sync_user_from_token", AsyncMock()) as sync_mock,
    ):
        u1 = await deps.get_current_user(token="t")
        await deps.get_current_user(token="t")  # second call → cached, no re-sync

    assert u1.sub == "sub-1"
    sync_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_jit_sync_fires_on_user_id_when_sub_absent():
    # Tokens may carry the identity in a custom `user_id` claim with no `sub`
    # (e.g. the `admin-001` dev identity). JIT-sync must still provision, keyed
    # on `user_id` — otherwise the audit FK (user_id → users.id) finds no row.
    deps._synced_users.discard("admin-001")
    payload = TokenPayload(sub=None, workspace_id="ws1", role="admin", user_id="admin-001")
    with (
        patch.object(deps, "decode_token", AsyncMock(return_value=payload)),
        patch("backend.app.auth.sync.sync_user_from_token", AsyncMock()) as sync_mock,
    ):
        user = await deps.get_current_user(token="t")

    assert user.user_id == "admin-001"
    sync_mock.assert_awaited_once()
    assert "admin-001" in deps._synced_users


@pytest.mark.asyncio
async def test_jit_sync_failure_does_not_break_auth():
    deps._synced_users.discard("sub-2")
    with (
        patch.object(deps, "decode_token", AsyncMock(return_value=_payload("sub-2"))),
        patch(
            "backend.app.auth.sync.sync_user_from_token",
            AsyncMock(side_effect=RuntimeError("db down")),
        ),
    ):
        user = await deps.get_current_user(token="t")

    assert user.sub == "sub-2"  # auth still succeeds despite the sync error
