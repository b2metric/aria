"""Phase 2 — pure row-limit injection helper (dialect-aware, skip-if-present)."""

from __future__ import annotations

from backend.app.db import DatabaseType
from backend.app.query.pipeline import _inject_row_limit


def test_oracle_appends_fetch_first():
    out = _inject_row_limit("SELECT * FROM t", DatabaseType.ORACLE, 1000)
    assert "FETCH FIRST 1001 ROWS ONLY" in out  # limit + 1


def test_non_oracle_appends_limit():
    out = _inject_row_limit("SELECT * FROM t", DatabaseType.POSTGRESQL, 1000)
    assert "LIMIT 1001" in out


def test_skips_when_oracle_limit_already_present():
    sql = "SELECT * FROM t FETCH FIRST 10 ROWS ONLY"
    assert _inject_row_limit(sql, DatabaseType.ORACLE, 1000) == sql


def test_skips_when_limit_or_top_already_present():
    assert _inject_row_limit("SELECT * FROM t LIMIT 10", DatabaseType.POSTGRESQL, 1000) == \
        "SELECT * FROM t LIMIT 10"
    assert _inject_row_limit("SELECT TOP 10 * FROM t", DatabaseType.MSSQL, 1000) == \
        "SELECT TOP 10 * FROM t"


def test_skips_when_existing_limit_is_lowercase():
    sql = "SELECT * FROM t limit 10"
    assert _inject_row_limit(sql, DatabaseType.POSTGRESQL, 1000) == sql
