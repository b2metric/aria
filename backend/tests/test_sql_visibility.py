"""Unit tests for per-user SQL-visibility override + governance audit.

These exercise the pure helpers in ``backend.app.query.sql_visibility`` (no DB
required) plus the audit-writing helpers wired into the query pipeline.

SQL visibility is resolved as: the user's explicit ``sql_visibility`` override
(``True``/``False``) wins; ``None`` inherits the role default
(``_can_view_sql(role)`` → only admin/analyst by default).  When a user may NOT
see SQL, the streaming response omits the raw SQL string and the raw row-level
tabular grid, while STILL returning the chart visualisation and the insight.

Governance audit: every time RLS row filters actually rewrite the SQL, or CLS
actually strips columns, a ``DataAuditLog`` entry is written via ``AuditService``
— never on a no-op pass.
"""

from __future__ import annotations

import copy
import json

import pytest

from backend.app.auth.models import Role
from backend.app.query.sql_visibility import (
    apply_sql_visibility_gate,
    gate_sse_event,
    resolve_effective_sql_visibility,
)

# ── (a) effective-visibility resolution ──────────────────────────────────────


def test_override_true_beats_viewer_role():
    # A viewer normally cannot see SQL, but an explicit True override wins.
    assert resolve_effective_sql_visibility(Role.VIEWER, sql_visibility=True) is True


def test_override_false_beats_admin_role():
    # An admin normally CAN see SQL, but an explicit False override wins.
    assert resolve_effective_sql_visibility(Role.ADMIN, sql_visibility=False) is False


def test_null_override_inherits_admin_role_default_true():
    # NULL override → inherit the role default. Admin → True.
    assert resolve_effective_sql_visibility(Role.ADMIN, sql_visibility=None) is True


def test_null_override_inherits_analyst_role_default_true():
    assert resolve_effective_sql_visibility(Role.ANALYST, sql_visibility=None) is True


def test_null_override_inherits_viewer_role_default_false():
    # NULL override → inherit the role default. Viewer → False.
    assert resolve_effective_sql_visibility(Role.VIEWER, sql_visibility=None) is False


def test_null_override_inherits_team_lead_role_default_false():
    # team_lead is NOT an SQL-viewing role by default.
    assert resolve_effective_sql_visibility(Role.TEAM_LEAD, sql_visibility=None) is False


def test_none_role_with_null_override_is_false():
    # Defensive: no role + no override → deny by default.
    assert resolve_effective_sql_visibility(None, sql_visibility=None) is False


# ── (b) response gate: omit SQL + raw rows, keep chart + insight ─────────────


def test_gate_visible_passes_sql_event_unchanged():
    event = {"event": "sql", "data": {"sql": "SELECT 1", "explanation": "ok"}}
    out = apply_sql_visibility_gate(event, sql_visible=True)
    assert out == event


def test_gate_not_visible_drops_sql_event():
    event = {"event": "sql", "data": {"sql": "SELECT 1", "explanation": "ok"}}
    out = apply_sql_visibility_gate(event, sql_visible=False)
    assert out is None  # the sql event is omitted entirely


def test_gate_not_visible_strips_sql_from_status_event():
    # The SQL_READY status event embeds the raw SQL string — strip it but keep
    # the rest of the status payload.
    event = {
        "event": "status",
        "data": {"status": "sql_ready", "message": "SQL generated", "sql": "SELECT 1"},
    }
    out = apply_sql_visibility_gate(event, sql_visible=False)
    assert out is not None
    assert "sql" not in out["data"]
    assert out["data"]["status"] == "sql_ready"
    assert out["data"]["message"] == "SQL generated"


def test_gate_visible_keeps_sql_in_status_event():
    event = {
        "event": "status",
        "data": {"status": "sql_ready", "message": "SQL generated", "sql": "SELECT 1"},
    }
    out = apply_sql_visibility_gate(event, sql_visible=True)
    assert out["data"]["sql"] == "SELECT 1"


def test_gate_not_visible_keeps_chart_visualisation():
    # A genuine chart visualisation (bar/line/pie) is kept even when SQL is hidden.
    chart_data = [{"region": "KW", "revenue": 100}, {"region": "AE", "revenue": 50}]
    event = {
        "event": "chart",
        "data": {
            "chart_type": "bar",
            "chart_data": chart_data,
            "chart_config": {"type": "bar"},
            "row_count": 2,
        },
    }
    out = apply_sql_visibility_gate(event, sql_visible=False)
    assert out is not None
    assert out["data"]["chart_data"] == chart_data  # visualisation kept
    assert out["data"]["chart_type"] == "bar"


