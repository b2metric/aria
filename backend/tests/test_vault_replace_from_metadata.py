"""Unit tests for scripts/vault-replace-from-metadata.py.

Verifies the rebuild refreshes structure (dtypes / enums / dropped columns) while
preserving curated content (frontmatter description, per-column descriptions, and
the ## Example Queries section), and that the output passes validate-vault.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "vault_replace_from_metadata", _REPO / "scripts" / "vault-replace-from-metadata.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


mod = _load_script()

_EXISTING_MD = """---
table: FCT_PREP_REV
database: oracle
workspace: stc-kuwait
keywords: [revenue, billing]
description: "Curated revenue fact table"
enriched_at: 2026-06-01T00:00:00
---

# FCT_PREP_REV

## Columns

| Column | Type | Nullable | PK | Description |
|--------|------|----------|----|-----------—|
| CONTRNO | NUMBER | ✗ | ✓ | Contract number (curated) |
| OLDCOL | VARCHAR2 | ✓ |  | to be dropped |

## Example Queries

### Q: Total revenue this month
Sums the billed amount.
```sql
SELECT SUM(BILLAMOUNT) FROM FCT_PREP_REV
```
"""


def _new_meta():
    # CONTRNO dtype changed NUMBER -> NUMBER(18); OLDCOL dropped; NEWCOL added.
    return {
        "table_name": "FCT_PREP_REV",
        "description": None,  # importer/replacer must NOT clobber curated desc
        "row_count": 999,
        "columns": [
            {"name": "CONTRNO", "data_type": "NUMBER(18)", "nullable": False, "is_pk": True},
            {"name": "NEWCOL", "data_type": "VARCHAR2", "nullable": True, "is_pk": False},
        ],
        "relationships": [],
        "enum_values": {"NEWCOL": ["Bundles", "Data", "Voice"]},
    }


def test_build_markdown_refreshes_dtype_and_preserves_curation(tmp_path):
    existing = tmp_path / "fct_prep_rev.md"
    existing.write_text(_EXISTING_MD, encoding="utf-8")
    preserved = mod.preserve_from_existing(existing)

    md = mod.build_markdown(_new_meta(), preserved, "stc-kuwait", "oracle")

    # fresh dtype landed
    assert "NUMBER(18)" in md
    # curated frontmatter description preserved
    assert "Curated revenue fact table" in md
    # curated per-column description carried into the rebuilt Columns table
    assert "Contract number (curated)" in md
    # curated Example Queries preserved verbatim
    assert "## Example Queries" in md
    assert "SELECT SUM(BILLAMOUNT)" in md
    # dropped column gone, new column present
    assert "OLDCOL" not in md
    assert "NEWCOL" in md


def test_preserve_returns_empty_for_missing_file(tmp_path):
    preserved = mod.preserve_from_existing(tmp_path / "nope.md")
    assert preserved["exists"] is False
    assert preserved["col_desc"] == {}
    assert preserved["sections"] == ""


def test_build_markdown_new_table_uses_generated_description(tmp_path):
    preserved = mod.preserve_from_existing(tmp_path / "missing.md")
    md = mod.build_markdown(_new_meta(), preserved, "stc-kuwait", "oracle")
    # brand-new table: no curated desc, but a non-empty generated one + structure
    assert "description:" in md
    assert "NUMBER(18)" in md
    assert "NEWCOL" in md


def test_replace_table_writes_enum_block_and_passes_validate(tmp_path):
    vault_dir = tmp_path / "docs" / "vaults" / "stc-kuwait" / "tables"
    vault_dir.mkdir(parents=True)
    (vault_dir / "fct_prep_rev.md").write_text(_EXISTING_MD, encoding="utf-8")

    target = tmp_path / "preview"
    result = mod.replace_table(_new_meta(), vault_dir, "stc-kuwait", "oracle", target)

    assert result["was_existing"] is True
    assert result["preserved_description"] is True
    assert result["preserved_sections"] is True
    # both old col descriptions are captured; OLDCOL's is simply unused (dropped)
    assert result["preserved_column_descs"] == 2

    out = target / result["file"]
    text = out.read_text(encoding="utf-8")
    # enum block injected with the FRESH values (the "Bundles not Bundle" fix)
    assert "## Sampled Values" in text
    assert "`Bundles`" in text
    assert "NUMBER(18)" in text

    # the produced file must satisfy the vault schema contract
    rc = mod._validate([out])
    assert rc == 0, "validate-vault.py flagged the rebuilt file"
