"""Unit tests for scripts/vault-extract-remote.py (offline Oracle snapshot).

The Oracle SQL itself is integration-only; here we test the pure assembly logic
against a fake catalog + the JSON/coercion helpers.
"""

from __future__ import annotations

import datetime as dt
import decimal
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

_REPO = Path(__file__).resolve().parents[2]


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "vault_extract_remote", _REPO / "scripts" / "vault-extract-remote.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


mod = _load_script()


class FakeCatalog:
    """Duck-typed stand-in for OracleCatalog with canned per-table data."""

    def __init__(self, data: dict, dependents: dict | None = None, views: dict | None = None):
        self._data = data
        self._dependents = dependents or {}
        self._views = views or {}

    def columns(self, owner, t):
        return self._data[t]["columns"]

    def pks(self, owner, t):
        return set(self._data[t].get("pks", []))

    def row_count(self, owner, t):
        return self._data[t].get("row_count")

    def fks(self, owner, t):
        return self._data[t].get("fks", [])

    def distinct_count(self, owner, t, col):
        return self._data[t].get("distinct_counts", {}).get(col)

    def distinct_values(self, owner, t, col, limit):
        return self._data[t].get("distinct_values", {}).get(col, [])[:limit]

    def sample_rows(self, owner, t, limit):
        return self._data[t].get("sample_rows", [])[:limit]

    def self_view_query(self, owner, t):
        return self._views.get(t)

    def dependents(self, owner, t):
        return self._dependents.get(t, [])


# ── _coerce ──────────────────────────────────────────────────────────────────


def test_coerce_makes_values_json_safe():
    assert mod._coerce(None) is None
    assert mod._coerce("x") == "x"
    assert mod._coerce(5) == 5
    assert mod._coerce(True) is True
    assert mod._coerce(decimal.Decimal("10")) == 10  # integral → int
    assert mod._coerce(decimal.Decimal("10.5")) == 10.5
    assert mod._coerce(dt.datetime(2026, 7, 1, 12, 0, 0)) == "2026-07-01T12:00:00"
    assert mod._coerce(dt.date(2026, 7, 1)) == "2026-07-01"
    assert mod._coerce(b"\x00\x01") == "AAE="  # base64
    # whole payload must be JSON-serializable
    json.dumps([mod._coerce(v) for v in (None, 1, "a", decimal.Decimal("3.2"))])


# ── build_table_entry ──────────────────────────────────────────────────────────


def _cols(*specs):
    # spec: (name, dtype, nullable_bool)
    return [
        {"COLUMN_NAME": n, "DATA_TYPE": d, "IS_NULLABLE": "YES" if nu else "NO"}
        for (n, d, nu) in specs
    ]


def test_build_table_entry_assembles_columns_pk_enums_fks():
    data = {
        "FCT_PREP_REV": {
            "columns": _cols(
                ("CONTRNO", "NUMBER", False),
                ("BS_TYPE", "VARCHAR2", True),
                ("NOTE", "VARCHAR2", True),
            ),
            "pks": ["CONTRNO"],
            "row_count": 1234,
            "fks": [
                {
                    "SOURCE_COLUMN": "CONTRNO",
                    "TARGET_TABLE": "FCT_PREP_MASTER",
                    "TARGET_COLUMN": "CONTRNO",
                    "CONSTRAINT_NAME": "FK_REV_MASTER",
                }
            ],
            "distinct_counts": {"BS_TYPE": 3, "NOTE": 9999},  # NOTE too high → skipped
            "distinct_values": {"BS_TYPE": ["Data", "M2M", "Voice"]},
            "sample_rows": [{"CONTRNO": 1, "BS_TYPE": "Voice"}],
        }
    }
    cat = FakeCatalog(data)
    entry, errors = mod.build_table_entry(
        cat, "STC", "FCT_PREP_REV", max_cardinality=50, sample_limit=5
    )

    assert errors == []
    assert entry["table_name"] == "FCT_PREP_REV"
    assert entry["description"] is None  # preserved by replacer, not set here
    assert entry["row_count"] == 1234

    by_name = {c["name"]: c for c in entry["columns"]}
    assert by_name["CONTRNO"]["is_pk"] is True
    assert by_name["CONTRNO"]["nullable"] is False
    assert by_name["BS_TYPE"]["data_type"] == "VARCHAR2"

    # enum sampling: BS_TYPE captured (card 3 <= 50), NOTE skipped (9999 > 50)
    assert entry["enum_values"] == {"BS_TYPE": ["Data", "M2M", "Voice"]}
    assert by_name["BS_TYPE"]["example_values"] == ["Data", "M2M", "Voice"]
    assert "NOTE" not in entry["enum_values"]

    assert entry["relationships"][0]["target_table"] == "FCT_PREP_MASTER"
    assert entry["relationships"][0]["constraint_name"] == "FK_REV_MASTER"
    assert entry["sample_rows"] == [{"CONTRNO": 1, "BS_TYPE": "Voice"}]