def test_gate_not_visible_drops_raw_table_grid():
    # When the "chart" degrades to a raw data table, that IS the row-level
    # tabular data — drop chart_data so the user cannot read the raw rows.
    rows = [{"id": 1, "secret": "x"}, {"id": 2, "secret": "y"}]
    event = {
        "event": "chart",
        "data": {
            "chart_type": "table",
            "chart_data": rows,
            "chart_config": {"type": "table"},
            "row_count": 2,
        },
    }
    out = apply_sql_visibility_gate(event, sql_visible=False)
    assert out is not None
    assert out["data"]["chart_data"] == []  # raw grid stripped
    assert out["data"]["row_count"] == 2  # count metadata preserved


def test_gate_visible_keeps_raw_table_grid():
    rows = [{"id": 1, "secret": "x"}]
    event = {
        "event": "chart",
        "data": {"chart_type": "table", "chart_data": rows, "chart_config": {"type": "table"}},
    }
    out = apply_sql_visibility_gate(event, sql_visible=True)
    assert out["data"]["chart_data"] == rows


def test_gate_not_visible_keeps_insight_event():
    event = {
        "event": "insight",
        "data": {"summary": "Revenue grew", "suggestions": ["Drill into KW"]},
    }
    out = apply_sql_visibility_gate(event, sql_visible=False)
    assert out == event  # insight always passes through


def test_gate_passes_through_other_events():
    for ev in ("done", "error"):
        event = {"event": ev, "data": {"foo": "bar"}}
        assert apply_sql_visibility_gate(event, sql_visible=False) == event


def test_gate_does_not_mutate_input_event():
    event = {
        "event": "chart",
        "data": {"chart_type": "table", "chart_data": [{"a": 1}], "row_count": 1},
    }
    snapshot = copy.deepcopy(event)
    apply_sql_visibility_gate(event, sql_visible=False)
    assert event == snapshot  # immutability: input untouched


# ── (b2) SSE-shaped gate: data is a JSON string on the wire ──────────────────


def test_sse_gate_drops_sql_event_with_string_data():
    event = {"event": "sql", "data": json.dumps({"sql": "SELECT 1", "explanation": "ok"})}
    assert gate_sse_event(event, sql_visible=False) is None


def test_sse_gate_strips_sql_from_status_string_data():
    event = {
        "event": "status",
        "data": json.dumps({"status": "sql_ready", "message": "SQL generated", "sql": "SELECT 1"}),
    }
    out = gate_sse_event(event, sql_visible=False)
    payload = json.loads(out["data"])
    assert "sql" not in payload
    assert payload["status"] == "sql_ready"


def test_sse_gate_blanks_table_grid_string_data():
    event = {
        "event": "chart",
        "data": json.dumps(
            {"chart_type": "table", "chart_data": [{"a": 1}], "row_count": 1}
        ),
    }
    out = gate_sse_event(event, sql_visible=False)
    payload = json.loads(out["data"])
    assert payload["chart_data"] == []
    assert payload["row_count"] == 1


def test_sse_gate_keeps_chart_visualisation_string_data():
    event = {
        "event": "chart",
        "data": json.dumps(
            {"chart_type": "bar", "chart_data": [{"x": 1, "y": 2}], "row_count": 1}
        ),
    }
    out = gate_sse_event(event, sql_visible=False)
    payload = json.loads(out["data"])
    assert payload["chart_data"] == [{"x": 1, "y": 2}]


def test_sse_gate_passes_through_when_visible():
    event = {"event": "sql", "data": json.dumps({"sql": "SELECT 1"})}
    assert gate_sse_event(event, sql_visible=True) == event


# ── (c) governance audit: RLS apply + CLS deny write a DataAuditLog ──────────


