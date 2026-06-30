"""Export delivery endpoints — workspace scoping + download readiness (Phase 4 §D)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.models.export_job import ExportJob, ExportStatus


async def _engine_with_job(**job_kwargs) -> tuple:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ExportJob.__table__.create)  # FK-free: create only this table
    jid = uuid.uuid4()
    async with AsyncSession(engine) as sess:
        sess.add(ExportJob(id=jid, **job_kwargs))
        await sess.commit()
    return engine, jid


@pytest.mark.asyncio
async def test_status_returns_job_for_owning_workspace():
    from backend.app.api import exports

    engine, jid = await _engine_with_job(
        workspace_id="ws1", user_id="u1", conversation_id="c", question="q",
        sql="SELECT 1", status=ExportStatus.SUCCESS, row_count=100_000, truncated=True,
        minio_key="exports/ws1/c/data.csv",
    )
    with patch.object(exports, "_get_engine", return_value=engine):
        out = await exports.get_export_status(str(jid), workspace_id="ws1", user=None)
    assert out["status"] == ExportStatus.SUCCESS
    assert out["row_count"] == 100_000
    assert out["truncated"] is True
    assert out["download_ready"] is True
    await engine.dispose()


@pytest.mark.asyncio
async def test_status_404s_for_other_workspace():
    """A caller MUST NOT see another tenant's export job (workspace isolation)."""
    from backend.app.api import exports

    engine, jid = await _engine_with_job(
        workspace_id="ws1", user_id="u1", conversation_id="c", question="q",
        sql="SELECT 1", status=ExportStatus.SUCCESS, minio_key="k",
    )
    with patch.object(exports, "_get_engine", return_value=engine), pytest.raises(HTTPException) as exc:
        await exports.get_export_status(str(jid), workspace_id="ws2", user=None)
    assert exc.value.status_code == 404
    await engine.dispose()


@pytest.mark.asyncio
async def test_status_404s_for_unknown_id():
    from backend.app.api import exports

    engine, _ = await _engine_with_job(
        workspace_id="ws1", user_id="u1", conversation_id="c", question="q",
        sql="SELECT 1", status=ExportStatus.QUEUED,
    )
    with patch.object(exports, "_get_engine", return_value=engine), pytest.raises(HTTPException) as exc:
        await exports.get_export_status(str(uuid.uuid4()), workspace_id="ws1", user=None)
    assert exc.value.status_code == 404
    await engine.dispose()


@pytest.mark.asyncio
async def test_download_409s_when_not_ready():
    from backend.app.api import exports

    engine, jid = await _engine_with_job(
        workspace_id="ws1", user_id="u1", conversation_id="c", question="q",
        sql="SELECT 1", status=ExportStatus.RUNNING,
    )
    with patch.object(exports, "_get_engine", return_value=engine), pytest.raises(HTTPException) as exc:
        await exports.download_export(str(jid), workspace_id="ws1", user=None)
    assert exc.value.status_code == 409
    await engine.dispose()


@pytest.mark.asyncio
async def test_download_streams_csv_bytes_for_ready_job():
    from backend.app.api import exports

    engine, jid = await _engine_with_job(
        workspace_id="ws1", user_id="u1", conversation_id="c", question="q",
        sql="SELECT 1", status=ExportStatus.SUCCESS, row_count=2,
        minio_key="exports/ws1/c/data.csv",
    )

    class _FakeStore:
        def download(self, key):
            assert key == "exports/ws1/c/data.csv"
            return b"id,amt\n1,10\n2,20\n"

    with (
        patch.object(exports, "_get_engine", return_value=engine),
        patch("agents.artifact_store.ArtifactStore", _FakeStore),
    ):
        resp = await exports.download_export(str(jid), workspace_id="ws1", user=None)
    assert resp.media_type == "text/csv; charset=utf-8"
    assert b"id,amt" in resp.body
    assert "attachment" in resp.headers["content-disposition"]
    await engine.dispose()
