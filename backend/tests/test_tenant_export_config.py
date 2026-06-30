"""Phase 1 — two-threshold export config (DBConfig DTO + admin API + invariant)."""

from __future__ import annotations

import pytest  # noqa: F401  # used by later tasks in this file

from backend.app.db.models import DBConfig, DatabaseType


def test_dbconfig_has_export_fields_with_defaults():
    cfg = DBConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="h",
        port=5432,
        database="d",
        username="u",
        password="p",
    )
    # display ceiling unchanged
    assert cfg.max_row_limit == 1000
    # new export ceiling + batch size defaults
    assert cfg.max_export_row_limit == 100_000
    assert cfg.export_batch_size == 50_000
