"""Read-only guard in ``pipeline._execute_sql`` (sqlglot path) — UNION coverage.

The guard requires a SINGLE statement whose parse tree is read-only. sqlglot
parses a top-level ``UNION [ALL]`` as a ``Union`` node — NOT a ``Select`` — so a
guard that only accepts ``Select`` roots rejects legitimate read-only set
queries (seen live: a CTE + ``UNION ALL`` revenue-segments query was blocked
with "Only read-only SELECT queries are permitted"). These tests pin that
single-statement set operations pass while writes and stacking stay blocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.db import DatabaseType, DBConfig


def _pg_config() -> DBConfig:
    return DBConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="db",
        port=5432,
        database="warehouse",
        username="u",
        password="p",
        max_row_limit=1000,
    )


def _mock_db() -> AsyncMock:
    """Customer-UUID lookup returns no row so ``_audit`` short-circuits."""
    db = AsyncMock()
    db.execute.return_value.fetchone.return_value = None
    return db


async def _run_guarded(sql: str):
    """Drive ``_execute_sql`` far enough that only the read-only guard can raise:
    security/config/EXPLAIN/execute are all mocked to benign values."""
    from backend.app.query import pipeline

    with (
        patch.object(pipeline, "verify_sql_security", new=AsyncMock(return_value=None)),
        patch.object(pipeline, "_get_db_config", new=AsyncMock(return_value=_pg_config())),
        patch.object(pipeline, "_resolve_vault_policy", new=AsyncMock(return_value=None)),
        patch(
            "backend.app.db.explain_query",
            new=AsyncMock(return_value={"estimated_rows": 10}),
        ),
        patch("backend.app.db.execute_query", new=AsyncMock(return_value=[{"x": 1}])),
    ):
        return await pipeline._execute_sql(
            sql=sql,
            engine=MagicMock(),
            workspace_id="ws1",
            db=_mock_db(),
            user_id="u1",
            question="q",
        )


READ_ONLY_SET_QUERIES = [
    "SELECT 1 AS x UNION ALL SELECT 2",
    "SELECT 1 AS x UNION SELECT 2",
    (
        "WITH cur AS (SELECT 1 AS x), prev AS (SELECT 2 AS x) "
        "SELECT 'cur' AS seg, x FROM cur "
        "UNION ALL SELECT 'prev' AS seg, x FROM prev "
        "UNION ALL SELECT 'total' AS seg, 3"
    ),
    "SELECT 1 AS x INTERSECT SELECT 1",
    "SELECT 1 AS x EXCEPT SELECT 2",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("sql", READ_ONLY_SET_QUERIES)
async def test_read_only_set_queries_are_allowed(sql: str) -> None:
    rows = await _run_guarded(sql)
    assert rows == [{"x": 1}]


@pytest.mark.asyncio
async def test_plain_select_still_allowed() -> None:
    rows = await _run_guarded("SELECT * FROM orders")
    assert rows == [{"x": 1}]


BLOCKED_QUERIES = [
    "INSERT INTO t SELECT 1",
    "SELECT 1; DROP TABLE orders",  # statement stacking
    "DELETE FROM orders UNION ALL SELECT 1",  # nonsense, but must not slip through
]


@pytest.mark.asyncio
@pytest.mark.parametrize("sql", BLOCKED_QUERIES)
async def test_writes_and_stacking_remain_blocked(sql: str) -> None:
    with pytest.raises(ValueError, match="Security Exception"):
        await _run_guarded(sql)