class _FakeAuditService:
    """Captures log_event calls instead of touching the DB."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    async def log_event(self, **kwargs) -> None:
        self.events.append(kwargs)


@pytest.mark.asyncio
async def test_audit_rls_filter_records_tables_and_filters():
    from backend.app.query.sql_visibility import audit_rls_applied
    from backend.app.services.audit import AuditAction

    fake = _FakeAuditService()
    row_filters = {"FCT_SALES": "REGION = 'KW'"}

    await audit_rls_applied(
        fake,
        customer_id="cust-uuid",
        user_id="user-uuid",
        row_filters=row_filters,
    )

    assert len(fake.events) == 1
    ev = fake.events[0]
    assert ev["action"] == AuditAction.RLS_FILTER
    assert ev["customer_id"] == "cust-uuid"
    assert ev["user_id"] == "user-uuid"
    assert ev["details"]["tables"] == ["FCT_SALES"]
    assert ev["details"]["filters"] == row_filters


@pytest.mark.asyncio
async def test_audit_cls_denied_records_table_and_columns():
    from backend.app.query.sql_visibility import audit_cls_denied
    from backend.app.services.audit import AuditAction

    fake = _FakeAuditService()
    deny = {"DIM_PREP_PRODUCTS": ["PRODUCT_TYPE", "COST"]}

    await audit_cls_denied(
        fake,
        customer_id="cust-uuid",
        user_id="user-uuid",
        deny_columns=deny,
    )

    assert len(fake.events) == 1
    ev = fake.events[0]
    assert ev["action"] == AuditAction.CLS_DENIED
    # one entry per table that has a non-empty deny-list
    assert ev["details"]["table"] == "DIM_PREP_PRODUCTS"
    assert ev["details"]["columns"] == ["PRODUCT_TYPE", "COST"]


@pytest.mark.asyncio
async def test_audit_rls_noop_writes_nothing():
    # No row filters → nothing was restricted → no audit entry.
    from backend.app.query.sql_visibility import audit_rls_applied

    fake = _FakeAuditService()
    await audit_rls_applied(fake, customer_id="c", user_id="u", row_filters=None)
    await audit_rls_applied(fake, customer_id="c", user_id="u", row_filters={})
    assert fake.events == []


@pytest.mark.asyncio
async def test_audit_cls_noop_writes_nothing():
    from backend.app.query.sql_visibility import audit_cls_denied

    fake = _FakeAuditService()
    await audit_cls_denied(fake, customer_id="c", user_id="u", deny_columns=None)
    await audit_cls_denied(fake, customer_id="c", user_id="u", deny_columns={})
    # an entry whose column list is empty is still a no-op
    await audit_cls_denied(fake, customer_id="c", user_id="u", deny_columns={"T": []})
    assert fake.events == []


@pytest.mark.asyncio
async def test_audit_failure_does_not_raise():
    # A failing audit backend must NOT break the query path.
    from backend.app.query.sql_visibility import audit_rls_applied

    class _Boom:
        async def log_event(self, **kwargs):
            raise RuntimeError("db down")

    # Should swallow the exception and return without raising.
    await audit_rls_applied(
        _Boom(), customer_id="c", user_id="u", row_filters={"T": "x = 1"}
    )


# ── (d) DB-backed effective visibility: _resolve_sql_visible ─────────────────
#
# `_resolve_sql_visible` reads the per-user `users.sql_visibility` override from
# the metadata DB and layers it over the role default. The security-critical
# property is fail-CLOSED: any error reading the override resolves to False
# (hide SQL) so a user explicitly set sql_visibility=False cannot silently
# become visible again on a transient DB error.


class _FakeResult:
    """Stands in for the object returned by ``conn.execute(...)``."""

    def __init__(self, row: tuple | None) -> None:
        self._row = row

    def fetchone(self) -> tuple | None:
        return self._row


class _FakeConn:
    """Async context-manager connection whose ``execute`` returns a fixed row."""

    def __init__(self, row: tuple | None) -> None:
        self._row = row

    async def __aenter__(self) -> _FakeConn:
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def execute(self, *args, **kwargs) -> _FakeResult:
        return _FakeResult(self._row)


class _FakeEngine:
    """Async engine whose ``connect()`` yields a connection with a fixed row."""

    def __init__(self, row: tuple | None) -> None:
        self._row = row

    def connect(self) -> _FakeConn:
        return _FakeConn(self._row)


class _BoomConn:
    async def __aenter__(self) -> _BoomConn:
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def execute(self, *args, **kwargs):
        raise RuntimeError("db down")


class _BoomEngine:
    """Async engine whose connection raises on ``execute`` — simulates a DB error."""

    def connect(self) -> _BoomConn:
        return _BoomConn()


def _user(role: Role | None, user_id: str | None = "user-001"):
    from backend.app.auth.models import UserContext

    return UserContext(user_id=user_id, role=role, workspace_id="ws-1")


@pytest.mark.asyncio
async def test_resolve_sql_visible_override_true_beats_role_default():
    # Override True wins even for a role (viewer) whose default is False.
    from backend.app.api.query import _resolve_sql_visible

    engine = _FakeEngine(row=(True,))
    assert await _resolve_sql_visible(engine, _user(Role.VIEWER)) is True


@pytest.mark.asyncio
async def test_resolve_sql_visible_override_false_beats_admin_role():
    # Override False wins even for admin (whose default is True).
    from backend.app.api.query import _resolve_sql_visible

    engine = _FakeEngine(row=(False,))
    assert await _resolve_sql_visible(engine, _user(Role.ADMIN)) is False


@pytest.mark.asyncio
async def test_resolve_sql_visible_null_override_inherits_role_default():
    # NULL override → role default. Admin → True, Viewer → False.
    from backend.app.api.query import _resolve_sql_visible

    engine_admin = _FakeEngine(row=(None,))
    assert await _resolve_sql_visible(engine_admin, _user(Role.ADMIN)) is True

    engine_viewer = _FakeEngine(row=(None,))
    assert await _resolve_sql_visible(engine_viewer, _user(Role.VIEWER)) is False


@pytest.mark.asyncio
async def test_resolve_sql_visible_no_row_inherits_role_default():
    # No matching user row → no override → role default.
    from backend.app.api.query import _resolve_sql_visible

    engine = _FakeEngine(row=None)
    assert await _resolve_sql_visible(engine, _user(Role.ANALYST)) is True


@pytest.mark.asyncio
async def test_resolve_sql_visible_fails_closed_on_db_error():
    # SECURITY: a DB error reading the override must resolve to False (deny),
    # even for an admin whose role default would otherwise be True.
    from backend.app.api.query import _resolve_sql_visible

    assert await _resolve_sql_visible(_BoomEngine(), _user(Role.ADMIN)) is False


@pytest.mark.asyncio
async def test_resolve_sql_visible_no_user_id_uses_role_default():
    # No user_id → skip the DB read entirely, fall back to role default.
    from backend.app.api.query import _resolve_sql_visible

    # engine.connect must NOT be called; pass an engine that would explode if it were.
    assert await _resolve_sql_visible(_BoomEngine(), _user(Role.ADMIN, user_id=None)) is True
    assert await _resolve_sql_visible(_BoomEngine(), _user(Role.VIEWER, user_id=None)) is False


# ── (e) async require_sql_access: DB override + fail-closed ──────────────────


class _FakeSession:
    def __init__(self, row: tuple | None) -> None:
        self._row = row

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def execute(self, *args, **kwargs) -> _FakeResult:
        return _FakeResult(self._row)


class _BoomSession:
    async def __aenter__(self) -> _BoomSession:
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def execute(self, *args, **kwargs):
        raise RuntimeError("db down")


def _sessionmaker_returning(session):
    def _maker():
        return session

    return _maker


def _patch_sessionmaker(monkeypatch, session):
    # require_sql_access does `from backend.app.db.session import get_sessionmaker`
    # INSIDE the function body, so the name must be patched on its source module,
    # not on the rbac module namespace.
    import backend.app.db.session as session_mod

    monkeypatch.setattr(
        session_mod, "get_sessionmaker", lambda: _sessionmaker_returning(session)
    )


@pytest.mark.asyncio
async def test_require_sql_access_override_true_grants_for_viewer(monkeypatch):
    from backend.app.auth import rbac

    _patch_sessionmaker(monkeypatch, _FakeSession((True,)))
    # Override True grants access even though viewer's role default is False.
    await rbac.require_sql_access(_user(Role.VIEWER))  # must not raise


@pytest.mark.asyncio
async def test_require_sql_access_override_false_denies_admin(monkeypatch):
    from fastapi import HTTPException

    from backend.app.auth import rbac

    _patch_sessionmaker(monkeypatch, _FakeSession((False,)))
    with pytest.raises(HTTPException) as exc:
        await rbac.require_sql_access(_user(Role.ADMIN))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_sql_access_null_override_inherits_role_default(monkeypatch):
    from fastapi import HTTPException

    from backend.app.auth import rbac

    # Admin default True → allowed.
    _patch_sessionmaker(monkeypatch, _FakeSession((None,)))
    await rbac.require_sql_access(_user(Role.ADMIN))
    # Viewer default False → denied.
    _patch_sessionmaker(monkeypatch, _FakeSession((None,)))
    with pytest.raises(HTTPException) as exc:
        await rbac.require_sql_access(_user(Role.VIEWER))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_sql_access_fails_closed_on_db_error(monkeypatch):
    # SECURITY: a DB error reading the override must DENY (403), even for admin.
    from fastapi import HTTPException

    from backend.app.auth import rbac

    _patch_sessionmaker(monkeypatch, _BoomSession())
    with pytest.raises(HTTPException) as exc:
        await rbac.require_sql_access(_user(Role.ADMIN))
    assert exc.value.status_code == 403


# ── (f) admin PATCH persists sql_visibility (model_fields_set semantics) ──────
#
# The admin update_user handler must only touch `user.sql_visibility` when the
# field is explicitly present in the request body. Omitting it leaves the
# existing value untouched; passing null resets to "inherit role default".


def _make_user(sql_visibility):
    import uuid as _uuid
    from datetime import UTC, datetime

    from backend.app.models.organization import User
    from backend.app.schemas.organization import UserRole

    now = datetime.now(UTC)
    return User(
        id=_uuid.uuid4(),
        customer_id=_uuid.uuid4(),
        external_id="kc-ext-id",
        email="u@b2metric.com",
        display_name="U",
        role=UserRole.ANALYST,
        team_id=None,
        is_active=True,
        sql_visibility=sql_visibility,
        created_at=now,
        updated_at=now,
    )


class _PatchSession:
    """Async session that returns a fixed user and records commit/refresh."""

    def __init__(self, user) -> None:
        self._user = user
        self.committed = False

    async def execute(self, *args, **kwargs):
        from unittest.mock import MagicMock

        result = MagicMock()
        result.scalar_one_or_none.return_value = self._user
        return result

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, _obj) -> None:
        return None


async def _run_update(body, existing_user, monkeypatch):
    """Drive the admin update_user handler with a mocked session + Keycloak."""
    import uuid as _uuid
    from unittest.mock import AsyncMock

    from backend.app.api.endpoints.admin import users as users_ep

    monkeypatch.setattr(
        users_ep, "resolve_customer_id", AsyncMock(return_value=existing_user.customer_id)
    )

    class _FakeKC:
        async def update_user(self, *args, **kwargs):
            return None

    monkeypatch.setattr(users_ep, "KeycloakAdminService", _FakeKC)

    session = _PatchSession(existing_user)
    admin_user = _user(Role.ADMIN)
    # The handler checks current_user.can_admin.
    admin_user.can_admin = True

    resp = await users_ep.update_user(
        user_id=_uuid.uuid4(),
        body=body,
        current_user=admin_user,
        db=session,
    )
    return resp, session


@pytest.mark.asyncio
async def test_admin_patch_sets_sql_visibility_false(monkeypatch):
    from backend.app.schemas.organization import UserUpdate

    existing = _make_user(sql_visibility=None)  # currently inherits role default
    body = UserUpdate(sql_visibility=False)  # explicitly present → must persist
    assert "sql_visibility" in body.model_fields_set

    resp, session = await _run_update(body, existing, monkeypatch)

    assert existing.sql_visibility is False
    assert resp.sql_visibility is False
    assert session.committed is True


@pytest.mark.asyncio
async def test_admin_patch_sets_sql_visibility_true(monkeypatch):
    from backend.app.schemas.organization import UserUpdate

    existing = _make_user(sql_visibility=None)
    body = UserUpdate(sql_visibility=True)

    resp, _ = await _run_update(body, existing, monkeypatch)

    assert existing.sql_visibility is True
    assert resp.sql_visibility is True


@pytest.mark.asyncio
async def test_admin_patch_omitting_sql_visibility_leaves_value_untouched(monkeypatch):
    # Only role is set; sql_visibility omitted from the body → existing value
    # (True) must be preserved (model_fields_set excludes sql_visibility).
    from backend.app.schemas.organization import UserRole, UserUpdate

    existing = _make_user(sql_visibility=True)
    body = UserUpdate(role=UserRole.VIEWER)
    assert "sql_visibility" not in body.model_fields_set

    resp, _ = await _run_update(body, existing, monkeypatch)

    assert existing.sql_visibility is True  # untouched
    assert resp.sql_visibility is True


@pytest.mark.asyncio
async def test_admin_patch_explicit_null_resets_to_inherit(monkeypatch):
    # Explicit null → reset override to "inherit role default" (None persisted).
    from backend.app.schemas.organization import UserUpdate

    existing = _make_user(sql_visibility=True)
    body = UserUpdate(sql_visibility=None)
    assert "sql_visibility" in body.model_fields_set

    resp, _ = await _run_update(body, existing, monkeypatch)

    assert existing.sql_visibility is None
    assert resp.sql_visibility is None
