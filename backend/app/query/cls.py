"""Column-level security (CLS): hide ``deny_columns`` from SQL + results.

``TeamVaultPolicy.deny_columns`` is a per-table deny-list, shape
``{"TABLE_NAME": ["COL1", "COL2"]}``.  ARIA enforces it two layers deep:

  1. **Prevention** — :func:`strip_denied_columns_from_schema` drops denied
     columns from the ``table_columns`` schema dict *before* it is handed to the
     LLM / rule-based SQL generator, so the model can never SELECT or otherwise
     reference a denied column.
  2. **Defense-in-depth** — :func:`strip_denied_columns_from_rows` strips denied
     columns from the flat result rows *after* execution by name.  It catches
     ``SELECT *`` and any column that KEEPS its original name; a renamed alias
     (``SELECT revenue AS r``) is NOT stripped, but in practice cannot reach
     here when layer 1 fires (the LLM never saw the column to alias it).

Both helpers are pure: they return NEW structures, match table and column names
case-insensitively, and never mutate their inputs (project immutability rule).
The denied-column lists are matched against UPPERCASE Oracle vault names in
practice (e.g. ``DIM_PREP_PRODUCTS`` / ``PRODUCT_TYPE``) but the matching is
case-insensitive to stay robust to any casing.
"""

from __future__ import annotations

DenyColumns = dict[str, list[str]]


def strip_denied_columns_from_schema(
    table_columns: dict[str, list[dict]],
    deny_columns: DenyColumns | None,
) -> dict[str, list[dict]]:
    """Return a copy of *table_columns* with each table's denied columns removed.

    Args:
        table_columns: Per-table column schema, e.g.
            ``{"DIM_PREP_PRODUCTS": [{"name": "PRODUCT_TYPE", "type": ...}, ...]}``.
            Each column is a dict carrying at least a ``"name"`` key.
        deny_columns: Per-table deny-list, e.g.
            ``{"DIM_PREP_PRODUCTS": ["PRODUCT_TYPE"]}``.  Matched
            case-insensitively on BOTH table name and column name.  ``None`` or
            empty means no columns are hidden.

    Returns:
        A NEW dict (with new per-table column lists) where every column whose
        name appears in that table's deny-list has been dropped.  When
        *deny_columns* is falsy the original input is returned unchanged.
    """
    if not deny_columns:
        # Identity by value: nothing to hide, so return the input untouched.
        return table_columns

    # Build a case-insensitive lookup: table-name(lower) -> set of denied
    # column names(lower).  Robust to any casing on either side.
    denied_by_table: dict[str, set[str]] = {
        str(table).lower(): {str(col).lower() for col in (cols or [])}
        for table, cols in deny_columns.items()
    }

    result: dict[str, list[dict]] = {}
    for table_name, columns in table_columns.items():
        denied = denied_by_table.get(str(table_name).lower())
        if not denied:
            # No deny-list for this table — keep all columns (new list, no
            # shared reference with the input).
            result[table_name] = list(columns)
            continue
        result[table_name] = [
            col for col in columns if str(col.get("name", "")).lower() not in denied
        ]
    return result


def strip_denied_columns_from_rows(
    rows: list[dict],
    deny_columns: DenyColumns | None,
) -> list[dict]:
    """Return a copy of *rows* with every denied column key removed.

    Result rows are FLAT dicts (column name -> value) and post-execution a
    result column cannot be reliably mapped back to its source table, so we
    strip any key whose name (case-insensitive) appears in the UNION of all
    denied-column lists across the policy.

    Args:
        rows: Flat result rows, e.g. ``[{"PRODUCT_ID": 1, "PRODUCT_TYPE": ...}]``.
        deny_columns: Per-table deny-list (see
            :func:`strip_denied_columns_from_schema`).  The union of all its
            column names is stripped.  ``None`` / empty means rows pass through
            unchanged.

    Returns:
        NEW row dicts with denied keys removed.  When *deny_columns* is falsy
        the original input is returned unchanged.
    """
    if not deny_columns:
        return rows

    # Union of every denied column name across all tables, lower-cased.
    denied: set[str] = {str(col).lower() for cols in deny_columns.values() for col in (cols or [])}
    if not denied:
        return rows

    return [{k: v for k, v in row.items() if str(k).lower() not in denied} for row in rows]
