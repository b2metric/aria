"""export_jobs ORM model — columns, defaults, and status lifecycle."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.models import Base
from backend.app.models.export_job import ExportJob, ExportStatus


@pytest.mark.asyncio
async def test_export_job_defaults_to_queued_and_persists():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ExportJob.__table__.create)

    job_id = uuid.uuid4()
    async with AsyncSession(engine) as sess:
        job = ExportJob(
            id=job_id,
            workspace_id="ws1",
            user_id="u1",
            conversation_id="ws1_u1",
            question="show all orders",
            sql="SELECT * FROM orders",
            total_estimate=5_000_000,
        )
        sess.add(job)
        await sess.commit()

    async with AsyncSession(engine) as sess:
        loaded = await sess.scalar(select(ExportJob).where(ExportJob.id == job_id))
        assert loaded is not None
        assert loaded.status == ExportStatus.QUEUED
        assert loaded.row_count is None
        assert loaded.truncated is False
        assert loaded.download_url is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_export_job_advances_to_success_with_url():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ExportJob.__table__.create)

    job_id = uuid.uuid4()
    async with AsyncSession(engine) as sess:
        sess.add(
            ExportJob(
                id=job_id, workspace_id="ws1", user_id="u1",
                conversation_id="c", question="q", sql="SELECT 1",
            )
        )
        await sess.commit()
    async with AsyncSession(engine) as sess:
        job = await sess.scalar(select(ExportJob).where(ExportJob.id == job_id))
        job.status = ExportStatus.SUCCESS
        job.row_count = 100_000
        job.truncated = True
        job.minio_key = "exports/ws1/c/data_export_abc.csv"
        job.download_url = "http://minio:9000/aria-artifacts/exports/ws1/c/data_export_abc.csv"
        await sess.commit()
    async with AsyncSession(engine) as sess:
        job = await sess.scalar(select(ExportJob).where(ExportJob.id == job_id))
        assert job.status == ExportStatus.SUCCESS
        assert job.row_count == 100_000
        assert job.truncated is True
        assert "data_export_abc.csv" in job.download_url
    await engine.dispose()
