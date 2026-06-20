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