def test_build_table_entry_missing_table_records_error():
    cat = FakeCatalog({"GONE": {"columns": []}})
    entry, errors = mod.build_table_entry(cat, "STC", "GONE")
    assert entry["columns"] == []
    assert errors and errors[0]["stage"] == "columns"


def test_build_table_entry_sample_rows_disabled():
    data = {"T": {"columns": _cols(("A", "NUMBER", True)), "sample_rows": [{"A": 1}]}}
    entry, _ = mod.build_table_entry(FakeCatalog(data), "STC", "T", sample_limit=0)
    assert entry["sample_rows"] == []


def test_self_materialized_view_captured():
    data = {"MV_REV": {"columns": _cols(("A", "NUMBER", True))}}
    views = {
        "MV_REV": {"name": "MV_REV", "kind": "materialized view", "query": "SELECT 1 FROM DUAL"}
    }
    entry, _ = mod.build_table_entry(FakeCatalog(data, views=views), "STC", "MV_REV", sample_limit=0)
    assert entry["materialized_view"]["kind"] == "materialized view"
    assert "SELECT 1" in entry["materialized_view"]["query"]


# ── collect_related_views ───────────────────────────────────────────────────────


def test_collect_related_views_dedupes_and_unions_references():
    dependents = {
        "FCT_PREP_REV": [{"NAME": "VW_REVENUE", "TYPE": "VIEW"}],
        "FCT_PREP_RECHARGE": [{"NAME": "VW_REVENUE", "TYPE": "VIEW"}],
    }
    views = {"VW_REVENUE": {"name": "VW_REVENUE", "kind": "view", "query": "SELECT ..."}}
    cat = FakeCatalog({}, dependents=dependents, views=views)
    result, errors = mod.collect_related_views(cat, "STC", ["FCT_PREP_REV", "FCT_PREP_RECHARGE"])

    assert errors == []
    assert len(result) == 1  # deduped
    v = result[0]
    assert v["name"] == "VW_REVENUE"
    assert set(v["references"]) == {"FCT_PREP_REV", "FCT_PREP_RECHARGE"}


def test_collect_related_views_skips_named_base_tables():
    # a table in the input list is not itself reported as a "related view"
    dependents = {"A": [{"NAME": "B", "TYPE": "VIEW"}]}
    cat = FakeCatalog(
        {}, dependents=dependents, views={"B": {"name": "B", "kind": "view", "query": "x"}}
    )
    result, _ = mod.collect_related_views(cat, "STC", ["A", "B"])
    assert result == []  # B is a base table in the list → excluded


# ── payload / writers ─────────────────────────────────────────────────────────


def test_assemble_and_write_json_is_import_compatible(tmp_path):
    data = {"T": {"columns": _cols(("A", "VARCHAR2", True)), "row_count": 1}}
    entry, _ = mod.build_table_entry(FakeCatalog(data), "STC", "T", sample_limit=0)
    payload = mod.assemble_payload("STC", [entry], [], [])

    # shape the importer (parse_json_metadata / enrich_from_metadata_json) relies on
    assert payload["schema_version"] == "1.0"
    assert payload["db_type"] == "oracle"
    assert payload["tables"][0]["table_name"] == "T"
    assert "data_type" in payload["tables"][0]["columns"][0]

    out = tmp_path / "meta.json"
    mod.write_json(payload, out)
    reloaded = json.loads(out.read_text())
    assert reloaded["tables"][0]["columns"][0]["name"] == "A"


def test_parse_args_exposes_thick_mode_flags():
    default = mod._parse_args(["--tables", "T"])
    assert default.thick is False
    assert default.lib_dir is None
    thick = mod._parse_args(["--tables", "T", "--thick", "--lib-dir", "/opt/ic"])
    assert thick.thick is True
    assert thick.lib_dir == "/opt/ic"


def test_load_table_list_dedupes_uppercases_and_skips_comments(tmp_path):
    f = tmp_path / "tabs.txt"
    f.write_text("# a comment\nfct_prep_rev\nDIM_PREP_PRODUCTS, fct_prep_rev\n  # indented comment\n")
    ns = SimpleNamespace(tables="dim_prep_products", tables_file=str(f))
    assert mod._load_table_list(ns) == ["DIM_PREP_PRODUCTS", "FCT_PREP_REV"]
