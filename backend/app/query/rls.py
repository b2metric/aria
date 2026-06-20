"""Row-level security (RLS): structural enforcement of per-table predicates.

ARIA must guarantee that a team/customer only ever sees the DB rows its policy
permits.  That guarantee cannot be delegated to the LLM — it has to be enforced
on the *generated SQL* itself.  This module rewrites a query so every filtered
table is replaced with a filtered subquery::

    FROM FCT_SALES              -> FROM (SELECT * FROM FCT_SALES WHERE REGION='KW') FCT_SALES
    JOIN DIM_CUSTOMER c ON ...  -> JOIN (SELECT * FROM DIM_CUSTOMER WHERE TENANT_ID=42) c ON ...

The rewrite is performed with ``sqlglot`` so the predicate is applied
structurally (per physical-table reference, including every JOINed occurrence)
rather than appended as a trusted WHERE clause that the LLM could subvert.

Fail-closed contract:  if the statement cannot be parsed/rewritten safely **and**
a filter applies to a table it references, we raise ``ValueError`` to reject the
query.  We never execute a statement that should have been filtered but wasn't.
If no row filter applies, the SQL is returned byte-for-byte unchanged.
"""

from __future__ import annotations

import logging
import re

import sqlglot
from sqlglot import expressions as exp
from sqlglot.errors import ParseError

logger = logging.getLogger("aria.query.rls")


def _references_filtered_table(sql: str, filter_keys: set[str]) -> bool:
    """Best-effort check: does the raw SQL text mention any filtered table?

    Used on the *fail-closed* path when parsing fails — we cannot rely on the
    parse tree, so we fall back to a case-insensitive word-boundary scan of the
    raw text.  A false positive only makes us reject a query we could not parse
    anyway; a false negative is impossible for table names that appear verbatim.
    """
    upper = sql.upper()
    return any(re.search(rf"\b{re.escape(name.upper())}\b", upper) for name in filter_keys)


def _wrap_table(table: exp.Table, predicate_sql: str, dialect: str | None) -> exp.Subquery:
    """Return ``(SELECT * FROM <table> WHERE <predicate>) <alias>`` for *table*.

    The inner FROM keeps the original (possibly schema-qualified) table so the
    physical reference is preserved; the subquery is aliased to the table's
    existing alias, or to its bare name when unaliased, so that qualified column
    references in the outer query continue to resolve.
    """
    alias_name = table.alias or table.name
    # Preserve schema / catalog qualification on the inner physical reference.
    inner_table = exp.Table(
        this=exp.to_identifier(table.name),
        db=exp.to_identifier(table.db) if table.db else None,
        catalog=exp.to_identifier(table.catalog) if table.catalog else None,
    )
    inner = (
        exp.Select()
        .select(exp.Star())
        .from_(inner_table)
        .where(sqlglot.condition(predicate_sql, dialect=dialect))
    )
    return exp.Subquery(this=inner, alias=exp.TableAlias(this=exp.to_identifier(alias_name)))


def apply_row_filters(
    sql: str,
    row_filters: dict[str, str] | None,
    dialect: str | None = None,
) -> str:
    """Rewrite *sql* so each filtered table is scoped by its row-level predicate.

    Args:
        sql: The generated SQL statement (already SELECT-only / table-pruned).
        row_filters: Per-table predicate map, e.g. ``{"FCT_SALES": "REGION='KW'"}``.
            Keys are matched to table names case-insensitively.  ``None`` / empty
            means no row restriction.
        dialect: sqlglot dialect to parse/generate with (e.g. ``"oracle"``).

    Returns:
        The rewritten SQL.  When no filter applies, the input is returned
        unchanged (byte-for-byte).

    Raises:
        ValueError: Fail-closed — if the statement references a filtered table
            but cannot be parsed/rewritten safely, the query is rejected rather
            than executed unfiltered.
    """
    if not row_filters:
        return sql

    # Normalise predicate keys to lower-case for case-insensitive matching.
    predicates = {name.lower(): pred for name, pred in row_filters.items() if pred}
    if not predicates:
        return sql

    filter_keys = set(predicates.keys())

    try:
        tree = sqlglot.parse_one(sql, dialect=dialect)
    except ParseError as exc:
        # Parsing failed.  Fail closed only if a filtered table is referenced.
        if _references_filtered_table(sql, filter_keys):
            logger.warning(
                "RLS fail-closed: could not parse SQL that references a filtered table: %s",
                exc,
            )
            raise ValueError(
                "Security Exception: query references a row-filtered table but could "
                "not be safely parsed for row-level security enforcement."
            ) from exc
        return sql

    if tree is None:
        if _references_filtered_table(sql, filter_keys):
            raise ValueError(
                "Security Exception: query references a row-filtered table but could "
                "not be safely parsed for row-level security enforcement."
            )
        return sql

    rewritten = tree.copy()
    applied = False

    # Replace every physical-table reference whose name matches a filter.  We
    # match only exp.Table nodes, so subquery-derived sources are untouched.
    for table in list(rewritten.find_all(exp.Table)):
        predicate_sql = predicates.get(table.name.lower())
        if predicate_sql is None:
            continue
        try:
            table.replace(_wrap_table(table, predicate_sql, dialect))
            applied = True
        except Exception as exc:  # pragma: no cover - defensive fail-closed
            logger.warning("RLS fail-closed: could not rewrite table %r: %s", table.name, exc)
            raise ValueError(
                f"Security Exception: could not apply row-level security filter to "
                f"table '{table.name}'."
            ) from exc

    if not applied:
        # No filtered table actually referenced → return original untouched.
        return sql

    return rewritten.sql(dialect=dialect)
