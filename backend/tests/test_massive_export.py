"""TIER 1 item 5 — large-result export delivers a download URL.

The pipeline now awaits ``export_massive_query_to_minio`` and surfaces its URL to
the user (previously fire-and-forget discarded it). These tests pin the worker's
contract: it dumps the full result to CSV in MinIO and returns a download URL.
"""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

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
