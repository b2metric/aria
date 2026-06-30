"""export_query_core: streams a bounded export to MinIO and advances the job."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.db.models import DatabaseType, DBConfig
from backend.app.models.export_job import ExportJob, ExportStatus


def _cfg() -> DBConfig:
    return DBConfig(
        db_type=DatabaseType.POSTGRESQL, host="h", port=5432, database="d",
        username="u", password="p", max_export_row_limit=5, export_batch_size=2,
    )


async def _seed_job(engine) -> uuid.UUID:
    jid = uuid.uuid4()
    async with AsyncSession(engine) as sess:
        sess.add(ExportJob(
            id=jid, workspace_id="ws1", user_id="u1", conversation_id="c",
            question="all rows", sql="SELECT * FROM big", total_estimate=1_000_000,
        ))
        await sess.commit()
    return jid


class _FakeRef:
    def __init__(self, key):
        self.key = key
    def public_url(self):
        return ""
    def presigned_url(self, expires=0):
        return "http://minio:9000/aria-artifacts/" + self.key


@pytest.mark.asyncio
async def test_flow_success_writes_capped_rows_and_marks_success(monkeypatch):
    from backend.app.flows import export as flowmod

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ExportJob.__table__.create)  # FK-free: create only this table
    jid = await _seed_job(engine)

    # 6 rows from the DB but ceiling is 5 → expect truncated=True, row_count=5.
    def fake_stream(sql, cfg, *, batch_size, params=None):
        yield [{"id": 1}, {"id": 2}]
        yield [{"id": 3}, {"id": 4}]
        yield [{"id": 5}, {"id": 6}]
    monkeypatch.setattr(flowmod, "stream_query_sync", fake_stream)

    written = {}

    class FakeStore:
        def upload_csv_stream(self, batches, *, key, **kw):
            written["rows"] = [r for b in batches for r in b]
            written["key"] = key
            return _FakeRef(key)
    monkeypatch.setattr(flowmod, "ArtifactStore", FakeStore)

    await flowmod.export_query_core(
        job_id=jid, sql="SELECT * FROM big", config=_cfg(),
        workspace_id="ws1", conversation_id="c", user_id="u1",
        session_factory=lambda: AsyncSession(engine),
    )

    assert len(written["rows"]) == 5  # capped at max_export_row_limit
    async with AsyncSession(engine) as sess:
        job = await sess.scalar(select(ExportJob).where(ExportJob.id == jid))
        assert job.status == ExportStatus.SUCCESS
        assert job.row_count == 5
        assert job.truncated is True
        assert job.download_url and "aria-artifacts" in job.download_url
        assert job.completed_at is not None
    await engine.dispose()


@pytest.mark.asyncio
async def test_flow_marks_error_when_stream_raises(monkeypatch):
    from backend.app.flows import export as flowmod

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ExportJob.__table__.create)  # FK-free: create only this table
    jid = await _seed_job(engine)

    def boom(sql, cfg, *, batch_size, params=None):
        raise RuntimeError("db down")
        yield  # pragma: no cover
    monkeypatch.setattr(flowmod, "stream_query_sync", boom)

    await flowmod.export_query_core(
        job_id=jid, sql="SELECT * FROM big", config=_cfg(),
        workspace_id="ws1", conversation_id="c", user_id="u1",
        session_factory=lambda: AsyncSession(engine),
    )

    async with AsyncSession(engine) as sess:
        job = await sess.scalar(select(ExportJob).where(ExportJob.id == jid))
        assert job.status == ExportStatus.ERROR
        assert "db down" in (job.error or "")
        assert job.download_url is None
    await engine.dispose()
