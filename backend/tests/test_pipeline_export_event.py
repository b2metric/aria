"""The export band raises ExportDispatched; _execute_sql creates+dispatches a job;
process_query turns the signal into an `export` SSE event WITHOUT self-correcting."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.db import DatabaseType, DBConfig
from backend.app.query.export_dispatch import ExportDispatched


def _cfg(max_row_limit=1000):
    return DBConfig(
        db_type=DatabaseType.POSTGRESQL, host="db", port=5432, database="w",
        username="u", password="p", max_row_limit=max_row_limit,
    )


@pytest.mark.asyncio
async def test_export_band_raises_export_dispatched_and_creates_job():
    from backend.app.query import pipeline

    fake_job_id = uuid.uuid4()
    db = AsyncMock()
    db.execute.return_value.fetchone.return_value = None  # no customer row → _audit short-circuits
    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_cfg())),
        patch.object(pipeline, "_resolve_vault_policy", new=AsyncMock(return_value=None)),
        patch("backend.app.db.explain_query", new=AsyncMock(return_value={"estimated_rows": 5_000_000})),
        patch.object(pipeline, "create_export_job", new=AsyncMock(return_value=fake_job_id)),
        patch.object(pipeline, "dispatch_export_job", new=AsyncMock(return_value=None)) as dispatch,
        pytest.raises(ExportDispatched) as exc,
    ):
        await pipeline._execute_sql(
            sql="SELECT * FROM orders", engine=MagicMock(), workspace_id="ws1",
            db=db, user_id="u1", question="all orders",
        )
    assert exc.value.job_id == fake_job_id
    assert exc.value.estimated_rows == 5_000_000
    dispatch.assert_awaited_once()


def test_export_event_shape():
    """_export_event yields a queued `export` SSE event carrying the job id."""
    from backend.app.query import pipeline

    fake_job_id = uuid.uuid4()
    event = pipeline._export_event(fake_job_id, 5_000_000)
    assert event["event"] == "export"
    data = json.loads(event["data"])
    assert data["export_job_id"] == str(fake_job_id)
    assert data["status"] == "queued"
    assert data["estimated_rows"] == 5_000_000
