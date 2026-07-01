#!/usr/bin/env python3
"""vault-build-stc-from-snapshot.py — build a vault FROM SCRATCH.

Unlike vault-replace-from-metadata.py (which preserves the existing vault's
curated descriptions + Example Queries), this builds each table's markdown fresh
from a remote-extraction snapshot JSON + column descriptions taken from an Excel
workbook (Book2.xlsx: one sheet per table, col A = column name, col B = description).

It intentionally writes NO ## Example Queries / ## Domain Mapping — a clean slate.
Enum blocks come from the snapshot's enum_values. Column descriptions come from the
Excel; columns absent from the Excel fall back to generate_table_markdown's heuristic.

    uv run --with openpyxl python scripts/vault-build-stc-from-snapshot.py \
        --workspace stc-kuwait \
        --json vault-rebuild-bundle/scripts/stc-vault-snapshot/db-metadata-*.json \
        --excel tmp/Book2.xlsx --apply

Dry-run (default) writes to ./vault-preview/; --apply writes the live vault dir and
removes stale lowercase duplicates.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def load_excel_descriptions(xlsx: Path) -> dict[str, dict[str, str]]:
    """{TABLE_UPPER: {COLUMN_UPPER: description}} from a per-table-sheet workbook."""
    import openpyxl

    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    out: dict[str, dict[str, str]] = {}
    for ws in wb.worksheets:
        cols: dict[str, str] = {}
        for row in ws.iter_rows(values_only=True):
            if not row or row[0] is None:
                continue
            name = str(row[0]).strip()
            if not name:
                continue
            desc = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            if desc:
                cols[name.upper()] = desc
        if cols:
            out[ws.title.strip().upper()] = cols
    return out


def build_one(meta: dict, col_desc: dict[str, str], workspace: str, db_type: str) -> str:
    from backend.app.schema_discovery.models import ColumnInfo, ForeignKeyInfo, TableInfo
    from backend.app.schema_discovery.vault_generator import generate_table_markdown

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
    ]
    table = TableInfo(
        name=meta["table_name"], columns=columns, foreign_keys=fks,
        row_count_estimate=meta.get("row_count"),
    )
    return generate_table_markdown(table, workspace_id=workspace, db_type=db_type)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Build a vault from scratch (snapshot + Excel descriptions)."
    )
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--json", required=True, help="extraction snapshot JSON (globs ok)")
    ap.add_argument("--excel", required=True, help="Book2.xlsx with per-table description sheets")
    ap.add_argument("--vault-root", default="docs/vaults")
    ap.add_argument("--apply", action="store_true", help="write live vault dir (else ./vault-preview)")
    ap.add_argument("--preview-dir", default="vault-preview")
    args = ap.parse_args(argv)

    from backend.app.services.vault_enum_sampler import inject_enum_block

    matches = glob.glob(args.json)
    if not matches:
        print(f"no JSON match: {args.json}", file=sys.stderr)
        return 1
    payload = json.loads(Path(sorted(matches)[-1]).read_text(encoding="utf-8"))
    db_type = payload.get("db_type", "oracle")
    tables = payload.get("tables", [])

    descriptions = load_excel_descriptions(Path(args.excel))

    live_dir = Path(args.vault_root) / args.workspace / "tables"
    target = live_dir if args.apply else Path(args.preview_dir)
    target.mkdir(parents=True, exist_ok=True)

    written = 0
    for meta in tables:
        tbl = meta["table_name"]
        col_desc = descriptions.get(tbl.upper(), {})
        md = build_one(meta, col_desc, args.workspace, db_type)
        out = target / f"{tbl.upper()}.md"  # consistent uppercase filename
        out.write_text(md, encoding="utf-8")
        enums = meta.get("enum_values") or {}
        if enums:
            inject_enum_block(out, enums)
        written += 1
        print(f"  {tbl:24} cols={len(meta.get('columns', [])):3} enums={len(enums):2} "
              f"desc={len(col_desc):3}")

    # Remove a stale lowercase duplicate when applying (fct_prep_master_hist.md).
    if args.apply:
        for meta in tables:
            up = live_dir / f"{meta['table_name'].upper()}.md"
            low = live_dir / f"{meta['table_name'].lower()}.md"
            # Guard for case-insensitive filesystems (macOS): up and low resolve to the
            # SAME inode there — unlinking would delete the file we just wrote.
            if (
                low.exists() and up.exists() and low.name != up.name
                and not low.samefile(up)
            ):
                low.unlink()
                print(f"  removed stale duplicate {low.name}")

    print(f"built {written} table file(s) → {target}" + ("" if args.apply else " (dry-run)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
