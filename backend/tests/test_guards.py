"""MECHANICAL GATE (model-independent, CI-blocking) for the read-only SQL guard.

`verify_read_only_sql` is the SELECT-only security invariant (AGENTS.md SQL
visibility / sprint-plan "SELECT-only guard"): the pipeline must never execute
DML/DDL against a customer DB. The guard existed but its *rejection* behaviour was
only used as a helper in test_rls.py, never asserted directly — so a refactor that
loosened the keyword list or the first-word check could silently weaken it. This
file pins the invariant: every write verb + statement-stacking + first-word evasion
must raise, and legitimate read-only shapes must pass.
"""

from __future__ import annotations

import pytest

from backend.app.query.guards import verify_read_only_sql

# Every DDL/DML verb the guard must reject, exercised as a realistic statement.
WRITE_STATEMENTS = [
    "UPDATE orders SET total = 0",
    "DELETE FROM orders WHERE id = 1",
    "INSERT INTO orders (id) VALUES (1)",
    "DROP TABLE orders",
    "TRUNCATE TABLE orders",
    "ALTER TABLE orders ADD col INT",
    "CREATE TABLE t (id INT)",
    "REPLACE INTO orders VALUES (1)",
    "GRANT SELECT ON orders TO bob",
    "REVOKE SELECT ON orders FROM bob",
    "MERGE INTO orders USING staging ON (1=1)",
    "EXEC sp_who",
    "EXECUTE sp_who",
    "CALL do_thing()",
    "COMMIT",
    "ROLLBACK",
]

# Read-only shapes the guard must allow (incl. CTE + EXPLAIN + benign look-alikes).
READ_ONLY_STATEMENTS = [
    "SELECT * FROM orders",
    "WITH t AS (SELECT 1) SELECT * FROM t",
    "EXPLAIN SELECT * FROM orders",
    "SELECT updated_at, created_at FROM orders",  # word-boundary: not UPDATE/CREATE
    "SELECT 'DROP TABLE x' AS note FROM dual",     # verb inside a string literal
    "SELECT id FROM orders -- DELETE FROM orders\n",  # verb inside a line comment
]


@pytest.mark.parametrize("sql", WRITE_STATEMENTS)
def test_write_statements_are_rejected(sql: str) -> None:
    with pytest.raises(ValueError):
        verify_read_only_sql(sql)


@pytest.mark.parametrize("sql", READ_ONLY_STATEMENTS)
def test_read_only_statements_are_allowed(sql: str) -> None:
    verify_read_only_sql(sql)  # must not raise


def test_statement_stacking_is_rejected() -> None:
    """A SELECT with a piggy-backed write must be blocked (';'-stacking evasion)."""
    with pytest.raises(ValueError):
        verify_read_only_sql("SELECT 1; DROP TABLE orders")


def test_non_select_first_word_is_rejected() -> None:
    """Even keyword-free SQL must start with SELECT/WITH/EXPLAIN."""
    with pytest.raises(ValueError):
        verify_read_only_sql("SHOW TABLES")


def test_empty_sql_is_rejected() -> None:
    with pytest.raises(ValueError):
        verify_read_only_sql("   ")
