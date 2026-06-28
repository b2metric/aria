#!/usr/bin/env python3
"""dedup-vault-sections.py — collapse duplicated vault sections.

Legacy enrichment appended new sections on every pass, leaving files with many
duplicate '## Column Descriptions' and '## /### (Manual) Relationships' blocks
(e.g. DIM_PREP_PRODUCTS had 12 relationship sections). This normalizes each
table file to AT MOST ONE of each:

- Column Descriptions: keep the single most-complete block (most non-empty
  `- **COL**: value` lines); drop the rest. The '## Columns' TABLE remains the
  source of truth.
- Relationships: MERGE every relationship bullet found across all
  '## Relationships' / '## Manual Relationships' / '### Manual Relationships'
  sections into ONE canonical '## Relationships' block, de-duplicated, dropping
  empty `` -> `.` bullets. No data is lost.
- Stale body placeholder: drop the legacy '**Description:** No description
  provided yet.' line. Frontmatter `description` is the single authority (the
  RAG pipeline reads frontmatter, not the body line), so the mirrored body line
  only ever drifted out of sync.

Everything else (Columns table, Keywords, Business Metadata scalar fields,
Domain Mapping, Example Queries, Sampled Values, frontmatter) is preserved.

This is the remediation counterpart to scripts/validate-vault.py (the contract).

Idempotent. Usage:  python3 scripts/dedup-vault-sections.py [workspace]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_HEADER_RE = re.compile(r"^(#{1,3})\s+(.*)$")


def _is_coldesc(title: str) -> bool:
    return title.strip().lower() == "column descriptions"


def _is_rel(title: str) -> bool:
    t = title.strip().lower()
    return t in ("relationships", "manual relationships")


def _split_blocks(lines: list[str]) -> list[tuple[str | None, list[str]]]:
    """Split into (header_line | None for preamble, body_lines incl. header)."""
    blocks: list[tuple[str | None, list[str]]] = []
    cur_header: str | None = None
    cur: list[str] = []
    for ln in lines:
        if _HEADER_RE.match(ln):
            if cur or cur_header is not None:
                blocks.append((cur_header, cur))
            cur_header = ln
            cur = [ln]
        else:
            cur.append(ln)
    if cur or cur_header is not None:
        blocks.append((cur_header, cur))
    return blocks


def _coldesc_score(body: list[str]) -> int:
    n = 0
    for ln in body:
        s = ln.strip()
        if s.startswith("- **") and "**:" in s and s.split("**:", 1)[1].strip():
            n += 1
    return n


def _rel_bullets(body: list[str]) -> list[str]:
    out = []
    for ln in body:
        s = ln.strip()
        if s.startswith("- ") and s != "- ":
            content = s[2:].strip()
            # drop empty/blank relationships like  `` -> `.`
            cleaned = content.replace("`", "").replace(" ", "")
            if content and cleaned not in ("→.", "->.", "→.(foreign_key)", "->.(foreign_key)"):
                out.append(content)
    return out


_STALE_DESC = "**Description:** No description provided yet."


def _strip_stale_desc(lines: list[str]) -> tuple[list[str], bool]:
    """Drop the legacy '**Description:** No description provided yet.' body line."""
    out = [ln for ln in lines if ln.strip() != _STALE_DESC]
    return out, len(out) != len(lines)


def _dedup_file(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").split("\n")
    lines, desc_fixed = _strip_stale_desc(lines)
    blocks = _split_blocks(lines)

    kept: list[tuple[str | None, list[str]]] = []
    coldesc_blocks: list[list[str]] = []
    rel_bullets: list[str] = []
    coldesc_count = 0
    rel_count = 0

    for header, body in blocks:
        if header is None:
            kept.append((header, body))
            continue
        m = _HEADER_RE.match(header)
        title = m.group(2) if m else ""
        if _is_coldesc(title):
            coldesc_blocks.append(body)
            coldesc_count += 1
            continue
        if _is_rel(title):
            rel_bullets.extend(_rel_bullets(body))
            rel_count += 1
            continue
        kept.append((header, body))

    # de-dup relationship bullets preserving order
    seen = set()
    uniq_rels = []
    for b in rel_bullets:
        if b not in seen:
            seen.add(b)
            uniq_rels.append(b)

    # nothing duplicated and nothing to normalize -> no change
    if coldesc_count <= 1 and rel_count <= 1 and not desc_fixed:
        return {"changed": False, "coldesc": coldesc_count, "rel_sections": rel_count}

    # rebuild
    out_lines: list[str] = []
    for _, body in kept:
        out_lines.extend(body)

    # append single canonical Column Descriptions (best block, normalized to h2)
    if coldesc_blocks:
        best = max(coldesc_blocks, key=_coldesc_score)
        bullets = [ln for ln in best if ln.strip().startswith("- **")]
        if bullets:
            out_lines.append("")
            out_lines.append("## Column Descriptions")
            out_lines.append("")
            out_lines.extend(bullets)
    # append single canonical Relationships
    if uniq_rels:
        out_lines.append("")
        out_lines.append("## Relationships")
        out_lines.append("")
        out_lines.extend(f"- {b}" for b in uniq_rels)

    # collapse 3+ blank lines
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(out_lines)).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")
    return {
        "changed": True,
        "coldesc": coldesc_count,
        "rel_sections": rel_count,
        "rels_kept": len(uniq_rels),
        "desc_fixed": desc_fixed,
    }


def main() -> int:
    ws = sys.argv[1] if len(sys.argv) > 1 else "stc-kuwait"
    tables_dir = REPO / "docs" / "vaults" / ws / "tables"
    if not tables_dir.exists():
        print(f"not found: {tables_dir}")
        return 1
    changed = 0
    for md in sorted(tables_dir.glob("*.md")):
        r = _dedup_file(md)
        if r["changed"]:
            changed += 1
            print(f"  fixed  {md.name:30s} coldesc {r['coldesc']}->1  rel_sections {r['rel_sections']}->{'1' if r.get('rels_kept') else '0'} ({r.get('rels_kept',0)} rels)")
        else:
            print(f"  ok     {md.name:30s} coldesc {r['coldesc']} rel {r['rel_sections']}")
    print(f"\n{changed} file(s) normalized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
