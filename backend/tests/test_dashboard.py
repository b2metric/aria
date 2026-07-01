"""Tests for the dashboard endpoint and the audit user_id coercion helper.

Two concerns are covered here:

1. Workspace-scoped dashboard stats (``GET /api/dashboard``) must surface real
   query activity counted by ``customer_id`` even when the JWT ``sub`` is a
   non-UUID legacy identifier (e.g. ``admin-001``). Such an identity now resolves
   to a deterministic UUID, so the per-user block runs against its own (empty)
   session and returns 0, while the workspace block surfaces the real counts.
2. ``pipeline._coerce_user_uuid`` resolves a non-UUID identifier to a stable
   deterministic UUID (via ``resolve_identity_uuid``) and returns the parsed
   UUID for a valid one.
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

    async def __aenter__(self) -> _FakeSession:
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


def _sessionmaker_returning(*sessions):
    """Return a sessionmaker that yields each given session in call order.

    The dashboard handler opens one session context for the per-user block and
    a second for the workspace block. Giving each its own session means the
    workspace assertions cannot be silently broken by a future scalar call
    added to the per-user block (which would shift a shared counter).
    Once exhausted, the last session is reused.
    """
    calls = {"n": 0}

    def _maker():
        index = min(calls["n"], len(sessions) - 1)
        calls["n"] += 1
        return sessions[index]

    return _maker


def _non_uuid_user():
    from backend.app.auth.models import UserContext

    return UserContext(user_id="admin-001", workspace_id="acme")


# ── Task 1: workspace-scoped dashboard stats ─────────────────────────────────


@pytest.mark.asyncio
async def test_workspace_stats_count_customer_rows_when_user_is_non_uuid(monkeypatch):
    from backend.app.api import dashboard

    customer_id = uuid.uuid4()
    # A non-UUID identity now resolves to a deterministic UUID, so the per-user
    # block DOES run. Give it its own empty session (scalar → 0) so per-user
    # "Total Queries" is "0" and the workspace session's scalar call-order can't
    # be perturbed by it.
    per_user_session = _FakeSession(customer_row=None, scalar_returns=[])
    # Workspace scalar call order: ws_total, ws_today, ws_tokens_today,
    # ws_active_users, then 7 trend-day counts. Only ws_total is non-zero here.
    workspace_session = _FakeSession(
        customer_row=(customer_id,),
        scalar_returns=[3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    )
    monkeypatch.setattr(
        dashboard,
        "get_sessionmaker",
        lambda: _sessionmaker_returning(per_user_session, workspace_session),
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


# ── Task 3: team/user filters on workspace stats ─────────────────────────────


@pytest.mark.asyncio
async def test_workspace_stats_apply_team_filter_and_echo(monkeypatch):
    """Passing ``team_id`` scopes the workspace aggregates and is echoed back.

    The fake workspace session returns the seeded scalars regardless of the
    extra WHERE conditions, so this asserts the wiring: the filter is accepted,
    surfaced in ``body["filters"]``, and the seeded workspace count flows
    through to the "Workspace Queries" card.
    """
    from backend.app.api import dashboard

    customer_id = uuid.uuid4()
    team_uuid = str(uuid.uuid4())

    per_user_session = _FakeSession(customer_row=None, scalar_returns=[])
    # ws_total, ws_today, ws_tokens_today, ws_active_users, then 7 trend days.
    workspace_session = _FakeSession(
        customer_row=(customer_id,),
        scalar_returns=[5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    )
    monkeypatch.setattr(
        dashboard,
        "get_sessionmaker",
        lambda: _sessionmaker_returning(per_user_session, workspace_session),
    )

    async def _no_saved(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "backend.app.query.saved_queries.list_saved_queries", _no_saved
    )

    body = await dashboard.get_user_dashboard(
        workspace_id="acme",
        current_user=_non_uuid_user(),
        team_id=team_uuid,
    )

    assert body["filters"]["team_id"] == team_uuid
    assert body["filters"]["user_id"] is None

    ws_stats = {s["label"]: s["value"] for s in body["workspaceStats"]}
    assert ws_stats["Workspace Queries"] == "5"


# ── Sprint 2 Task 11: Cost Today card ────────────────────────────────────────


@pytest.mark.asyncio
async def test_workspace_stats_include_cost_today(monkeypatch):
    """The workspace block surfaces a "Cost Today (USD)" card summing
    ``TokenUsageDaily.cost_usd`` for today, next to the token total."""
    from decimal import Decimal

    from backend.app.api import dashboard

    customer_id = uuid.uuid4()
    per_user_session = _FakeSession(customer_row=None, scalar_returns=[])
    # Workspace scalar order (Task 18): ws_total, ws_today, ws_tokens_priced,
    # ws_tokens_unpriced, ws_cost_today, ws_active_users, then 7 trend-day counts.
    # Tokens Today is now priced+unpriced (all of today's, incl. unpriced).
    workspace_session = _FakeSession(
        customer_row=(customer_id,),
        scalar_returns=[7, 0, 12884, 0, Decimal("0.0330"), 0, 0, 0, 0, 0, 0, 0, 0],
    )
    monkeypatch.setattr(
        dashboard,
        "get_sessionmaker",
        lambda: _sessionmaker_returning(per_user_session, workspace_session),
    )

    async def _no_saved(*args, **kwargs):
        return []

    monkeypatch.setattr("backend.app.query.saved_queries.list_saved_queries", _no_saved)

    body = await dashboard.get_user_dashboard(
        workspace_id="acme", current_user=_non_uuid_user()
    )

    ws_stats = {s["label"]: s["value"] for s in body["workspaceStats"]}
    assert ws_stats["Tokens Today"] == "12,884"
    assert ws_stats["Cost Today (USD)"] == "$0.0330"


# ── Task 18: priced vs unpriced token split ──────────────────────────────────


@pytest.mark.asyncio
async def test_workspace_tokens_today_splits_priced_unpriced(monkeypatch):
    """The workspace "Tokens Today" is the sum of priced + unpriced tokens for
    today (from ``token_usage_events``), and the response exposes a ``tokenSplit``
    breakdown so the dashboard can show the priced-vs-unpriced share. Unpriced =
    self-hosted / $0-cost calls (incl. system ops), which are counted even though
    they cost nothing."""
    from decimal import Decimal

    from backend.app.api import dashboard

    customer_id = uuid.uuid4()
    per_user_session = _FakeSession(customer_row=None, scalar_returns=[])
    # ws order: ws_total, ws_today, ws_tokens_priced, ws_tokens_unpriced,
    # ws_cost_today, ws_active_users, then 7 trend-day counts.
    workspace_session = _FakeSession(
        customer_row=(customer_id,),
        scalar_returns=[7, 0, 10000, 2500, Decimal("0.0330"), 0, 0, 0, 0, 0, 0, 0, 0],
    )
    monkeypatch.setattr(
        dashboard,
        "get_sessionmaker",
        lambda: _sessionmaker_returning(per_user_session, workspace_session),
    )

    async def _no_saved(*args, **kwargs):
        return []

    monkeypatch.setattr("backend.app.query.saved_queries.list_saved_queries", _no_saved)

    body = await dashboard.get_user_dashboard(
        workspace_id="acme", current_user=_non_uuid_user()
    )

    ws_stats = {s["label"]: s["value"] for s in body["workspaceStats"]}
    assert ws_stats["Tokens Today"] == "12,500"  # 10000 priced + 2500 unpriced

    split = body["tokenSplit"]
    assert split["priced"] == 10000
    assert split["unpriced"] == 2500
    assert split["total"] == 12500


# ── Task 2: _coerce_user_uuid ────────────────────────────────────────────────


def test_non_uuid_user_id_resolves_deterministically():
    from backend.app.auth.identity import resolve_identity_uuid
    from backend.app.query import pipeline
    result = pipeline._coerce_user_uuid("admin-001")
    assert result == resolve_identity_uuid("admin-001")


def test_valid_uuid_user_id_coerces():
    from backend.app.query import pipeline

    some_uuid = uuid.uuid4()
    assert pipeline._coerce_user_uuid(str(some_uuid)) == some_uuid


def test_none_user_id_returns_none():
    from backend.app.query import pipeline

    assert pipeline._coerce_user_uuid(None) is None
