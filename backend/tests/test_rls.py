"""Unit tests for row-level security (RLS) SQL rewriting.

These tests exercise the pure ``apply_row_filters`` rewriter in
``backend.app.query.rls`` — no database required.  We parse the rewritten
SQL back with sqlglot and assert the row-filter predicate lands on the right
table, rather than asserting brittle string equality.
"""

from __future__ import annotations

import pytest
import sqlglot
from sqlglot import expressions as exp

from backend.app.query.guards import verify_read_only_sql
from backend.app.query.rls import apply_row_filters


def _table_has_predicate(sql: str, table_name: str, dialect: str | None = None) -> bool:
    """Return True if a subquery scoping *table_name* with a WHERE clause exists.

    The rewriter substitutes ``FROM T`` with ``FROM (SELECT * FROM T WHERE ...) T``.
    We confirm at least one subquery selecting from *table_name* carries a WHERE.
    """
    tree = sqlglot.parse_one(sql, dialect=dialect)
    target = table_name.lower()
    for subquery in tree.find_all(exp.Subquery):
        inner = subquery.this
        if not isinstance(inner, exp.Select):
            continue
        from_tables = [t.name.lower() for t in inner.find_all(exp.Table)]
        if target in from_tables and inner.args.get("where") is not None:
            return True
    return False


# ── (a) filter injected for a filtered table ────────────────────────────────


def test_filter_injected_for_filtered_table():
    sql = "SELECT * FROM FCT_SALES"
    out = apply_row_filters(sql, {"FCT_SALES": "REGION = 'KW'"}, dialect="oracle")

    assert _table_has_predicate(out, "FCT_SALES", dialect="oracle")
    assert "REGION" in out.upper()
    # Result must still be a read-only SELECT
    verify_read_only_sql(out)


# ── (b) SQL untouched when no policy / no row_filters ────────────────────────


def test_no_filters_passes_through_byte_for_byte():
    sql = "SELECT a, b FROM FCT_SALES WHERE a > 1"
    assert apply_row_filters(sql, {}, dialect="oracle") == sql
    assert apply_row_filters(sql, None, dialect="oracle") == sql  # type: ignore[arg-type]


def test_filters_for_unreferenced_table_pass_through_byte_for_byte():
    # The filter targets a table the query never touches → no rewrite needed.
    sql = "SELECT a, b FROM FCT_SALES WHERE a > 1"
    out = apply_row_filters(sql, {"DIM_CUSTOMER": "TENANT_ID = 42"}, dialect="oracle")
    assert out == sql


# ── (c) multi-table query filters each filtered table ────────────────────────


def test_multi_table_query_filters_each_filtered_table():
    sql = "SELECT s.AMOUNT, c.NAME FROM FCT_SALES s JOIN DIM_CUSTOMER c ON s.CUST_ID = c.ID"
    out = apply_row_filters(
        sql,
        {"FCT_SALES": "REGION = 'KW'", "DIM_CUSTOMER": "TENANT_ID = 42"},
        dialect="oracle",
    )

    assert _table_has_predicate(out, "FCT_SALES", dialect="oracle")
    assert _table_has_predicate(out, "DIM_CUSTOMER", dialect="oracle")
    verify_read_only_sql(out)


# ── (d) a table with no predicate is left alone in a mixed query ─────────────


def test_unfiltered_table_left_alone_in_mixed_query():
    sql = "SELECT s.AMOUNT, d.LABEL FROM FCT_SALES s JOIN DIM_DATE d ON s.DT = d.DT"
    out = apply_row_filters(sql, {"FCT_SALES": "REGION = 'KW'"}, dialect="oracle")

    assert _table_has_predicate(out, "FCT_SALES", dialect="oracle")
    # DIM_DATE has no predicate → must NOT be wrapped in a filtered subquery.
    assert not _table_has_predicate(out, "DIM_DATE", dialect="oracle")
    verify_read_only_sql(out)


