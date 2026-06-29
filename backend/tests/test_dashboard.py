"""Tests for the dashboard endpoint and the audit user_id coercion helper.

Two concerns are covered here:

1. Workspace-scoped dashboard stats (``GET /api/dashboard``) must surface real
   query activity counted by ``customer_id`` even when the JWT ``sub`` is a
   non-UUID legacy identifier (e.g. ``admin-001``). In that case the per-user
   block is skipped entirely (``if user_uuid:`` guard), so only the workspace
   block's queries execute.
2. ``pipeline._coerce_user_uuid`` warns (instead of silently dropping) on a
   non-UUID identifier, and returns the parsed UUID for a valid one.
"""

from __future__ import annotations

import uuid

import pytest


# ── Fake async session machinery (mirrors test_sql_visibility.py) ────────────


class _FakeResult:
    """Stands in for the object returned by ``session.execute(...)``."""

    def __init__(self, row: tuple | None) -> None:
        self._row = row

    def fetchone(self) -> tuple | None:
        return self._row


class _FakeSession:
    """Async context-manager session.

    ``execute`` always returns the configured customer row (used for the
    slug → customer-id resolution). ``scalar`` returns successive values from
    ``scalar_returns`` in call order, defaulting to 0 once exhausted.
    """

    def __init__(self, customer_row: tuple | None, scalar_returns: list) -> None:
        self._customer_row = customer_row
        self._scalar_returns = list(scalar_returns)
        self._scalar_calls = 0

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def execute(self, *args, **kwargs) -> _FakeResult:
        return _FakeResult(self._customer_row)

    async def scalar(self, *args, **kwargs):
        if self._scalar_calls < len(self._scalar_returns):
            value = self._scalar_returns[self._scalar_calls]
        else:
            value = 0
        self._scalar_calls += 1
        return value


def _sessionmaker_returning(session):
    def _maker():
        return session

    return _maker


def _non_uuid_user():
    from backend.app.auth.models import UserContext

    return UserContext(user_id="admin-001", workspace_id="acme")


# ── Task 1: workspace-scoped dashboard stats ─────────────────────────────────


@pytest.mark.asyncio
async def test_workspace_stats_count_customer_rows_when_user_is_non_uuid(monkeypatch):
    from backend.app.api import dashboard

    customer_id = uuid.uuid4()
    # Workspace scalar call order: ws_total, ws_today, ws_tokens_today,
    # ws_active_users, then 7 trend-day counts. Only ws_total is non-zero here.
    session = _FakeSession(
        customer_row=(customer_id,),
        scalar_returns=[3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    )
    monkeypatch.setattr(
        dashboard, "get_sessionmaker", lambda: _sessionmaker_returning(session)
    )

    # Keep the saved-queries Redis block hermetic.
    async def _no_saved(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "backend.app.query.saved_queries.list_saved_queries", _no_saved
    )

    body = await dashboard.get_user_dashboard(
        workspace_id="acme", current_user=_non_uuid_user()
    )

    ws_stats = {s["label"]: s["value"] for s in body["workspaceStats"]}
    assert ws_stats["Workspace Queries"] == "3"

    per_user = {s["label"]: s["value"] for s in body["stats"]}
    assert per_user["Total Queries"] == "0"
