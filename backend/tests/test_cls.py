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
from types import SimpleNamespace

import pytest

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


# ── (f) wiring: team-less request applies the customer-DEFAULT deny_columns ───
#
# Regression test for the HIGH finding: a request with team_id=None must still
# resolve the customer-wide-default policy (team_id IS NULL) so its
# deny_columns are pruned from the schema BEFORE it reaches the LLM (Step 1).
# Previously the Step-1 guard required ``team_id is not None``, so team-less
# requests leaked denied column names/types into the LLM prompt.


@pytest.mark.asyncio
async def test_team_less_request_prunes_default_policy_deny_columns(monkeypatch):
    from backend.app.query import pipeline

    workspace_id = "acme"
    tables = [{"name": "DIM_PREP_PRODUCTS", "keywords": "", "description": "", "order": 1}]
    full_columns = [
        {"name": "PRODUCT_ID", "type": "NUMBER", "description": ""},
        {"name": "PRODUCT_TYPE", "type": "VARCHAR2", "description": ""},  # denied
        {"name": "PRODUCT_NAME", "type": "VARCHAR2", "description": ""},
    ]

    async def fake_get_available_tables(engine, ws, db=None, team_id=None):
        return tables

    async def fake_get_table_columns(engine, table_name, ws):
        return list(full_columns)

    # Customer-wide DEFAULT policy (team_id IS NULL) carrying a deny-list.
    default_policy = SimpleNamespace(
        deny_columns={"DIM_PREP_PRODUCTS": ["PRODUCT_TYPE"]},
        row_filters=None,
    )

    async def fake_resolve_vault_policy(ws, db, team_id=None):
        # The default policy must be returned even when team_id is None.
        return default_policy

    # Capture what the LLM path actually receives as its schema.
    captured: dict = {}

    async def fake_generate_sql_with_llm(**kwargs):
        captured["table_columns"] = kwargs["table_columns"]
        return ("SELECT 1", "ok", {})

    monkeypatch.setattr(pipeline, "_get_available_tables", fake_get_available_tables)
    monkeypatch.setattr(pipeline, "_get_table_columns", fake_get_table_columns)
    monkeypatch.setattr(pipeline, "_resolve_vault_policy", fake_resolve_vault_policy)
    # generate_sql_with_llm is imported lazily inside _generate_sql from this module.
    monkeypatch.setattr(
        "backend.app.query.llm_sql.generate_sql_with_llm",
        fake_generate_sql_with_llm,
    )

    sentinel_db = object()  # a session IS available; team_id is None.
    # A question with no schema keyword overlap → low score → LLM path fires,
    # which is where we can observe the (pruned) table_columns.
    await pipeline._generate_sql(
        "zzz qqq xxx",
        engine=None,
        workspace_id=workspace_id,
        db=sentinel_db,
        team_id=None,
    )

    schema = captured["table_columns"]
    names = [c["name"] for c in schema["DIM_PREP_PRODUCTS"]]
    assert "PRODUCT_TYPE" not in names, "default-policy deny_columns must be pruned for team-less requests"
    assert names == ["PRODUCT_ID", "PRODUCT_NAME"]
