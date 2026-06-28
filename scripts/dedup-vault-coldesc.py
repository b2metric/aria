#!/usr/bin/env python3
"""dedup-vault-coldesc.py — collapse duplicate '## Column Descriptions' blocks.

Legacy STC onboarding enrichment appended a new '## Column Descriptions' (h2)
section on every pass (empty template + Turkish + English + re-runs), stacking
up to 8 duplicate blocks per vault file. They bloat the file and the Qdrant
embedding (the whole md is embedded) with redundant noise.

This keeps the SINGLE most-complete '## Column Descriptions' (h2) block — the one
with the most non-empty `- **COL**: text` entries (ties → the last, usually the
English pass) — and removes the rest. Everything else (the '## Columns' table,
Keywords, '## Business Metadata' + its '### Column Descriptions', Domain Mapping,
Example Queries, Sampled Values) is untouched.

Idempotent: a file with 0 or 1 such block is left unchanged.

Usage:
    python3 scripts/dedup-vault-coldesc.py [workspace]   # default: stc-kuwait
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HEADER = "## Column Descriptions"


def _entry_score(block_lines: list[str]) -> int:
    """Count non-empty `- **COL**: value` lines in a block."""
    score = 0
    for ln in block_lines:
        s = ln.strip()
        if s.startswith("- **") and "**:" in s:
            value = s.split("**:", 1)[1].strip()
            if value:
                score += 1
    return score


def _dedup_file(path: Path) -> tuple[bool, int, int]:
    """Return (changed, blocks_before, kept_index)."""
    lines = path.read_text(encoding="utf-8").split("\n")

    # Find h2 '## Column Descriptions' block spans: [start, end) up to next '## ' (h2).
    blocks: list[tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        if lines[i].strip() == HEADER:
            start = i
            j = i + 1
            while j < n and not lines[j].startswith("## "):
                j += 1
            blocks.append((start, j))
            i = j
        else:
            i += 1

    if len(blocks) <= 1:
        return (False, len(blocks), 0)

    # Pick the best block: max non-empty entries, tie -> last.
    best_idx = 0
    best_score = -1
    for idx, (s, e) in enumerate(blocks):
        sc = _entry_score(lines[s:e])
        if sc >= best_score:  # >= so ties prefer the later (English) block
            best_score = sc
            best_idx = idx

    drop_ranges = [rng for k, rng in enumerate(blocks) if k != best_idx]
    drop = set()
    for s, e in drop_ranges:
        drop.update(range(s, e))

    new_lines = [ln for k, ln in enumerate(lines) if k not in drop]
    # collapse 3+ consecutive blank lines left behind into max 2
    cleaned: list[str] = []
    blank = 0
    for ln in new_lines:
        if ln.strip() == "":
            blank += 1
            if blank > 2:
                continue
        else:
            blank = 0
        cleaned.append(ln)

    path.write_text("\n".join(cleaned), encoding="utf-8")
    return (True, len(blocks), best_idx)


def main() -> int:
    workspace = sys.argv[1] if len(sys.argv) > 1 else "stc-kuwait"
    tables_dir = REPO / "docs" / "vaults" / workspace / "tables"
    if not tables_dir.exists():
        print(f"not found: {tables_dir}")
        return 1
    total_changed = 0
    for md in sorted(tables_dir.glob("*.md")):
        changed, before, kept = _dedup_file(md)
        if changed:
            total_changed += 1
            print(f"  fixed  {md.name:32s} {before} blocks -> 1 (kept #{kept + 1})")
        else:
            print(f"  ok     {md.name:32s} {before} block(s)")
    print(f"\n{total_changed} file(s) de-duplicated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
