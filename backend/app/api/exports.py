"""Export delivery endpoints (massive-export Phase 4, spec §D).

Surfaces the durable ``export_jobs`` rows produced by the chat export band:
- ``GET /api/exports`` — list the caller's recent export jobs (workspace-scoped)
  for an Exports page.
- ``GET /api/exports/{job_id}`` — poll a job's status (queued/running/success/error)
  so the chat UI can turn its "preparing CSV" bubble into a download button.
- ``GET /api/exports/{job_id}/download`` — stream the finished CSV back through the
  backend (reachable at the app host) instead of handing out the internal
  ``minio:9000`` URL; this is the browser-reachable download path.

Both are workspace-scoped: a caller may only see/download a job whose
``workspace_id`` matches their own (honoring the existing RBAC/SQL-visibility
invariants).

Download links expire after the tenant's configured ``export_link_ttl_days``
(default 3): a finished job past its TTL is no longer ``download_ready`` and
the download endpoint 410s.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.query import _get_engine
from backend.app.auth.dependencies import CurrentUser, WorkspaceID
from backend.app.models.export_job import ExportJob

router = APIRouter(prefix="/api/exports", tags=["exports"])


async def _tenant_ttl_days(workspace_id: str) -> int:
    """The tenant's export-link validity in days (default 3)."""
    from backend.app.models.database import CustomerDBConfig
    from backend.app.models.organization import Customer  # customers.slug == workspace_id

    engine = await _get_engine()
    try:
        async with AsyncSession(engine) as sess:
            cust = await sess.scalar(select(Customer).where(Customer.slug == workspace_id))
            if cust is None:
                return 3
            cfg = await sess.scalar(
                select(CustomerDBConfig).where(CustomerDBConfig.customer_id == cust.id)
            )
            return int(getattr(cfg, "export_link_ttl_days", 3) or 3) if cfg else 3
    finally:
        await engine.dispose()


def _is_expired(job: ExportJob, ttl_days: int) -> bool:
    """Whether a finished job's download link is past its TTL."""
    if job.completed_at is None:
        return False
    completed = job.completed_at
    if completed.tzinfo is None:
        completed = completed.replace(tzinfo=UTC)
    return datetime.now(UTC) > completed + timedelta(days=ttl_days)


def _job_summary(job: ExportJob, ttl_days: int) -> dict:
    """Shared response shape for the list + status endpoints."""
    download_ready = (
        job.status == "success" and bool(job.minio_key) and not _is_expired(job, ttl_days)
    )
    return {
        "id": str(job.id),
        "status": job.status,
        "question": job.question,
        "row_count": job.row_count,
        "truncated": job.truncated,
        "total_estimate": job.total_estimate,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        # The raw minio_url is intentionally NOT exposed; download goes through the
        # proxy below so the link is browser-reachable + access-controlled.
        "download_ready": download_ready,
    }


async def _load_owned_job(job_id: str, workspace_id: str) -> ExportJob:
    """Fetch an export job, 404ing if it doesn't exist OR isn't the caller's."""
    try:
        jid = uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export job not found") from exc

    engine = await _get_engine()
    try:
        async with AsyncSession(engine) as sess:
            job = await sess.scalar(select(ExportJob).where(ExportJob.id == jid))
    finally:
        await engine.dispose()

    # Workspace scoping: never reveal another tenant's job (treat as not-found).
    if job is None or job.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export job not found")
    return job


@router.get("", summary="List the workspace's recent export jobs")
async def list_exports(
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> list[dict]:
    """Return the caller's recent export jobs (workspace-scoped), newest first."""
    engine = await _get_engine()
    try:
        async with AsyncSession(engine) as sess:
            rows = (
                await sess.scalars(
                    select(ExportJob)
                    .where(ExportJob.workspace_id == workspace_id)
                    .order_by(ExportJob.created_at.desc())
                    .limit(50)
                )
            ).all()
    finally:
        await engine.dispose()

    ttl_days = await _tenant_ttl_days(workspace_id)
    return [_job_summary(j, ttl_days) for j in rows]


@router.get("/{job_id}", summary="Get the status of a CSV export job")
async def get_export_status(
    job_id: str,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> dict:
    """Return the export job's current lifecycle state for inline-chat polling."""
    job = await _load_owned_job(job_id, workspace_id)
    ttl_days = await _tenant_ttl_days(workspace_id)
    return _job_summary(job, ttl_days)


@router.get("/{job_id}/download", summary="Download a finished export CSV (proxied)")
async def download_export(
    job_id: str,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> Response:
    """Stream the finished CSV through the backend (reachable host), fetching the
    object from MinIO internally so the browser never needs the ``minio:9000`` URL."""
    job = await _load_owned_job(job_id, workspace_id)

    if job.status != "success" or not job.minio_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Export is not ready for download (status: {job.status}).",
        )

    ttl_days = await _tenant_ttl_days(workspace_id)
    if _is_expired(job, ttl_days):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This export link has expired.")

    from agents.artifact_store import ArtifactStore

    data = ArtifactStore().download(job.minio_key)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export artifact is no longer available.",
        )

    filename = f"export_{job.id}.csv"
    return Response(
        content=data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
