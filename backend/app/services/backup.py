"""Backup-before-delete (AGENTS.md hard invariant).

The protected tables — ``customers``, ``token_usage_daily``, ``queries``,
``background_jobs`` — MUST be backed up to MinIO as JSON before ANY deletion.
This module is the single helper every such delete path must call FIRST. If the
backup upload fails it RAISES, so a delete can never proceed without a durable
backup (fail-closed).

There are currently no application delete paths for these tables, so the invariant
holds vacuously; this helper + the guard test (``test_backup_before_delete``) keep
it enforceable so a future delete cannot silently violate it.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from agents.artifact_store import ArtifactStore

log = logging.getLogger(__name__)

# Tables AGENTS.md requires backed up to MinIO JSON before deletion.
PROTECTED_TABLES: frozenset[str] = frozenset(
    {"customers", "token_usage_daily", "queries", "background_jobs"}
)


def _json_default(value: Any) -> str:
    """Serialize the non-JSON-native types that appear in ORM rows."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    return str(value)


def backup_before_delete(
    rows: list[dict[str, Any]],
    *,
    table: str,
    scope: str,
    stamp: str | None = None,
) -> str:
    """Serialize ``rows`` to JSON and upload to MinIO BEFORE the caller deletes them.

    Args:
        rows: the rows about to be deleted (already fetched as dicts).
        table: one of :data:`PROTECTED_TABLES`.
        scope: a caller label for the backup key (e.g. workspace id / customer id).
        stamp: optional deterministic key suffix (else a random hex).

    Returns:
        The backup object's URL.

    Raises:
        RuntimeError: if ``table`` is not protected (misuse guard) OR the upload
            fails — so the caller's delete is aborted (fail-closed).
    """
    if table not in PROTECTED_TABLES:
        raise RuntimeError(f"backup_before_delete called for non-protected table {table!r}")

    payload = json.dumps(
        {"table": table, "scope": scope, "row_count": len(rows), "rows": rows},
        default=_json_default,
    )
    key = f"backups/{table}/{scope}/{stamp or uuid.uuid4().hex}.json"
    try:
        ref = ArtifactStore().upload_json(payload, key=key)
    except Exception as exc:  # noqa: BLE001 — fail-closed: never delete without backup
        log.error("backup_before_delete FAILED for %s/%s: %s — aborting delete", table, scope, exc)
        raise RuntimeError(f"backup-before-delete failed for {table}; delete aborted") from exc

    url = ref.public_url() or ref.presigned_url(expires=86400 * 30)
    log.info("Backed up %d %s row(s) before delete -> %s", len(rows), table, key)
    return url
