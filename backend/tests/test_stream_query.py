"""stream_query yields the DB result in batches via fetchmany, per dialect."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import psycopg2.extras  # noqa: F401  (primes the submodule so patch("psycopg2.extras") can find it)

from backend.app.db.models import DatabaseType, DBConfig


def _cfg(db_type: DatabaseType) -> DBConfig:
    return DBConfig(
        db_type=db_type, host="h", port=0, database="d",
        username="u", password="p", export_batch_size=2,
    )


def _fake_cursor(rows, description):
    """A cursor whose fetchmany(n) drains `rows` in chunks of n."""
    cur = MagicMock()
    cur.description = description
    state = {"i": 0}

    def _fetchmany(n):
        i = state["i"]
        chunk = rows[i : i + n]
        state["i"] = i + n
        return chunk

    cur.fetchmany.side_effect = _fetchmany
    return cur


def test_postgres_stream_query_batches_rows():
    from backend.app.db import executor

    # psycopg2 RealDictCursor yields dict rows directly.
    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    cur = _fake_cursor(rows, description=[("id",)])
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    with patch("psycopg2.connect", return_value=conn), patch("psycopg2.extras"):
        ex = executor.PostgreSQLExecutor(_cfg(DatabaseType.POSTGRESQL))
        batches = list(ex.stream_query("SELECT * FROM t", batch_size=2))
    assert [len(b) for b in batches] == [2, 1]
    assert batches[0] == [{"id": 1}, {"id": 2}]
    assert batches[1] == [{"id": 3}]


def test_oracle_stream_query_zips_columns_and_batches():
    from backend.app.db import executor

    # oracledb returns tuples; the executor must zip with cur.description names.
    rows = [(1, "a"), (2, "b"), (3, "c")]
    cur = _fake_cursor(rows, description=[("ID",), ("NAME",)])
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    fake_oracledb = MagicMock()
    fake_oracledb.connect.return_value = conn
    with patch.dict("sys.modules", {"oracledb": fake_oracledb}):
        ex = executor.OracleExecutor(_cfg(DatabaseType.ORACLE))
        batches = list(ex.stream_query("SELECT id, name FROM t", batch_size=2))
    assert [len(b) for b in batches] == [2, 1]
    assert batches[0] == [{"ID": 1, "NAME": "a"}, {"ID": 2, "NAME": "b"}]
    assert batches[1] == [{"ID": 3, "NAME": "c"}]
    # arraysize set to the batch size for round-trip efficiency.
    assert cur.arraysize == 2


def test_stream_query_sync_dispatches_to_executor():
    from backend.app.db import executor

    cfg = _cfg(DatabaseType.POSTGRESQL)
    sentinel = iter([[{"id": 1}]])
    with patch.object(executor.PostgreSQLExecutor, "stream_query", return_value=sentinel) as m:
        gen = executor.stream_query_sync("SELECT 1", cfg, batch_size=500)
        assert list(gen) == [[{"id": 1}]]
    m.assert_called_once()
