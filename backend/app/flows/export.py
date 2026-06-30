"""Batched, streaming CSV export flow (massive-export Phase 3, spec §C).

The chat pipeline routes a too-large result to the export band, inserts an
``export_jobs`` row (queued), and dispatches this flow. The flow streams the
bare SQL in batches (memory-bounded), writes the first ``max_export_row_limit``
rows to a single CSV in MinIO (multipart), and advances the job to
success/error — recording row count, truncation, MinIO key, and a presigned URL.

Mirrors ``reconcile.py``: the orchestration core is pure async (unit-tested with
mocked stream + mocked store + an injected session factory), and the Prefect
decoration is applied lazily so importing this module never needs a Prefect
server. Durability across backend restarts comes from running it as a Prefect
deployment in prod (the in-process asyncio fallback is dev-only).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable, Iterator
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

# Imported at module top so tests can monkeypatch flowmod.stream_query_sync /
# flowmod.ArtifactStore.
from agents.artifact_store import ArtifactStore
from backend.app.db.executor import stream_query_sync
from backend.app.db.models import DBConfig
from backend.app.models.base import utcnow
from backend.app.models.export_job import ExportJob, ExportStatus

logger = logging.getLogger(__name__)

_PRESIGN_EXPIRES = 86_400 * 3  # 3 days


def _capped_batches(
    batches: Iterator[list[dict[str, Any]]], ceiling: int
) -> tuple[Iterator[list[dict[str, Any]]], dict[str, Any]]:
    """Wrap a batch iterator so it yields at most ``ceiling`` rows. The returned
    ``stats`` dict is filled as a side effect: row_count + truncated."""
    stats: dict[str, Any] = {"row_count": 0, "truncated": False}

    def _gen() -> Iterator[list[dict[str, Any]]]:
        remaining = ceiling
        for batch in batches:
            if remaining <= 0:
                stats["truncated"] = True
                break
            if len(batch) > remaining:
                stats["truncated"] = True
                batch = batch[:remaining]
            remaining -= len(batch)
            stats["row_count"] += len(batch)
            yield batch

    return _gen(), stats


async def _set_job(
    session_factory: Callable[[], AsyncSession], job_id: uuid.UUID, **values: Any
) -> None:
    async with session_factory() as sess:
        await sess.execute(update(ExportJob).where(ExportJob.id == job_id).values(**values))
        await sess.commit()


async def export_query_core(
    *,
    job_id: uuid.UUID,
    sql: str,
    config: DBConfig,
    workspace_id: str,
    conversation_id: str | None,
    user_id: str | None,
    session_factory: Callable[[], AsyncSession],
) -> None:
    """Run one export job end-to-end, advancing the export_jobs row.

    Never raises: any failure is recorded as ``status=error`` on the job so the
    chat surface and the (Phase 4) Exports list can show a terminal state.
    """
    ceiling = config.max_export_row_limit
    batch_size = min(config.export_batch_size, ceiling)

    try:
        await _set_job(session_factory, job_id, status=ExportStatus.RUNNING, started_at=utcnow())

        loop = asyncio.get_event_loop()
        raw_batches = await loop.run_in_executor(
            None, lambda: stream_query_sync(sql, config, batch_size=batch_size)
        )
        capped, stats = _capped_batches(raw_batches, ceiling)

        store = ArtifactStore()
        key = f"exports/{workspace_id}/{conversation_id or 'adhoc'}/data_export_{uuid.uuid4().hex[:8]}.csv"
        # The blocking MinIO multipart upload (which pulls the stream, which pulls
        # the DB cursor) runs in a thread so the event loop is not blocked.
        ref = await loop.run_in_executor(None, lambda: store.upload_csv_stream(capped, key=key))

        if ref is None:
            await _set_job(
                session_factory, job_id, status=ExportStatus.SUCCESS,
                row_count=0, truncated=False, completed_at=utcnow(),
            )
            return

        url = ref.public_url() or ref.presigned_url(expires=_PRESIGN_EXPIRES)
        await _set_job(
            session_factory, job_id,
            status=ExportStatus.SUCCESS,
            row_count=stats["row_count"],
            truncated=stats["truncated"],
            minio_key=ref.key,
            download_url=url,
            completed_at=utcnow(),
        )
        logger.info(
            "Export job %s succeeded: %d rows (truncated=%s)",
            job_id, stats["row_count"], stats["truncated"],
        )
    except Exception as exc:  # noqa: BLE001 — terminal error recorded on the job
        logger.exception("Export job %s failed", job_id)
        try:
            await _set_job(
                session_factory, job_id, status=ExportStatus.ERROR,
                error=str(exc)[:2000], completed_at=utcnow(),
            )
        except Exception:  # noqa: BLE001 — the job-row write itself failed; original error already logged
            logger.exception("Failed to record ERROR terminal state for export job %s", job_id)


async def export_query_flow(
    job_id: str,
    sql: str,
    db_config_json: dict,
    workspace_id: str,
    conversation_id: str | None,
    user_id: str | None,
    max_export_row_limit: int,
    export_batch_size: int,
) -> None:
    """Prefect entrypoint: rebuild DBConfig + a session factory, then run the core.

    Imported lazily by the dispatcher; Prefect-serializable args only (no live
    SQLAlchemy objects), so DBConfig arrives as a plain dict.
    """
    from backend.app.api.query import _get_engine
    from backend.app.db.models import DatabaseType

    engine = await _get_engine()
    config = DBConfig(
        db_type=DatabaseType(db_config_json["db_type"]),
        host=db_config_json["host"], port=db_config_json["port"],
        database=db_config_json["database"], username=db_config_json["username"],
        password=db_config_json["password"], options=db_config_json.get("options"),
        max_row_limit=db_config_json.get("max_row_limit", 1000),
        max_export_row_limit=max_export_row_limit, export_batch_size=export_batch_size,
    )
    try:
        await export_query_core(
            job_id=uuid.UUID(job_id), sql=sql, config=config,
            workspace_id=workspace_id, conversation_id=conversation_id, user_id=user_id,
            session_factory=lambda: AsyncSession(engine),
        )
    finally:
        await engine.dispose()


def get_export_flow():
    """Return the Prefect-decorated export flow (for deployment registration).

    Prefect is imported here, not at module top, so unit tests that exercise the
    core never need a Prefect install/server.
    """
    from prefect import flow

    return flow(name="export-query", log_prints=True)(export_query_flow)
