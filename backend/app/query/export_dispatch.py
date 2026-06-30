"""Export-band side effects: a typed dispatch signal + job creation + flow dispatch.

Kept out of pipeline._execute_sql so the executor stays focused. The pipeline
generator (process_query) catches ExportDispatched and turns it into a clean
``export`` SSE event — replacing the old ValueError-as-delivery hack that the FE
rendered as a red "Query execution failed" and that triggered a duplicate export
via SQL self-correction.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import DBConfig
from backend.app.models.export_job import ExportJob

logger = logging.getLogger(__name__)

# Strong refs to in-flight dev-fallback export tasks so they aren't GC'd
# before completion (asyncio only holds weak refs to bare create_task results).
_PENDING_EXPORT_TASKS: set[asyncio.Task] = set()


class ExportDispatched(Exception):  # noqa: N818 — a signal, NOT an error; named for what it means
    """Raised by the export band to signal that the result is being exported
    asynchronously. NOT an error: process_query catches it BEFORE its generic
    self-correction handler and emits an ``export`` SSE event."""

    def __init__(self, *, job_id: uuid.UUID, estimated_rows: int) -> None:
        self.job_id = job_id
        self.estimated_rows = estimated_rows
        super().__init__(
            f"Result (~{estimated_rows:,} rows) too large to display; export job {job_id} dispatched."
        )


async def create_export_job(
    db: AsyncSession,
    *,
    workspace_id: str,
    user_id: str | None,
    conversation_id: str | None,
    question: str | None,
    sql: str,
    total_estimate: int,
) -> uuid.UUID:
    """Insert a queued export_jobs row and return its id. Caller commits."""
    job = ExportJob(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        question=question,
        sql=sql,
        total_estimate=total_estimate,
    )
    db.add(job)
    await db.flush()  # assign + surface PK without forcing the caller's commit boundary
    return job.id


def _config_to_json(config: DBConfig) -> dict:
    return {
        "db_type": config.db_type.value,
        "host": config.host,
        "port": config.port,
        "database": config.database,
        "username": config.username,
        "password": config.password,
        "options": config.options,
        "max_row_limit": config.max_row_limit,
    }


async def dispatch_export_job(
    *,
    job_id: uuid.UUID,
    sql: str,
    config: DBConfig,
    workspace_id: str,
    conversation_id: str | None,
    user_id: str | None,
) -> None:
    """Schedule the export flow. Prefer a durable Prefect deployment; fall back to
    an in-process asyncio task in dev (no Prefect server). Never blocks the turn."""
    payload = {
        "job_id": str(job_id),
        "sql": sql,
        "db_config_json": _config_to_json(config),
        "workspace_id": workspace_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "max_export_row_limit": config.max_export_row_limit,
        "export_batch_size": config.export_batch_size,
    }
    try:
        from prefect.deployments import run_deployment  # type: ignore[import-untyped]

        await run_deployment(
            name="export-query/export-query",
            parameters=payload,
            timeout=0,  # fire-and-forget: return immediately, don't await completion
        )
        logger.info("Export job %s dispatched via Prefect deployment", job_id)
        return
    except Exception as exc:  # noqa: BLE001 — dev fallback when no Prefect server/deployment
        logger.warning("Prefect dispatch unavailable (%s); running export in-process (dev)", exc)

    from backend.app.flows.export import export_query_flow

    task = asyncio.create_task(export_query_flow(**payload))
    _PENDING_EXPORT_TASKS.add(task)
    task.add_done_callback(_PENDING_EXPORT_TASKS.discard)
