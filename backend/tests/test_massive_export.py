"""TIER 1 item 5 — large-result export routing.

Phase 3: the chat path no longer calls the in-RAM worker
(``export_massive_query_to_minio``) directly — that module is now dead from the
chat path (Phase 4 cleanup will remove it). Instead, the export band in
``pipeline._execute_sql`` creates a durable ``ExportJob`` row, dispatches the
streaming Prefect flow, and raises ``ExportDispatched`` — which
``process_query`` catches and turns into a clean ``export`` SSE event. The
worker-failure path is now owned by the flow (covered by test_export_flow.py).
"""

from __future__ import annotations

import uuid as _uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Pipeline routing branch (_execute_sql) ─────────────────────────────────
# The DECISION to display-vs-export lives in pipeline._execute_sql. Phase 2
# routes on the TRUE size: EXPLAIN runs on the un-limited SQL and the result is
# offloaded to an async export when the estimate exceeds the tenant's
# max_row_limit, or when the display read overflows max_row_limit + 1 (EXPLAIN
# under-estimate). A huge estimate is NOT blocked outright — it routes to the
# export band.
from backend.app.db import DatabaseType, DBConfig  # noqa: E402
from backend.app.query.export_dispatch import ExportDispatched


def _pg_config(max_row_limit: int = 1000) -> DBConfig:
    return DBConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="db",
        port=5432,
        database="warehouse",
        username="u",
        password="p",
        max_row_limit=max_row_limit,
    )


def _mock_db() -> AsyncMock:
    """An AsyncMock session whose customer-UUID lookup returns no row, so
    ``_execute_sql`` leaves ``_customer_uuid`` None and ``_audit`` short-circuits
    — keeping these routing tests off the audit path (and warning-free)."""
    db = AsyncMock()
    db.execute.return_value.fetchone.return_value = None
    return db


async def _run_routed(estimated_rows: int, rows_returned: list | None = None, job_id=None):
    """Drive _execute_sql past routing. EXPLAIN returns `estimated_rows` for the
    BARE sql; create/dispatch are mocked so the export band raises ExportDispatched."""
    from backend.app.query import pipeline

    if rows_returned is None:
        rows_returned = [{"x": 1}]
    job_id = job_id or _uuid.uuid4()
    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_pg_config())),
        patch.object(pipeline, "_resolve_vault_policy", new=AsyncMock(return_value=None)),
        patch("backend.app.db.explain_query", new=AsyncMock(return_value={"estimated_rows": estimated_rows})),
        patch("backend.app.db.execute_query", new=AsyncMock(return_value=rows_returned)),
        patch.object(pipeline, "create_export_job", new=AsyncMock(return_value=job_id)),
        patch.object(pipeline, "dispatch_export_job", new=AsyncMock(return_value=None)),
    ):
        return await pipeline._execute_sql(
            sql="SELECT * FROM orders", engine=MagicMock(), workspace_id="ws1",
            db=_mock_db(), user_id="u1", question="show all orders",
        )


class _AsyncCM:
    """Minimal async context manager wrapping a plain object (for engine.connect())."""

    def __init__(self, obj):
        self._obj = obj

    async def __aenter__(self):
        return self._obj

    async def __aexit__(self, *_args):
        return False


def test_tenant_db_config_columns_are_wired_into_get_db_config():
    """MECHANICAL GATE (model-independent, CI-blocking): every customer_db_configs
    column that has a same-named DBConfig field MUST be referenced by _get_db_config.

    Auto-derived — no hardcoded field list — so when a NEW tenant field is added to
    both the table and DBConfig, this fails until the loader's SELECT + DBConfig(...)
    actually read it. Guards the "set 100005 but export truncated at 100000" bug
    class, where a tenant value silently falls back to the DBConfig dataclass default
    because the loader forgot to map the column."""
    import dataclasses
    import inspect
    import re

    from backend.app.models.database import CustomerDBConfig
    from backend.app.query import pipeline

    column_names = {c.name for c in CustomerDBConfig.__table__.columns}
    dbconfig_fields = {f.name for f in dataclasses.fields(DBConfig)}
    tenant_fields = column_names & dbconfig_fields  # same-named ⇒ sourced from the tenant row

    # sanity: the fields this gate exists to protect must be in the derived set
    assert {"max_export_row_limit", "export_batch_size", "export_link_ttl_days"} <= tenant_fields

    src = inspect.getsource(pipeline._get_db_config)
    missing = [f for f in sorted(tenant_fields) if not re.search(rf"\b{re.escape(f)}\b", src)]
    assert not missing, (
        f"_get_db_config does not reference tenant DBConfig field(s) {missing}; their "
        "tenant values will silently fall back to the DBConfig dataclass default. Add "
        "the column(s) to the SELECT and the DBConfig(...) constructor in _get_db_config."
    )


