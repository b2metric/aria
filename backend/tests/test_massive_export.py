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


# ── Pipeline offload branch (_execute_sql) ─────────────────────────────────
# The worker contract above is only half the feature. The DECISION to offload —
# "EXPLAIN estimates too many rows → background export → deliver the link" —
# lives in pipeline._execute_sql and was previously untested. These pin that
# branch: when the planner estimates > UI_RENDER_THRESHOLD rows, the user must
# get the download URL (success) or a clear "narrow the query" message (failure),
# and an absurd estimate (> 100× the tenant limit) must be blocked outright.

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


async def _run_offload(estimated_rows: int, export_result: dict | None):
    """Drive _execute_sql to the EXPLAIN/offload branch with everything around it
    mocked: security check is a no-op, the tenant DB config is synthetic, and
    EXPLAIN + the export worker return canned values. db=None so the audit/RLS
    side paths are skipped."""
    from backend.app.query import pipeline

    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_pg_config())),
        patch(
            "backend.app.db.explain_query",
            new=AsyncMock(return_value={"estimated_rows": estimated_rows}),
        ),
        patch(
            "backend.app.worker.tasks.export_massive_query_to_minio",
            new=AsyncMock(return_value=export_result),
        ),
    ):
        await pipeline._execute_sql(
            sql="SELECT * FROM orders",
            engine=MagicMock(),
            workspace_id="ws1",
            db=None,
            user_id="u1",
            question="show all orders",
        )


@pytest.mark.asyncio
async def test_offload_delivers_download_url_when_estimate_exceeds_ui_threshold():
    """> 5000 estimated rows → the export URL is surfaced to the user."""
    export = {"status": "success", "url": "http://minio/aria-artifacts/exports/big.csv", "row_count": 50000}
    with pytest.raises(ValueError) as exc:
        await _run_offload(estimated_rows=50_000, export_result=export)
    msg = str(exc.value)
    assert export["url"] in msg
    assert "download" in msg.lower()


@pytest.mark.asyncio
async def test_offload_failure_asks_user_to_narrow_query():
    """Background export failed (no URL) → a clear, non-silent failure message."""
    export = {"status": "error", "url": None, "error": "boom"}
    with pytest.raises(ValueError) as exc:
        await _run_offload(estimated_rows=50_000, export_result=export)
    assert "narrow the query" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_absurd_estimate_is_blocked_before_export():
    """> 100× the tenant row limit → blocked outright, never handed to the worker."""
    export_called = AsyncMock(return_value={"status": "success", "url": "x"})
    from backend.app.query import pipeline

    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_pg_config(1000))),
        patch(
            "backend.app.db.explain_query",
            new=AsyncMock(return_value={"estimated_rows": 100_001}),  # > 1000 * 100
        ),
        patch("backend.app.worker.tasks.export_massive_query_to_minio", new=export_called),
    ):
        with pytest.raises(ValueError) as exc:
            await pipeline._execute_sql(
                sql="SELECT * FROM orders",
                engine=MagicMock(),
                workspace_id="ws1",
                db=None,
                user_id="u1",
                question="dump everything",
            )
    assert "security exception" in str(exc.value).lower()
    export_called.assert_not_called()
