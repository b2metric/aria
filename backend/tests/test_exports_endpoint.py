"""Export delivery endpoints — workspace scoping + download readiness (Phase 4 §D)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

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


async def _engine_with_jobs(*job_kwargs_list) -> tuple:
    """Like _engine_with_job but seeds multiple rows; returns (engine, [ids])."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ExportJob.__table__.create)
    ids = [uuid.uuid4() for _ in job_kwargs_list]
    async with AsyncSession(engine) as sess:
        for jid, kwargs in zip(ids, job_kwargs_list, strict=True):
            sess.add(ExportJob(id=jid, **kwargs))
        await sess.commit()
    return engine, ids


@pytest.mark.asyncio
async def test_status_returns_job_for_owning_workspace():
    from backend.app.api import exports

    engine, jid = await _engine_with_job(
        workspace_id="ws1", user_id="u1", conversation_id="c", question="q",
        sql="SELECT 1", status=ExportStatus.SUCCESS, row_count=100_000, truncated=True,
        minio_key="exports/ws1/c/data.csv",
    )
    with (
        patch.object(exports, "_get_engine", return_value=engine),
        patch.object(exports, "_tenant_ttl_days", AsyncMock(return_value=3)),
    ):
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
        patch.object(exports, "_tenant_ttl_days", AsyncMock(return_value=3)),
        patch("agents.artifact_store.ArtifactStore", _FakeStore),
    ):
        resp = await exports.download_export(str(jid), workspace_id="ws1", user=None)
    assert resp.media_type == "text/csv; charset=utf-8"
    assert b"id,amt" in resp.body
    assert "attachment" in resp.headers["content-disposition"]
    await engine.dispose()


# ---------------------------------------------------------------------------
# GET /api/exports — list endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_exports_returns_workspace_jobs_newest_first():
    from backend.app.api import exports

    now = datetime.now(UTC)
    engine, (jid_old, jid_new, jid_other_ws) = await _engine_with_jobs(
        {
            "workspace_id": "ws1", "user_id": "u1", "conversation_id": "c1", "question": "older",
            "sql": "SELECT 1", "status": ExportStatus.SUCCESS,
            "created_at": now - timedelta(hours=2),
        },
        {
            "workspace_id": "ws1", "user_id": "u1", "conversation_id": "c2", "question": "newer",
            "sql": "SELECT 1", "status": ExportStatus.QUEUED,
            "created_at": now - timedelta(minutes=5),
        },
        {
            "workspace_id": "ws2", "user_id": "u2", "conversation_id": "c3", "question": "other ws",
            "sql": "SELECT 1", "status": ExportStatus.SUCCESS,
            "created_at": now,
        },
    )
    with (
        patch.object(exports, "_get_engine", return_value=engine),
        patch.object(exports, "_tenant_ttl_days", AsyncMock(return_value=3)),
    ):
        out = await exports.list_exports(workspace_id="ws1", user=None)

    assert [row["id"] for row in out] == [str(jid_new), str(jid_old)]
    assert {row["question"] for row in out} == {"newer", "older"}
    await engine.dispose()


# ---------------------------------------------------------------------------
# Export link TTL enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_download_410s_when_expired():
    from backend.app.api import exports

    stale = datetime.now(UTC) - timedelta(days=10)
    engine, jid = await _engine_with_job(
        workspace_id="ws1", user_id="u1", conversation_id="c", question="q",
        sql="SELECT 1", status=ExportStatus.SUCCESS, row_count=2,
        minio_key="exports/ws1/c/data.csv", completed_at=stale,
    )
    with (
        patch.object(exports, "_get_engine", return_value=engine),
        patch.object(exports, "_tenant_ttl_days", AsyncMock(return_value=3)),
        pytest.raises(HTTPException) as exc,
    ):
        await exports.download_export(str(jid), workspace_id="ws1", user=None)
    assert exc.value.status_code == 410
    await engine.dispose()


@pytest.mark.asyncio
async def test_download_ready_false_when_expired():
    from backend.app.api import exports

    stale = datetime.now(UTC) - timedelta(days=10)
    engine, jid = await _engine_with_job(
        workspace_id="ws1", user_id="u1", conversation_id="c", question="q",
        sql="SELECT 1", status=ExportStatus.SUCCESS, row_count=2,
        minio_key="exports/ws1/c/data.csv", completed_at=stale,
    )
    with (
        patch.object(exports, "_get_engine", return_value=engine),
        patch.object(exports, "_tenant_ttl_days", AsyncMock(return_value=3)),
    ):
        out = await exports.get_export_status(str(jid), workspace_id="ws1", user=None)
    assert out["download_ready"] is False
    await engine.dispose()
