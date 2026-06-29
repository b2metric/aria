"""TIER 1 item 1 — backup-before-delete invariant (AGENTS.md).

The protected tables must be backed up to MinIO JSON before any delete, and the
upload must be fail-closed (a failed backup aborts the delete). There are no
application delete paths for these tables today, so these tests pin the helper's
behaviour + keep ``PROTECTED_TABLES`` in sync with the AGENTS.md invariant.
"""

from __future__ import annotations

import json
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.backup import PROTECTED_TABLES, backup_before_delete

_REPO = Path(__file__).resolve().parents[2]


def _patched_store(upload_side_effect=None):
    """Return a patch() ctx for ArtifactStore + the captured upload mock."""
    ref = types.SimpleNamespace(
        public_url=lambda: "http://minio/aria-artifacts/backups/x.json",
        presigned_url=lambda expires=0: "http://minio/presigned",
    )
    instance = MagicMock()
    if upload_side_effect is not None:
        instance.upload_json.side_effect = upload_side_effect
    else:
        instance.upload_json.return_value = ref
    cls = MagicMock(return_value=instance)
    return patch("backend.app.services.backup.ArtifactStore", cls), instance


def test_protected_tables_match_agents_md():
    text = (_REPO / "AGENTS.md").read_text()
    for table in PROTECTED_TABLES:
        assert table in text, f"{table} missing from AGENTS.md backup-before-delete invariant"
    # Exactly the four AGENTS.md names — no drift.
    assert {"customers", "token_usage_daily", "queries", "background_jobs"} == PROTECTED_TABLES


def test_backup_uploads_json_and_returns_url():
    ctx, store = _patched_store()
    with ctx:
        url = backup_before_delete(
            [{"id": "r1", "amount": 5}], table="queries", scope="ws1", stamp="fixed"
        )
    assert url
    store.upload_json.assert_called_once()
    call = store.upload_json.call_args
    body = json.loads(call.args[0])
    assert body["table"] == "queries"
    assert body["row_count"] == 1
    assert body["rows"][0]["id"] == "r1"
    assert call.kwargs["key"] == "backups/queries/ws1/fixed.json"


def test_rejects_non_protected_table():
    with pytest.raises(RuntimeError):
        backup_before_delete([], table="users", scope="ws1")  # users is never auto-deleted


def test_upload_failure_aborts_delete():
    ctx, _ = _patched_store(upload_side_effect=RuntimeError("minio down"))
    with ctx, pytest.raises(RuntimeError, match="delete aborted"):
        backup_before_delete([{"id": "r1"}], table="customers", scope="cust-1")
