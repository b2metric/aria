"""TIER 1 item 5 — large-result export delivers a download URL.

The pipeline now awaits ``export_massive_query_to_minio`` and surfaces its URL to
the user (previously fire-and-forget discarded it). These tests pin the worker's
contract: it dumps the full result to CSV in MinIO and returns a download URL.
"""

from __future__ import annotations

import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _fake_store(ref_url="http://minio/aria-artifacts/exports/x.csv"):
    ref = types.SimpleNamespace(
        public_url=lambda: ref_url,
        presigned_url=lambda expires=0: "http://minio/presigned",
    )
    store = MagicMock()
    store.upload_csv.return_value = ref
    return MagicMock(return_value=store), store


@pytest.mark.asyncio
async def test_export_returns_download_url():
    from backend.app.worker import tasks

    rows = [{"id": 1, "amt": 10}, {"id": 2, "amt": 20}]
    store_cls, store = _fake_store()
    with (
        patch.object(tasks, "execute_query_sync", return_value=rows),
        patch("agents.artifact_store.ArtifactStore", store_cls),
    ):
        res = await tasks.export_massive_query_to_minio(
            sql="SELECT 1", db_config=MagicMock(), conversation_id="c1", workspace_id="ws1"
        )
    assert res["status"] == "success"
    assert res["url"]  # the URL the pipeline now delivers to the user
    assert res["row_count"] == 2
    # The full (un-truncated) dataset was written.
    store.upload_csv.assert_called_once()


@pytest.mark.asyncio
async def test_export_zero_rows_returns_no_url():
    from backend.app.worker import tasks

    with patch.object(tasks, "execute_query_sync", return_value=[]):
        res = await tasks.export_massive_query_to_minio(
            sql="SELECT 1", db_config=MagicMock(), conversation_id="c1", workspace_id="ws1"
        )
    assert res["status"] == "success"
    assert res["row_count"] == 0
    assert res["url"] is None


@pytest.mark.asyncio
async def test_export_failure_is_reported_not_swallowed():
    from backend.app.worker import tasks

    with patch.object(tasks, "execute_query_sync", side_effect=RuntimeError("db down")):
        res = await tasks.export_massive_query_to_minio(
            sql="SELECT 1", db_config=MagicMock(), conversation_id="c1", workspace_id="ws1"
        )
    assert res["status"] == "error"  # pipeline turns this into a "export failed, narrow query"


# ── Pipeline routing branch (_execute_sql) ─────────────────────────────────
# The DECISION to display-vs-export lives in pipeline._execute_sql. Phase 2
# routes on the TRUE size: EXPLAIN runs on the un-limited SQL and the result is
# offloaded to a CSV export when the estimate exceeds the tenant's max_row_limit,
# or when the display read overflows max_row_limit + 1 (EXPLAIN under-estimate).
# A huge estimate is NO LONGER blocked outright — it routes to the export band.

from backend.app.db import DatabaseType, DBConfig  # noqa: E402


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


async def _run_routed(estimated_rows: int, export_result: dict | None, rows_returned: list | None = None):
    """Drive _execute_sql past routing. EXPLAIN returns `estimated_rows` for the
    BARE sql; the display path's execute_query returns `rows_returned` (default a
    small list so the display branch returns normally)."""
    from backend.app.query import pipeline

    if rows_returned is None:
        rows_returned = [{"x": 1}]

    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_pg_config())),
        patch("backend.app.db.explain_query", new=AsyncMock(return_value={"estimated_rows": estimated_rows})),
        patch("backend.app.db.execute_query", new=AsyncMock(return_value=rows_returned)),
        patch("backend.app.worker.tasks.export_massive_query_to_minio", new=AsyncMock(return_value=export_result)),
    ):
        return await pipeline._execute_sql(
            sql="SELECT * FROM orders",
            engine=MagicMock(),
            workspace_id="ws1",
            db=None,
            user_id="u1",
            question="show all orders",
        )


@pytest.mark.asyncio
async def test_estimate_within_display_limit_returns_rows_inline():
    """R̂ ≤ max_row_limit (1000) → display path returns rows, no export."""
    export = AsyncMock()
    from backend.app.query import pipeline

    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_pg_config())),
        patch("backend.app.db.explain_query", new=AsyncMock(return_value={"estimated_rows": 50})),
        patch("backend.app.db.execute_query", new=AsyncMock(return_value=[{"x": 1}, {"x": 2}])),
        patch("backend.app.worker.tasks.export_massive_query_to_minio", new=export),
    ):
        out = await pipeline._execute_sql(
            sql="SELECT * FROM orders", engine=MagicMock(), workspace_id="ws1",
            db=None, user_id="u1", question="q",
        )
    assert out == [{"x": 1}, {"x": 2}]
    export.assert_not_called()


@pytest.mark.asyncio
async def test_estimate_above_display_limit_offloads_with_download_url():
    """R̂ > max_row_limit → export band; the download URL is surfaced."""
    export = {"status": "success", "url": "http://minio/exports/big.csv", "row_count": 50000}
    with pytest.raises(ValueError) as exc:
        await _run_routed(estimated_rows=50_000, export_result=export)
    msg = str(exc.value)
    assert export["url"] in msg
    assert "download" in msg.lower()


@pytest.mark.asyncio
async def test_offload_failure_asks_user_to_narrow_query():
    export = {"status": "error", "url": None, "error": "boom"}
    with pytest.raises(ValueError) as exc:
        await _run_routed(estimated_rows=50_000, export_result=export)
    assert "narrow the query" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_huge_estimate_offloads_instead_of_blocking():
    """Phase 2 removes the >100x hard block: a huge estimate now ROUTES TO EXPORT
    (bounded by max_export_row_limit downstream), it is NOT rejected outright."""
    export = {"status": "success", "url": "http://minio/exports/huge.csv", "row_count": 1_000_000}
    with pytest.raises(ValueError) as exc:
        await _run_routed(estimated_rows=5_000_000, export_result=export)
    m = str(exc.value).lower()
    assert "download" in m
    assert "security exception" not in m  # no longer blocked


@pytest.mark.asyncio
async def test_inline_safety_cap_offloads_when_read_overflows():
    """EXPLAIN underestimates (≤ max_row_limit) but the display read returns
    max_row_limit + 1 rows → switch to export band."""
    over = [{"x": i} for i in range(1001)]  # max_row_limit(1000) + 1
    export = {"status": "success", "url": "http://minio/exports/late.csv", "row_count": 1001}
    with pytest.raises(ValueError) as exc:
        await _run_routed(estimated_rows=200, export_result=export, rows_returned=over)
    assert "download" in str(exc.value).lower()
