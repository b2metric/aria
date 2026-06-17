import logging
import asyncio
import csv
from io import StringIO
import json
import uuid
from typing import Any

from backend.app.db.executor import execute_query_sync
from backend.app.db.models import DBConfig
from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

async def export_massive_query_to_minio(
    sql: str,
    db_config: DBConfig,
    conversation_id: str,
    workspace_id: str,
) -> dict[str, Any]:
    """Execute a potentially massive query in the background and upload to MinIO.

    This function runs in a background worker (e.g. ARQ or FastAPI BackgroundTask).
    It bypasses the normal row limits to dump the full dataset into a CSV and
    uploads it directly to MinIO, returning a presigned download link.
    """
    from agents.artifact_store import ArtifactStore

    logger.info("Background export started for conversation %s", conversation_id)

    try:
        # We run the synchronous executor in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, lambda: execute_query_sync(sql, db_config))

        if not rows:
            logger.info("Export returned 0 rows.")
            return {"status": "success", "url": None, "row_count": 0}

        # Convert list of dicts to CSV string
        csv_file = StringIO()
        writer = csv.DictWriter(csv_file, fieldnames=rows[0].keys())
        writer.writeheader()

        # Write rows safely (handling Decimal, datetime etc)
        def _safe_val(v):
            if v is None: return ""
            return str(v)

        for row in rows:
            safe_row = {k: _safe_val(v) for k, v in row.items()}
            writer.writerow(safe_row)

        csv_content = csv_file.getvalue()

        # Upload to MinIO
        store = ArtifactStore()
        prefix = f"exports/{workspace_id}/{conversation_id}"
        file_key = f"{prefix}/data_export_{uuid.uuid4().hex[:8]}.csv"

        logger.info("Uploading %d rows to MinIO at %s", len(rows), file_key)

        csv_ref = store.upload_csv(
            csv_content,
            key_prefix=prefix,
            key=file_key
        )

        # Generate 3-day valid URL
        download_url = csv_ref.public_url() or csv_ref.presigned_url(expires=86400 * 3)

        logger.info("Export successful. URL generated.")

        return {
            "status": "success",
            "url": download_url,
            "row_count": len(rows)
        }

    except Exception as e:
        logger.exception("Massive export failed")
        return {
            "status": "error",
            "error": str(e)
        }