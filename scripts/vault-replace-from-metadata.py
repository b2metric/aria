#!/usr/bin/env python3
"""vault-replace-from-metadata.py — rebuild a vault from a fresh Oracle snapshot.

Companion to ``scripts/vault-extract-remote.py``. Runs INSIDE the ARIA repo
(needs the backend importable + the vault files on disk). For each table in the
extraction JSON it REBUILDS the structural parts of the table's vault markdown
from the fresh metadata — the ``## Columns`` table (dtypes / nullable / PK), the
``## Relationships`` (from fresh FKs), and the ``## Sampled Values`` enum block —
while PRESERVING the curated, human/LLM-authored content:

  - frontmatter ``description``, ``keywords``, ``business_name``, ``data_domain``
  - per-column descriptions (matched by column name, carried into the new table)
  - the ``## Example Queries``, ``## Domain Mapping`` and ``## Business Metadata``
    sections (verbatim)
  - ``join_keys.json`` is never touched

Why this exists (and why not just POST to /vault/import-metadata): the API import
path is additive — for a table that ALREADY has a vault file it refreshes enums +
descriptions but does NOT replace column dtypes (``ColumnEnrichment`` doesn't even
carry a data_type). This script does the true "replace structure, keep curation".

Dropped columns (present in the old vault, absent from the fresh pull) disappear;
new columns appear. Sample rows in the JSON are ignored (never written to a vault).

Usage (from the repo root):
    uv run python scripts/vault-replace-from-metadata.py \
        --workspace stc-kuwait --json db-metadata-commbi_prod-20260701-1200.json
    # ^ dry-run by default: writes rebuilt files to ./vault-preview/ for review.

    uv run python scripts/vault-replace-from-metadata.py \
        --workspace stc-kuwait --json <file> --apply --validate
    # ^ overwrites the live vault files in place, then runs validate-vault.py.

Exit codes: 0 = ok; 1 = config error; 2 = one or more tables failed / validation
errors.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("vault-replace")

# Curated body sections preserved verbatim across a rebuild.
_PRESERVE_SECTIONS = ["Example Queries", "Domain Mapping", "Business Metadata"]


def _split_frontmatter(md: str) -> tuple[dict[str, Any], str]:
    import yaml

    if md.startswith("---"):
        parts = md.split("---", 2)
        if len(parts) >= 3:
            return yaml.safe_load(parts[1].strip()) or {}, parts[2].strip()
    return {}, md


def _join_frontmatter(frontmatter: dict[str, Any], body: str) -> str:
    import yaml

    def list_representer(dumper, data):
        if all(isinstance(item, str) for item in data):
            return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)
        return dumper.represent_sequence("tag:yaml.org,2002:seq", data)

    yaml.add_representer(list, list_representer)
    fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm_str}---\n\n{body.strip()}\n"


def preserve_from_existing(path: Path) -> dict[str, Any]:
    """Extract the curated content to carry across a rebuild. Empty dict-ish
    result when the file does not exist (brand-new table)."""
    from backend.app.services.vault_md import parse_vault_file, read_sections

    if not path.exists():
        return {"exists": False, "col_desc": {}, "sections": ""}

    parsed = parse_vault_file(path)
    col_desc = {
        c["name"].upper(): c["description"]
        for c in parsed.get("columns", [])
        if c.get("description")
    }
    return {
        "exists": True,
        "description": parsed.get("description"),
        "keywords": parsed.get("keywords") or [],
        "business_name": parsed.get("business_name"),
        "data_domain": parsed.get("data_domain"),
        "enriched_at": parsed.get("enriched_at"),
        "col_desc": col_desc,
        "sections": read_sections(path, _PRESERVE_SECTIONS),
    }


def _table_info_from_meta(meta: dict, col_desc: dict[str, str]) -> Any:
    """Build a schema_discovery TableInfo from an extraction-JSON table entry,
    injecting preserved per-column descriptions as ColumnInfo.comment so the
    regenerated Columns table keeps them."""
    from backend.app.schema_discovery.models import ColumnInfo, ForeignKeyInfo, TableInfo

    columns = [
        ColumnInfo(
            name=c["name"],
            data_type=c.get("data_type", "UNKNOWN"),
            nullable=bool(c.get("nullable", True)),
            is_primary_key=bool(c.get("is_pk", False)),
            comment=col_desc.get(c["name"].upper()),
        )
        for c in meta.get("columns", [])
    ]
    fks = [
        ForeignKeyInfo(
            source_table=meta["table_name"],
            source_column=r["source_column"],
            target_table=r["target_table"],
            target_column=r["target_column"],
            constraint_name=r.get("constraint_name"),
        )
        for r in meta.get("relationships", [])
        if r.get("relationship_type", "foreign_key") == "foreign_key"
    ]
    return TableInfo(
        name=meta["table_name"],
        columns=columns,
        foreign_keys=fks,
        row_count_estimate=meta.get("row_count"),
    )


def build_markdown(meta: dict, preserved: dict, workspace_id: str, db_type: str) -> str:
    """Regenerate a table's vault markdown: fresh structure + preserved curation.
    (Enum block is injected separately, on the written file.)"""
    from backend.app.schema_discovery.vault_generator import generate_table_markdown

    table = _table_info_from_meta(meta, preserved.get("col_desc", {}))
    base = generate_table_markdown(table, workspace_id=workspace_id, db_type=db_type)

    fm, body = _split_frontmatter(base)
    # Restore curated frontmatter (only when the old file actually had it).
    if preserved.get("description"):
        fm["description"] = preserved["description"]
    if preserved.get("keywords"):
        fm["keywords"] = preserved["keywords"]
    if preserved.get("business_name"):
        fm["business_name"] = preserved["business_name"]
    if preserved.get("data_domain"):
        fm["data_domain"] = preserved["data_domain"]
    if preserved.get("enriched_at"):
        fm["enriched_at"] = preserved["enriched_at"]

    md = _join_frontmatter(fm, body)

    sections = (preserved.get("sections") or "").strip()
    if sections:
        md = md.rstrip() + "\n\n" + sections + "\n"
    return md


def replace_table(
    meta: dict, vault_dir: Path, workspace_id: str, db_type: str, target_dir: Path
) -> dict:
    """Rebuild one table's file into ``target_dir`` (which may be the live vault
    dir for --apply or a preview dir). Returns a per-table result dict."""
    from backend.app.services.vault_enum_sampler import inject_enum_block
    from backend.app.services.vault_md import resolve_vault_file

    table_name = meta["table_name"]
    existing = resolve_vault_file(vault_dir, table_name)
    preserved = preserve_from_existing(existing)

    md = build_markdown(meta, preserved, workspace_id, db_type)

    # Keep the existing filename/casing when the file exists; else lowercase.
    out_name = existing.name if preserved.get("exists") else f"{table_name.lower()}.md"
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / out_name
    out_path.write_text(md, encoding="utf-8")

    enums = meta.get("enum_values") or {}
    if enums:
        inject_enum_block(out_path, enums)

    return {
        "table": table_name,
        "file": out_path.name,
        "was_existing": preserved.get("exists", False),
        "preserved_description": bool(preserved.get("description")),
        "preserved_sections": bool((preserved.get("sections") or "").strip()),
        "preserved_column_descs": len(preserved.get("col_desc", {})),
        "columns": len(meta.get("columns", [])),
        "enum_columns": len(enums),
    }


def _validate(paths: list[Path]) -> int:
    """Run the vault schema contract (scripts/validate-vault.py::_validate_file)
    over the produced files. Returns 1 if any file has ERRORS, else 0."""
    validator = _REPO / "scripts" / "validate-vault.py"
    if not validator.exists():
        logger.warning("validate-vault.py not found — skipping validation.")
        return 0
    spec = importlib.util.spec_from_file_location("validate_vault", validator)
    if not (spec and spec.loader):
        return 0
    vv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vv)

    total_err = 0
    for p in paths:
        errs, warns = vv._validate_file(p)
        total_err += len(errs)
        if errs or warns:
            logger.info("validate %s — %d error(s), %d warning(s)", p.name, len(errs), len(warns))
            for e in errs:
                logger.error("  ✗ %s", e)
            for w in warns:
                logger.info("  ⚠ %s", w)
    return 1 if total_err else 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Rebuild a vault from a fresh Oracle metadata snapshot."
    )
    p.add_argument("--workspace", required=True, help="Workspace/tenant slug, e.g. stc-kuwait")
    p.add_argument("--json", required=True, help="Extraction JSON from vault-extract-remote.py")
    p.add_argument("--vault-root", default="docs/vaults",
                   help="Vault base path (default docs/vaults)")
    p.add_argument("--apply", action="store_true",
                   help="Overwrite live vault files (default: dry-run into --preview-dir)")
    p.add_argument("--preview-dir", default="vault-preview",
                   help="Where dry-run rebuilt files are written")
    p.add_argument("--only", help="Comma-separated subset of tables to rebuild")
    p.add_argument("--validate", action="store_true",
                   help="Run scripts/validate-vault.py on the produced files")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    json_path = Path(args.json)
    if not json_path.exists():
        logger.error("JSON not found: %s", json_path)
        return 1
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    db_type = payload.get("db_type", "oracle")
    tables = payload.get("tables", [])
    if not tables:
        logger.error("No tables in %s", json_path)
        return 1

    only = {t.strip().upper() for t in args.only.split(",")} if args.only else None
    if only:
        tables = [t for t in tables if t["table_name"].upper() in only]

    vault_dir = Path(args.vault_root) / args.workspace / "tables"
    if not vault_dir.exists() and args.apply:
        logger.error("Vault dir does not exist: %s", vault_dir)
        return 1

    target_dir = vault_dir if args.apply else Path(args.preview_dir)
    mode = "APPLY (in place)" if args.apply else f"DRY-RUN → {target_dir}"
    logger.info("Rebuilding %d tables for '%s' [%s]", len(tables), args.workspace, mode)

    results: list[dict] = []
    produced: list[Path] = []
    failures = 0
    for meta in tables:
        try:
            r = replace_table(meta, vault_dir, args.workspace, db_type, target_dir)
            results.append(r)
            produced.append(target_dir / r["file"])
            logger.info(
                "  %-24s cols=%-3d enums=%-2d desc=%s sections=%s col_desc=%d%s",
                r["table"], r["columns"], r["enum_columns"],
                "Y" if r["preserved_description"] else "-",
                "Y" if r["preserved_sections"] else "-",
                r["preserved_column_descs"],
                "" if r["was_existing"] else "  (NEW)",
            )
        except Exception as e:  # noqa: BLE001
            failures += 1
            logger.error("  %-24s FAILED: %s", meta.get("table_name"), e)

    rc = 0
    if args.validate and produced:
        rc = _validate(produced)

    logger.info(
        "Done: %d rebuilt, %d failed. %s",
        len(results), failures,
        "Applied in place." if args.apply
        else f"Review {target_dir}, then re-run with --apply.",
    )
    if args.apply:
        logger.info(
            "Remember to re-index Qdrant: POST /api/workspaces/vault/reindex "
            "(or restart backend) so retrieval picks up the changes."
        )
    return 2 if (failures or rc) else 0


if __name__ == "__main__":
    sys.exit(main())
