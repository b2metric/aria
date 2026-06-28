#!/usr/bin/env python3
"""validate-vault.py — enforce the ARIA vault schema contract.

The vault is ARIA's semantic layer (see docs/vault-format-analysis.md). This is
the CONTRACT that keeps it from drifting back into the duplicated/stale mess
(multiple Column Descriptions, stale "No description provided yet", empty
relationships). Run in CI (blocking) and locally.

Pure stdlib (no PyYAML) so the CI job needs no install step.

Per table file (docs/vaults/<ws>/tables/*.md) it checks:

ERRORS (exit 1 — block):
- frontmatter present with structural keys: table, database, workspace
  (corruption blocks; an *absent* description is a completeness WARN — see below —
  because the sync→enrich lifecycle creates skeletons before they are described)
- a non-empty '## Columns' markdown table
- NO duplicate canonical sections (Columns, Column Descriptions, Relationships /
  Manual Relationships, Business Metadata, Domain Mapping, Example Queries,
  Sampled Values, Keywords)
- NO drift placeholder ("No description provided yet.") when frontmatter has a
  real description
- every '### Q:' example has a ```sql fence
- NO empty relationship bullets (`` -> `.`)

WARNINGS (reported; fail only with --strict):
- frontmatter 'description' missing/empty (table synced but not yet enriched)
- frontmatter 'keywords' missing/empty
- a redundant empty '## Keywords' body section (keywords live in frontmatter)
- columns with blank descriptions (metadata gap; count)

Usage:
    python3 scripts/validate-vault.py [--workspace stc-kuwait] [--strict]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VAULTS = REPO / "docs" / "vaults"

REQUIRED_FM = ("table", "database", "workspace")  # structural identity → ERROR if missing
_HEADER_RE = re.compile(r"^#{1,3}\s+(.*?)\s*$")


def _canonical_section(title: str) -> str | None:
    """Map a header title to its canonical section name (or None if not tracked)."""
    t = title.strip().lower()
    mapping = {
        "columns": "Columns",
        "column descriptions": "Column Descriptions",
        "relationships": "Relationships",
        "manual relationships": "Relationships",
        "business metadata": "Business Metadata",
        "domain mapping": "Domain Mapping",
        "example queries": "Example Queries",
        "sampled values": "Sampled Values",
        "keywords": "Keywords",
    }
    return mapping.get(t)


def _frontmatter(text: str) -> dict[str, str] | None:
    """Minimal top-level YAML frontmatter parse (no nested structures)."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm: dict[str, str] = {}
    for line in text[3:end].split("\n"):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def _validate_file(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # ── frontmatter ──
    fm = _frontmatter(text)
    if fm is None:
        errors.append("missing YAML frontmatter")
        fm = {}
    for key in REQUIRED_FM:
        if not fm.get(key):
            errors.append(f"frontmatter missing required key '{key}'")
    if not fm.get("description"):
        warnings.append("frontmatter 'description' is empty (table not yet enriched)")
    if not fm.get("keywords") or fm.get("keywords") in ("[]", ""):
        warnings.append("frontmatter 'keywords' is empty")

    # ── section counts + duplicate detection ──
    section_counts: dict[str, int] = {}
    for ln in lines:
        m = _HEADER_RE.match(ln)
        if m:
            canon = _canonical_section(m.group(1))
            if canon:
                section_counts[canon] = section_counts.get(canon, 0) + 1
    for canon, n in sorted(section_counts.items()):
        if n > 1:
            errors.append(f"duplicate section '{canon}' appears {n}× (must be ≤1)")

    # ── Columns table present + non-empty ──
    if section_counts.get("Columns", 0) == 0:
        errors.append("missing '## Columns' section")
    else:
        col_rows = [
            ln for ln in lines
            if ln.strip().startswith("|")
            and not ln.strip().startswith("| Column")
            and not ln.strip().lstrip("|").lstrip().startswith("---")
        ]
        if not col_rows:
            errors.append("'## Columns' table has no data rows")
        else:
            blank = 0
            for row in col_rows:
                cells = [p.strip() for p in row.strip().strip("|").split("|")]
                if len(cells) >= 5 and not cells[4]:
                    blank += 1
            if blank:
                warnings.append(f"{blank} column(s) have no description")

    # ── drift placeholder ──
    if fm.get("description") and "No description provided yet." in text:
        errors.append(
            "stale '**Description:** No description provided yet.' while "
            "frontmatter has a real description"
        )

    # ── redundant empty Keywords body section ──
    if section_counts.get("Keywords", 0) >= 1:
        warnings.append("redundant '## Keywords' body section (keywords live in frontmatter)")

    # ── empty relationship bullets ──
    for ln in lines:
        s = ln.strip()
        if s.startswith("- "):
            stripped = s[2:].replace("`", "").replace(" ", "")
            if stripped in ("→.", "->.", "→.(foreign_key)", "->.(foreign_key)"):
                errors.append("empty relationship bullet (`` → `.`)")
                break

    # ── example queries each have a sql fence ──
    eqm = re.search(
        r"^## Example Queries\s*\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE
    )
    if eqm:
        for q in re.finditer(
            r"^###\s*Q:\s*(.+?)\s*\n(.*?)(?=^###\s*Q:|\Z)",
            eqm.group(1),
            re.DOTALL | re.MULTILINE,
        ):
            if "```" not in q.group(2):
                errors.append(f"example query '{q.group(1)[:40]}' has no SQL code block")

    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate ARIA vault markdown against the schema contract.")
    ap.add_argument("--workspace", help="validate a single workspace (default: all)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args()

    if not VAULTS.exists():
        print(f"no vaults dir: {VAULTS}")
        return 0

    workspaces = (
        [VAULTS / args.workspace]
        if args.workspace
        else sorted(p for p in VAULTS.iterdir() if p.is_dir())
    )

    total_err = total_warn = total_files = 0
    for ws in workspaces:
        tables = ws / "tables"
        if not tables.exists():
            continue
        for md in sorted(tables.glob("*.md")):
            total_files += 1
            errs, warns = _validate_file(md)
            total_err += len(errs)
            total_warn += len(warns)
            if errs or warns:
                print(f"\n{ws.name}/{md.name}")
                for e in errs:
                    print(f"  ✗ ERROR: {e}")
                for w in warns:
                    print(f"  ⚠ warn:  {w}")

    print(
        f"\nvalidated {total_files} table file(s): "
        f"{total_err} error(s), {total_warn} warning(s)"
    )
    if total_err or (args.strict and total_warn):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
