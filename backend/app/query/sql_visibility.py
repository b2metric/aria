"""Per-user SQL-visibility resolution + governance audit helpers.

ARIA's SQL-visibility invariant: only users whose *effective* visibility is
``True`` may see the raw generated SQL string and the raw row-level tabular
result.  Effective visibility is computed as:

    user override (``sql_visibility``)  if it is not NULL
    else  the role default              (``_can_view_sql(role)`` → admin/analyst)

A user who cannot see SQL still gets the **chart visualisation** and the
**insight/summary** — only the raw SQL text and the raw tabular grid are hidden.

This module is deliberately pure (no DB, no I/O) for the visibility logic, and
exposes two small async helpers that write governance ``DataAuditLog`` entries
through an :class:`~backend.app.services.audit.AuditService` whenever Row-Level
Security actually rewrote the SQL or Column-Level Security actually stripped
columns.  Audit failures never propagate — governance logging must not break a
query.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from backend.app.auth.dependencies import _can_view_sql
from backend.app.auth.models import Role
from backend.app.services.audit import AuditAction, AuditResourceType

logger = logging.getLogger("aria.query.sql_visibility")


# ── Effective visibility ─────────────────────────────────────────────────────


def resolve_effective_sql_visibility(role: Role | None, sql_visibility: bool | None) -> bool:
    """Return whether the user may see the raw SQL + raw tabular rows.

    Args:
        role: The user's role (may be ``None`` — defensive deny-by-default).
        sql_visibility: The per-user override.  ``None`` inherits the role
            default; ``True``/``False`` is an explicit override that wins.

    Returns:
        ``True`` if SQL is visible to this user, else ``False``.
    """
    if sql_visibility is not None:
        return sql_visibility
    if role is None:
        return False
    return _can_view_sql(role)


# ── SSE response gate ────────────────────────────────────────────────────────


def apply_sql_visibility_gate(event: dict[str, Any], sql_visible: bool) -> dict[str, Any] | None:
    """Filter a single SSE event for a user who may not see raw SQL.

    When *sql_visible* is ``True`` the event passes through unchanged.

    When *sql_visible* is ``False``:
      * ``"sql"`` events are omitted entirely (return ``None``);
      * the raw ``sql`` string is stripped from a ``"status"`` event payload;
      * a ``"chart"`` event that degraded to a raw data table
        (``chart_type == "table"``) has its ``chart_data`` blanked — that grid
        IS the row-level tabular data — while a genuine chart visualisation
        (bar/line/pie/…) keeps its ``chart_data``;
      * all other events (``insight``, ``done``, ``error``, …) pass through.

    The input event is never mutated; a new dict is returned when a change is
    needed.
    """
    if sql_visible:
        return event

    kind = event.get("event")

    if kind == "sql":
        return None

    if kind == "status":
        data = event.get("data")
        if isinstance(data, dict) and "sql" in data:
            new_data = {k: v for k, v in data.items() if k != "sql"}
            return {**event, "data": new_data}
        return event

    if kind == "chart":
        data = event.get("data")
        if isinstance(data, dict) and data.get("chart_type") == "table":
            # Raw tabular grid == the row-level data; strip it but keep metadata.
            return {**event, "data": {**data, "chart_data": []}}
        return event

    return event


def gate_sse_event(event: dict[str, Any], sql_visible: bool) -> dict[str, Any] | None:
    """SSE-shaped wrapper around :func:`apply_sql_visibility_gate`.

    Real pipeline events carry their payload as a JSON *string* under ``data``
    (it has already been ``json.dumps``'d for the wire).  This wrapper parses
    that string into a dict, applies the gate, and re-serialises — so the pure
    dict-based gate stays simple and fully unit-tested.  Non-JSON / non-dict
    payloads pass through the dict gate unchanged.
    """
    if sql_visible:
        return event

    data = event.get("data")
    parsed: Any = data
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
        except (ValueError, TypeError):
            parsed = data

    gated = apply_sql_visibility_gate({**event, "data": parsed}, sql_visible=False)
    if gated is None:
        return None
    # Re-serialise only if we parsed a JSON string in the first place.
    if isinstance(data, str) and isinstance(gated.get("data"), (dict, list)):
        return {**gated, "data": json.dumps(gated["data"], default=str)}
    return gated


# ── Governance audit helpers ─────────────────────────────────────────────────


class _AuditLike(Protocol):
    """Minimal interface needed to write a governance audit entry."""

    async def log_event(self, **kwargs: Any) -> Any: ...


async def audit_rls_applied(
    audit: _AuditLike,
    *,
    customer_id: Any,
    user_id: Any,
    row_filters: dict[str, str] | None,
) -> None:
    """Record that Row-Level Security actually rewrote the SQL.

    Only writes when *row_filters* is non-empty (an empty/None map is a no-op
    pass and must not be logged).  Never raises — audit failures are swallowed.
    """
    if not row_filters:
        return
    try:
        await audit.log_event(
            customer_id=customer_id,
            user_id=user_id,
            action=AuditAction.RLS_FILTER,
            resource_type=AuditResourceType.POLICY,
            details={"tables": sorted(row_filters.keys()), "filters": dict(row_filters)},
        )
    except Exception:
        logger.exception("Failed to write RLS-filter audit log")


async def audit_cls_denied(
    audit: _AuditLike,
    *,
    customer_id: Any,
    user_id: Any,
    deny_columns: dict[str, list[str]] | None,
) -> None:
    """Record that Column-Level Security actually stripped columns.

    Writes one entry per table that has a non-empty deny-list.  An empty/None
    map (or a table whose column list is empty) is a no-op pass and is not
    logged.  Never raises — audit failures are swallowed.
    """
    if not deny_columns:
        return
    try:
        for table, columns in deny_columns.items():
            if not columns:
                continue
            await audit.log_event(
                customer_id=customer_id,
                user_id=user_id,
                action=AuditAction.CLS_DENIED,
                resource_type=AuditResourceType.POLICY,
                details={"table": table, "columns": list(columns)},
            )
    except Exception:
        logger.exception("Failed to write CLS-denied audit log")
