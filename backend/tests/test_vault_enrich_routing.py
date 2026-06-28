"""Unit tests for Sprint C/D: LLM enrichment merge rules, per-operation model
routing, and the service-layer vault markdown parser.

Pure-logic only (no DB, no LLM) — fast regression coverage for the new code.
"""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path

from backend.app.schema_discovery.enrichment import TableEnrichment, enrich_vault_table
from backend.app.schema_discovery.models import ColumnInfo, TableInfo
from backend.app.schema_discovery.vault_generator import generate_table_markdown
from backend.app.services.llm_resolver import ResolvedLLM, _apply_operation_override
from backend.app.services.vault_llm_enrich import (
    ColumnDraft,
    TableEnrichmentDraft,
    draft_to_enrichment,
)
from backend.app.services.vault_md import parse_vault_file, read_enum_block, resolve_vault_file
from backend.app.services.vault_sync import VaultSyncService

_REPO = Path(__file__).resolve().parents[2]


# ── draft_to_enrichment: fill_empty must never clobber populated fields ──────


def test_fill_empty_drops_already_populated_description():
    draft = TableEnrichmentDraft(
        table_name="FCT_X",
        current_description="existing desc",  # already populated
        suggested_description="new LLM desc",
    )
    out = draft_to_enrichment(draft, mode="fill_empty")
    # populated description must NOT be overwritten (enrich_vault_table overwrites)
    assert out.description is None


def test_fill_empty_sets_blank_description():
    draft = TableEnrichmentDraft(
        table_name="FCT_X",
        current_description="",  # blank → fill
        suggested_description="new LLM desc",
    )
    out = draft_to_enrichment(draft, mode="fill_empty")
    assert out.description == "new LLM desc"


def test_overwrite_replaces_populated_description():
    draft = TableEnrichmentDraft(
        table_name="FCT_X",
        current_description="existing",
        suggested_description="replacement",
    )
    out = draft_to_enrichment(draft, mode="overwrite")
    assert out.description == "replacement"


def test_fill_empty_skips_already_described_columns():
    draft = TableEnrichmentDraft(
        table_name="FCT_X",
        columns=[
            ColumnDraft(name="A", suggested_description="newA", is_empty=True),
            ColumnDraft(name="B", suggested_description="newB", is_empty=False),
        ],
    )
    out = draft_to_enrichment(draft, mode="fill_empty")
    names = {c.name for c in out.columns}
    assert names == {"A"}  # B already had a description → skipped


def test_fields_filter_limits_what_is_applied():
    draft = TableEnrichmentDraft(
        table_name="FCT_X",
        current_description="",
        suggested_description="d",
        suggested_keywords=["k1", "k2"],
    )
    out = draft_to_enrichment(draft, mode="fill_empty", fields=["keywords"])
    assert out.description is None  # description not in fields
    assert out.keywords == ["k1", "k2"]


# ── per-operation model routing override ─────────────────────────────────────


def _base_llm() -> ResolvedLLM:
    return ResolvedLLM(
        api_base="http://litellm:4000",
        api_key="k",
        model="default-model",
        custom_llm_provider="litellm",
        source="customer_byok",
        temperature=0.1,
        max_tokens=2000,
    )


def test_operation_override_applies_model_and_params():
    om = {"sql_generation": {"model": "deepseek-reasoner", "temperature": 0.0, "max_tokens": 4000}}
    out = _apply_operation_override(_base_llm(), om, "sql_generation")
    assert out.model == "deepseek-reasoner"
    assert out.temperature == 0.0
    assert out.max_tokens == 4000
    assert out.operation == "sql_generation"


def test_operation_override_absent_returns_base():
    om = {"insight": {"model": "gemini-x"}}
    out = _apply_operation_override(_base_llm(), om, "sql_generation")
    assert out.model == "default-model"  # no sql_generation entry → unchanged


def test_operation_override_none_map_returns_base():
    out = _apply_operation_override(_base_llm(), None, "insight")
    assert out.model == "default-model"


def test_operation_override_partial_keeps_base_params():
    om = {"chart": {"model": "m"}}  # no temperature/max_tokens
    out = _apply_operation_override(_base_llm(), om, "chart")
    assert out.model == "m"
    assert out.temperature == 0.1  # inherited from base
    assert out.max_tokens == 2000


