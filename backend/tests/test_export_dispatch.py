"""create_export_job inserts a queued row; ExportDispatched carries the id+estimate."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.models.export_job import ExportJob, ExportStatus
from backend.app.query.export_dispatch import ExportDispatched, create_export_job


@pytest.mark.asyncio
async def test_create_export_job_inserts_queued_row():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(ExportJob.__table__.create)  # FK-free: create only this table
    async with AsyncSession(engine) as sess:
        job_id = await create_export_job(
            sess, workspace_id="ws1", user_id="u1", conversation_id="c",
            question="all rows", sql="SELECT * FROM big", total_estimate=5_000_000,
        )
        await sess.commit()
    async with AsyncSession(engine) as sess:
        job = await sess.scalar(select(ExportJob).where(ExportJob.id == job_id))
        assert job.status == ExportStatus.QUEUED
        assert job.total_estimate == 5_000_000
        assert job.sql == "SELECT * FROM big"
    await engine.dispose()


def test_export_dispatched_carries_job_id_and_estimate():
    jid = uuid.uuid4()
    exc = ExportDispatched(job_id=jid, estimated_rows=5_000_000)
    assert exc.job_id == jid
    assert exc.estimated_rows == 5_000_000
    assert "5,000,000" in str(exc)