@pytest.mark.asyncio
async def test_get_db_config_maps_tenant_export_columns():
    """REGRESSION: _get_db_config must read max_export_row_limit / export_batch_size /
    export_link_ttl_days from customer_db_configs — not silently fall back to the
    DBConfig dataclass defaults. Root cause of "set 100005 but export truncated at
    100000": the loader SELECT omitted these columns."""
    from backend.app.query import pipeline

    result = MagicMock()
    result.fetchone.return_value = (
        _uuid.uuid4(),  # customer_id
        "postgresql",   # db_type
        "db",           # host
        5432,           # port
        "warehouse",    # database
        "u",            # username
        "enc",          # encrypted_password
        1000,           # max_row_limit
        100005,         # max_export_row_limit
        50000,          # export_batch_size
        7,              # export_link_ttl_days
    )
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=result)
    engine = MagicMock()
    engine.connect.return_value = _AsyncCM(conn)

    with patch(
        "backend.app.services.crypto.async_decrypt_password",
        new=AsyncMock(return_value="pw"),
    ):
        cfg = await pipeline._get_db_config(engine, "stc-kuwait")

    assert cfg.max_row_limit == 1000
    assert cfg.max_export_row_limit == 100005
    assert cfg.export_batch_size == 50000
    assert cfg.export_link_ttl_days == 7


@pytest.mark.asyncio
async def test_estimate_within_display_limit_returns_rows_inline():
    """R̂ ≤ max_row_limit (1000) -> display path returns rows, no export job."""
    from backend.app.query import pipeline

    create = AsyncMock()
    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_pg_config())),
        patch.object(pipeline, "_resolve_vault_policy", new=AsyncMock(return_value=None)),
        patch("backend.app.db.explain_query", new=AsyncMock(return_value={"estimated_rows": 50})),
        patch("backend.app.db.execute_query", new=AsyncMock(return_value=[{"x": 1}, {"x": 2}])),
        patch.object(pipeline, "create_export_job", new=create),
    ):
        out = await pipeline._execute_sql(
            sql="SELECT * FROM orders", engine=MagicMock(), workspace_id="ws1",
            db=_mock_db(), user_id="u1", question="q",
        )
    assert out == [{"x": 1}, {"x": 2}]
    create.assert_not_called()


@pytest.mark.asyncio
async def test_estimate_above_display_limit_dispatches_export():
    """R̂ > max_row_limit -> export band raises ExportDispatched with the estimate."""
    jid = _uuid.uuid4()
    with pytest.raises(ExportDispatched) as exc:
        await _run_routed(estimated_rows=50_000, job_id=jid)
    assert exc.value.job_id == jid
    assert exc.value.estimated_rows == 50_000


@pytest.mark.asyncio
async def test_huge_estimate_dispatches_instead_of_blocking():
    """Phase 2 removed the >100x hard block; a huge estimate routes to export."""
    with pytest.raises(ExportDispatched):
        await _run_routed(estimated_rows=5_000_000)


@pytest.mark.asyncio
async def test_inline_safety_cap_dispatches_when_read_overflows():
    """EXPLAIN underestimates (≤ max_row_limit) but the read returns max_row_limit+1
    rows -> switch to export band."""
    over = [{"x": i} for i in range(1001)]  # max_row_limit(1000) + 1
    with pytest.raises(ExportDispatched):
        await _run_routed(estimated_rows=200, rows_returned=over)
