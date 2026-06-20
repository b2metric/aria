"""Unit tests for column-level security (CLS) enforcement.

These tests exercise the two pure helpers in ``backend.app.query.cls`` — no
database required.  CLS hides ``deny_columns`` two ways:

  1. ``strip_denied_columns_from_schema`` removes denied columns from the
     ``table_columns`` schema dict fed to the LLM / rule-based SQL generator so
     the model can never SELECT or reference them (prevention).
  2. ``strip_denied_columns_from_rows`` strips denied columns from flat result
     rows post-execution, catching ``SELECT *`` / aliases that dodge layer 1
     (defense-in-depth).

Both helpers are pure: they return NEW structures, match case-insensitively on
table and column names, and never mutate their inputs.
"""

from __future__ import annotations

import copy

from backend.app.query.cls import (
    strip_denied_columns_from_rows,
    strip_denied_columns_from_schema,
)

# ── (a) denied column dropped from the schema (case-insensitive) ─────────────


def test_denied_column_dropped_from_schema():
    table_columns = {
        "DIM_PREP_PRODUCTS": [
            {"name": "PRODUCT_ID", "type": "NUMBER"},
            {"name": "PRODUCT_TYPE", "type": "VARCHAR2"},
            {"name": "PRODUCT_NAME", "type": "VARCHAR2"},
        ],
    }
    deny = {"DIM_PREP_PRODUCTS": ["PRODUCT_TYPE"]}

    out = strip_denied_columns_from_schema(table_columns, deny)

    names = [c["name"] for c in out["DIM_PREP_PRODUCTS"]]
    assert names == ["PRODUCT_ID", "PRODUCT_NAME"]
    assert "PRODUCT_TYPE" not in names


def test_denied_column_dropped_case_insensitive_table_and_column():
    # deny-list uses different case than the schema for BOTH table and column.
    table_columns = {
        "DIM_Prep_Products": [
            {"name": "Product_Id", "type": "NUMBER"},
            {"name": "Product_Type", "type": "VARCHAR2"},
        ],
    }
    deny = {"dim_prep_products": ["product_type"]}

    out = strip_denied_columns_from_schema(table_columns, deny)

    names = [c["name"] for c in out["DIM_Prep_Products"]]
    assert names == ["Product_Id"]


def test_denied_column_for_other_table_does_not_affect_this_table():
    # A deny entry for a DIFFERENT table must leave this table untouched.
    table_columns = {
        "FCT_SALES": [
            {"name": "AMOUNT", "type": "NUMBER"},
            {"name": "REGION", "type": "VARCHAR2"},
        ],
    }
    deny = {"DIM_CUSTOMER": ["AMOUNT"]}

    out = strip_denied_columns_from_schema(table_columns, deny)

    names = [c["name"] for c in out["FCT_SALES"]]
    assert names == ["AMOUNT", "REGION"]


# ── (b) denied column stripped from result rows (covers SELECT *) ────────────


def test_denied_column_stripped_from_select_star_rows():
    # Simulate a flat row dict produced by ``SELECT *`` that includes the
    # denied column — layer 1 (schema) cannot help here, layer 2 must.
    rows = [
        {"PRODUCT_ID": 1, "PRODUCT_TYPE": "secret", "PRODUCT_NAME": "Widget"},
        {"PRODUCT_ID": 2, "PRODUCT_TYPE": "secret2", "PRODUCT_NAME": "Gadget"},
    ]
    deny = {"DIM_PREP_PRODUCTS": ["PRODUCT_TYPE"]}

    out = strip_denied_columns_from_rows(rows, deny)

    assert out == [
        {"PRODUCT_ID": 1, "PRODUCT_NAME": "Widget"},
        {"PRODUCT_ID": 2, "PRODUCT_NAME": "Gadget"},
    ]
    for row in out:
        assert "PRODUCT_TYPE" not in row


def test_rows_strip_uses_union_of_all_denied_columns():
    # Post-execution we can't map a column back to its table, so the strip
    # uses the UNION of every denied-column list across all tables.
    rows = [{"AMOUNT": 10, "REVENUE": 99, "REGION": "KW"}]
    deny = {"FCT_SALES": ["REVENUE"], "DIM_OTHER": ["REGION"]}

    out = strip_denied_columns_from_rows(rows, deny)

    assert out == [{"AMOUNT": 10}]


def test_rows_strip_is_case_insensitive():
    rows = [{"Product_Type": "secret", "Product_Id": 1}]
    deny = {"DIM_PREP_PRODUCTS": ["PRODUCT_TYPE"]}

    out = strip_denied_columns_from_rows(rows, deny)

    assert out == [{"Product_Id": 1}]


# ── (c) no policy / empty deny_columns → identity (unchanged) ────────────────


def test_schema_unchanged_when_no_deny_columns():
    table_columns = {
        "FCT_SALES": [
            {"name": "AMOUNT", "type": "NUMBER"},
            {"name": "REGION", "type": "VARCHAR2"},
        ],
    }
    assert strip_denied_columns_from_schema(table_columns, None) == table_columns
    assert strip_denied_columns_from_schema(table_columns, {}) == table_columns


def test_rows_unchanged_when_no_deny_columns():
    rows = [{"AMOUNT": 10, "REGION": "KW"}]
    assert strip_denied_columns_from_rows(rows, None) == rows
    assert strip_denied_columns_from_rows(rows, {}) == rows


def test_empty_inputs_pass_through():
    assert strip_denied_columns_from_schema({}, {"T": ["C"]}) == {}
    assert strip_denied_columns_from_rows([], {"T": ["C"]}) == []


# ── (d) a non-denied column is preserved ─────────────────────────────────────


def test_non_denied_column_preserved_in_schema():
    table_columns = {
        "FCT_SALES": [
            {"name": "AMOUNT", "type": "NUMBER"},
            {"name": "MARGIN", "type": "NUMBER"},
        ],
    }
    deny = {"FCT_SALES": ["MARGIN"]}

    out = strip_denied_columns_from_schema(table_columns, deny)

    names = [c["name"] for c in out["FCT_SALES"]]
    assert "AMOUNT" in names  # non-denied preserved
    assert "MARGIN" not in names  # denied removed


def test_non_denied_column_preserved_in_rows():
    rows = [{"AMOUNT": 10, "MARGIN": 3}]
    deny = {"FCT_SALES": ["MARGIN"]}

    out = strip_denied_columns_from_rows(rows, deny)

    assert out == [{"AMOUNT": 10}]


# ── (e) immutability — inputs are never mutated ──────────────────────────────


def test_schema_inputs_not_mutated():
    table_columns = {
        "FCT_SALES": [
            {"name": "AMOUNT", "type": "NUMBER"},
            {"name": "MARGIN", "type": "NUMBER"},
        ],
    }
    deny = {"FCT_SALES": ["MARGIN"]}
    snapshot = copy.deepcopy(table_columns)

    out = strip_denied_columns_from_schema(table_columns, deny)

    # Original dict + its nested column lists must be untouched.
    assert table_columns == snapshot
    # A new top-level dict must be returned (not the same object).
    assert out is not table_columns
    # The retained column list must be a new list object (no shared ref that
    # could be mutated later) — defensive copy expectation.
    assert out["FCT_SALES"] is not table_columns["FCT_SALES"]


def test_rows_inputs_not_mutated():
    rows = [{"AMOUNT": 10, "MARGIN": 3}]
    deny = {"FCT_SALES": ["MARGIN"]}
    snapshot = copy.deepcopy(rows)

    out = strip_denied_columns_from_rows(rows, deny)

    assert rows == snapshot
    assert out is not rows
    assert out[0] is not rows[0]
