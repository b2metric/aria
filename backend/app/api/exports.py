"""Export delivery endpoints (massive-export Phase 4, spec §D).

Surfaces the durable ``export_jobs`` rows produced by the chat export band:
- ``GET /api/exports/{job_id}`` — poll a job's status (queued/running/success/error)
  so the chat UI can turn its "preparing CSV" bubble into a download button.
- ``GET /api/exports/{job_id}/download`` — stream the finished CSV back through the
  backend (reachable at the app host) instead of handing out the internal
  ``minio:9000`` URL; this is the browser-reachable download path.

Both are workspace-scoped: a caller may only see/download a job whose
``workspace_id`` matches their own (honoring the existing RBAC/SQL-visibility
invariants).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.query import _get_engine
from backend.app.auth.dependencies import CurrentUser, WorkspaceID
from backend.app.models.export_job import ExportJob

router = APIRouter(prefix="/api/exports", tags=["exports"])


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


@router.get("/{job_id}", summary="Get the status of a CSV export job")
async def get_export_status(
    job_id: str,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> dict:
    """Return the export job's current lifecycle state for inline-chat polling."""
    job = await _load_owned_job(job_id, workspace_id)
    return {
        "id": str(job.id),
        "status": job.status,
        "row_count": job.row_count,
        "truncated": job.truncated,
        "total_estimate": job.total_estimate,
        "error": job.error,
        # The raw minio_url is intentionally NOT exposed; download goes through the
        # proxy below so the link is browser-reachable + access-controlled.
        "download_ready": job.status == "success" and bool(job.minio_key),
    }


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