# ── (e) fail-closed when a filtered table can't be safely rewritten ──────────


def test_fail_closed_on_unparseable_sql_when_filter_applies():
    # Garbage that references a filtered table but cannot be parsed safely.
    sql = "SELECT FROM FROM FCT_SALES WHERE )("
    with pytest.raises(ValueError):
        apply_row_filters(sql, {"FCT_SALES": "REGION = 'KW'"}, dialect="oracle")


def test_garbage_with_no_applicable_filter_passes_through():
    # If parsing fails but NO filtered table is referenced, we must not block.
    sql = "SELECT FROM FROM SOME_OTHER WHERE )("
    out = apply_row_filters(sql, {"FCT_SALES": "REGION = 'KW'"}, dialect="oracle")
    assert out == sql


# ── (f) case-insensitive table matching ──────────────────────────────────────


def test_case_insensitive_table_matching():
    sql = "SELECT * FROM fct_sales"
    out = apply_row_filters(sql, {"FCT_SALES": "REGION = 'KW'"}, dialect="oracle")

    assert _table_has_predicate(out, "fct_sales", dialect="oracle")
    verify_read_only_sql(out)


def test_predicate_key_case_insensitive():
    # Predicate dict key uses a different case than the SQL table reference.
    sql = "SELECT * FROM FCT_SALES"
    out = apply_row_filters(sql, {"fct_sales": "REGION = 'KW'"}, dialect="oracle")
    assert _table_has_predicate(out, "FCT_SALES", dialect="oracle")


# ── extra: CTE / WITH queries still get scoped ───────────────────────────────


def test_with_cte_query_filters_underlying_table():
    sql = "WITH t AS (SELECT * FROM FCT_SALES) SELECT * FROM t"
    out = apply_row_filters(sql, {"FCT_SALES": "REGION = 'KW'"}, dialect="oracle")
    assert _table_has_predicate(out, "FCT_SALES", dialect="oracle")
    verify_read_only_sql(out)


def test_cte_name_collision_does_not_wrap_outer_reference():
    # A CTE named identically to a filtered physical table.  The OUTER
    # ``FROM FCT_SALES`` references the CTE — wrapping it would create a
    # circular self-reference ``(SELECT * FROM FCT_SALES WHERE ...) FCT_SALES``
    # that the DB rejects.  The CTE body selects from an *unfiltered* table, so
    # nothing should be wrapped and no error should be raised.
    sql = "WITH FCT_SALES AS (SELECT id FROM OTHER_TABLE) SELECT * FROM FCT_SALES"
    out = apply_row_filters(sql, {"FCT_SALES": "REGION = 'KW'"}, dialect="oracle")

    # Outer CTE reference must NOT be wrapped into a filtered subquery.
    assert not _table_has_predicate(out, "FCT_SALES", dialect="oracle")
    # The output must remain valid, parseable SELECT SQL.
    verify_read_only_sql(out)
    tree = sqlglot.parse_one(out, dialect="oracle")
    assert tree is not None
    # The outer FROM should still reference the CTE alias directly (unwrapped),
    # and no circular subquery should have been introduced.
    outer_select = tree.find(exp.Select)
    assert outer_select is not None


def test_cte_collision_still_wraps_filtered_table_inside_cte_body():
    # When the CTE shadows a filtered table BUT the CTE body itself selects FROM
    # the same filtered physical table, the inner physical reference must still
    # be wrapped; only the outer CTE-alias reference is skipped.
    sql = "WITH FCT_SALES AS (SELECT * FROM FCT_SALES) SELECT * FROM FCT_SALES"
    out = apply_row_filters(sql, {"FCT_SALES": "REGION = 'KW'"}, dialect="oracle")

    # The inner physical reference inside the CTE body must carry the predicate.
    assert _table_has_predicate(out, "FCT_SALES", dialect="oracle")
    verify_read_only_sql(out)