# ── vault_md parser + case-insensitive resolve + enum block ──────────────────


_MD = """---
table: FCT_DEMO
description: A demo fact table.
keywords: [demo, fact]
---

# FCT_DEMO

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-------------|
| ID | NUMBER | | ✓ | Primary key |
| STATUS | VARCHAR2 | ✓ | | Row status |

<!-- ARIA:ENUM-VALUES-START -->

## Sampled Values
*Auto-updated by vault sync. Last sampled: 2026-06-28T00:00:00Z*

- **STATUS**: `ACTIVE`, `CLOSED`, `PENDING`

<!-- ARIA:ENUM-VALUES-END -->
"""


def test_parse_vault_file(tmp_path):
    f = tmp_path / "FCT_DEMO.md"
    f.write_text(_MD)
    p = parse_vault_file(f)
    assert p["table_name"] == "FCT_DEMO"
    assert p["description"] == "A demo fact table."
    assert p["keywords"] == ["demo", "fact"]
    assert p["column_count"] == 2
    cols = {c["name"]: c for c in p["columns"]}
    assert cols["ID"]["is_pk"] is True
    assert cols["STATUS"]["description"] == "Row status"


def test_read_enum_block(tmp_path):
    f = tmp_path / "FCT_DEMO.md"
    f.write_text(_MD)
    enums = read_enum_block(f)
    assert enums == {"STATUS": ["ACTIVE", "CLOSED", "PENDING"]}


def test_resolve_vault_file_case_insensitive(tmp_path):
    (tmp_path / "FCT_DEMO.md").write_text(_MD)
    # request lowercase though the file is uppercase — must resolve to an
    # existing, readable file. (Asserting the exact-case name is filesystem
    # dependent — macOS is case-insensitive, the Linux container is not — so we
    # assert behavior, not the name.)
    resolved = resolve_vault_file(tmp_path, "fct_demo")
    assert resolved.exists()
    assert "FCT_DEMO" in resolved.read_text()


def test_resolve_vault_file_missing_falls_back_to_lower(tmp_path):
    resolved = resolve_vault_file(tmp_path, "NOPE")
    assert resolved.name == "nope.md"
    assert not resolved.exists()


# ── vault writers must emit contract-compliant markdown ──────────────────────
# (validate-vault.py is the contract; these prove creation / discovery / enrich
#  never re-introduce the duplicated-section / stale-placeholder drift.)


def _contract_errors(md_path: Path) -> list[str]:
    """Load scripts/validate-vault.py and return its ERROR list for one file."""
    spec = importlib.util.spec_from_file_location(
        "validate_vault", _REPO / "scripts" / "validate-vault.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    errors, _warnings = mod._validate_file(md_path)
    return errors


def test_sync_new_table_markdown_is_contract_clean(tmp_path):
    svc = VaultSyncService.__new__(VaultSyncService)  # skip DB-bound __init__
    svc.workspace_id = "ws-test"
    svc.vault_path = tmp_path
    svc.db_config = types.SimpleNamespace(db_type="oracle")

    svc._generate_new_markdown(
        "FCT_NEW",
        [
            {"name": "ID", "type": "NUMBER", "nullable": False, "is_pk": True},
            {"name": "AMT", "type": "NUMBER", "nullable": True, "is_pk": False},
        ],
    )
    text = (tmp_path / "FCT_NEW.md").read_text()
    assert "No description provided yet." not in text  # no stale placeholder
    assert "## Keywords" not in text  # no empty redundant body section
    assert _contract_errors(tmp_path / "FCT_NEW.md") == []


def test_discovery_generator_puts_description_in_frontmatter(tmp_path):
    table = TableInfo(
        name="FCT_PREP_RECHARGE",
        columns=[ColumnInfo(name="TOPUP_AMOUNT", data_type="NUMBER")],
    )
    md = generate_table_markdown(table, "ws-test", "oracle")
    # frontmatter (before the body) must carry the description — the pipeline
    # reads it from here, not the body.
    frontmatter = md.split("---")[1]
    assert "description:" in frontmatter
    assert "**Description:**" not in md  # no duplicate body line
    assert "## Keywords" not in md  # keywords live in frontmatter only

    f = tmp_path / "FCT_PREP_RECHARGE.md"
    f.write_text(md)
    assert _contract_errors(f) == []


def test_enrich_strips_legacy_description_placeholder(tmp_path):
    vault = tmp_path / "ws-test" / "tables"
    vault.mkdir(parents=True)
    (vault / "FCT_X.md").write_text(
        "---\n"
        "table: FCT_X\ndatabase: oracle\nworkspace: ws-test\nkeywords: []\n"
        "---\n\n# FCT_X\n\n"
        "**Description:** No description provided yet.\n\n"
        "## Columns\n\n"
        "| Column | Type | Nullable | PK | Description |\n"
        "|--------|------|----------|----|-------------|\n"
        "| ID | NUMBER |  | ✓ | id |\n"
    )
    res = enrich_vault_table(
        tmp_path,
        "ws-test",
        TableEnrichment(table_name="FCT_X", description="Real meaning of FCT_X."),
    )
    assert res["status"] == "success"
    out = (vault / "FCT_X.md").read_text()
    assert "No description provided yet." not in out  # placeholder stripped
    assert "description: Real meaning of FCT_X." in out  # frontmatter authority
    assert _contract_errors(vault / "FCT_X.md") == []


def test_vault_table_response_keeps_example_queries():
    """Regression: VaultTableResponse must declare example_queries, else the
    response_model silently drops curated queries from the admin UI payload."""
    from backend.app.api.workspaces import VaultTableResponse

    data = {
        "table_name": "FCT_PREP_PROVISION",
        "example_queries": [
            {"question": "Top bundles", "answer": "", "sql": "SELECT 1"},
        ],
        "enriched_at": "2026-06-16T14:59:52+00:00",
    }
    dumped = VaultTableResponse(**data).model_dump()
    assert len(dumped["example_queries"]) == 1
    assert dumped["example_queries"][0]["sql"] == "SELECT 1"
    assert dumped["enriched_at"] == "2026-06-16T14:59:52+00:00"


# ── keyword edit semantics: replace (user) vs union (enrichment) ─────────────


def _seed_table_with_keywords(tmp_path, keywords: list[str]):
    vault = tmp_path / "ws-test" / "tables"
    vault.mkdir(parents=True, exist_ok=True)
    kw = ", ".join(keywords)
    (vault / "FCT_K.md").write_text(
        f"---\ntable: FCT_K\ndatabase: oracle\nworkspace: ws-test\nkeywords: [{kw}]\n"
        "description: d\n---\n\n# FCT_K\n\n## Columns\n\n"
        "| Column | Type | Nullable | PK | Description |\n"
        "|--------|------|----------|----|-------------|\n"
        "| ID | NUMBER |  | ✓ | id |\n"
    )
    return tmp_path, vault / "FCT_K.md"


def _kw(md_path) -> list[str]:
    from backend.app.services.vault_md import parse_vault_file

    return parse_vault_file(md_path)["keywords"]


def test_replace_keywords_drops_deleted(tmp_path):
    base, md = _seed_table_with_keywords(tmp_path, ["recharge", "topup", "stale"])
    # user edits the list down to two — the deleted "stale" must NOT come back
    enrich_vault_table(
        base,
        "ws-test",
        TableEnrichment(table_name="FCT_K", keywords=["recharge", "topup"]),
        replace_keywords=True,
    )
    assert _kw(md) == ["recharge", "topup"]


def test_replace_keywords_empty_clears(tmp_path):
    base, md = _seed_table_with_keywords(tmp_path, ["a", "b"])
    enrich_vault_table(
        base,
        "ws-test",
        TableEnrichment(table_name="FCT_K", keywords=[]),
        replace_keywords=True,
    )
    assert _kw(md) == []


def test_enrichment_union_keeps_existing(tmp_path):
    # default (LLM/import) path must still UNION, never clobber curation
    base, md = _seed_table_with_keywords(tmp_path, ["recharge", "topup"])
    enrich_vault_table(
        base,
        "ws-test",
        TableEnrichment(table_name="FCT_K", keywords=["balance"]),
    )
    assert set(_kw(md)) == {"recharge", "topup", "balance"}
