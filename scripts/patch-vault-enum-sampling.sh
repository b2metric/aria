#!/usr/bin/env bash
# patch-vault-enum-sampling.sh — add live DISTINCT-value sampling to vault sync.
#
# Adds a new module backend/app/services/vault_enum_sampler.py and rewires
# VaultSyncService.sync() to call it. After this, "resync vault" populates
# each table's markdown with the REAL enum values (e.g. "Bundles" instead of
# the handcrafted "Bundle") so the LLM stops emitting zero-row queries.
#
# Idempotent: re-running is a no-op once both edits are in place.
# Run from the repo root (~/projects/b2metric-aria by default).
#
# Usage:
#   bash scripts/patch-vault-enum-sampling.sh
#   docker compose -f docker-compose.dev.yml restart backend
#   # then in the ARIA admin UI: workspaces → STC → Resync Vault
#
# Tune (optional, set in backend/.env):
#   ARIA_VAULT_MAX_ENUM_CARDINALITY=50    # default: skip cols with >50 distinct
#   ARIA_VAULT_ENUM_SKIP=1                # disable sampling entirely

set -euo pipefail

REPO_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
SAMPLER="$REPO_DIR/backend/app/services/vault_enum_sampler.py"
SYNC="$REPO_DIR/backend/app/services/vault_sync.py"

log() { printf '\033[36m[patch]\033[0m %s\n' "$*"; }
ok()  { printf '\033[32m[patch]\033[0m %s\n' "$*"; }
die() { printf '\033[31m[patch]\033[0m %s\n' "$*" >&2; exit 1; }

[[ -f "$SYNC" ]] || die "not found: $SYNC  (run from repo root or pass repo dir as arg)"

# --- Part 1: create the new sampler module (if missing) ---------------------
if [[ -f "$SAMPLER" ]] && grep -q 'def sample_enum_values' "$SAMPLER" 2>/dev/null; then
  log "sampler module already exists, skipping create"
else
  log "creating $SAMPLER"
  cat > "$SAMPLER" <<'PYEOF'
"""Vault enum-value sampler.

Live-samples DISTINCT values for low-cardinality VARCHAR/CHAR columns and
injects them into the table's vault markdown as a sentinel-fenced block.
This closes the gap where vault descriptions list plausible-but-wrong enum
values (e.g. "Bundle" while the DB actually has "Bundles") that cause the
LLM to emit zero-row queries.

Called from VaultSync.sync() after _fetch_live_schema().

Tunables (env):
- ARIA_VAULT_MAX_ENUM_CARDINALITY  (default 50) — columns with more distinct
  values than this are skipped (not enum-like).
- ARIA_VAULT_ENUM_SKIP             (default 0)  — set to 1 to disable sampling.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ENUM_BLOCK_START = "<!-- ARIA:ENUM-VALUES-START -->"
ENUM_BLOCK_END = "<!-- ARIA:ENUM-VALUES-END -->"

_VARCHAR_PREFIXES = ("VARCHAR", "CHAR", "NVARCHAR", "NCHAR", "TEXT", "STRING")


def _is_varchar(dtype: str | None) -> bool:
    t = (dtype or "").upper()
    return any(t.startswith(p) for p in _VARCHAR_PREFIXES)


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


async def sample_enum_values(
    db_config: Any,
    live_tables: dict[str, list[dict]],
    max_cardinality: int | None = None,
) -> dict[str, dict[str, list[str]]]:
    if os.environ.get("ARIA_VAULT_ENUM_SKIP") == "1":
        logger.info("Enum sampling disabled (ARIA_VAULT_ENUM_SKIP=1)")
        return {}

    if max_cardinality is None:
        try:
            max_cardinality = int(os.environ.get("ARIA_VAULT_MAX_ENUM_CARDINALITY", "50"))
        except ValueError:
            max_cardinality = 50

    from backend.app.db.executor import get_executor

    executor = get_executor(db_config)
    loop = asyncio.get_event_loop()
    out: dict[str, dict[str, list[str]]] = {}

    for table_name, cols in live_tables.items():
        varchar_cols = [c for c in cols if _is_varchar(c.get("type"))]
        if not varchar_cols:
            continue
        for col in varchar_cols:
            col_name = col["name"]
            try:
                count_sql = (
                    f"SELECT COUNT(DISTINCT {_quote_ident(col_name)}) AS C "
                    f"FROM {_quote_ident(table_name)}"
                )
                rows = await loop.run_in_executor(
                    None, lambda s=count_sql: executor.execute(s, {})
                )
                if not rows:
                    continue
                count_val = next(iter(rows[0].values()))
                if count_val is None:
                    continue
                count_int = int(count_val)
                if count_int == 0 or count_int > max_cardinality:
                    continue

                distinct_sql = (
                    f"SELECT DISTINCT {_quote_ident(col_name)} AS V "
                    f"FROM {_quote_ident(table_name)} "
                    f"WHERE {_quote_ident(col_name)} IS NOT NULL "
                    f"FETCH FIRST {max_cardinality} ROWS ONLY"
                )
                drows = await loop.run_in_executor(
                    None, lambda s=distinct_sql: executor.execute(s, {})
                )
                values = sorted({
                    str(next(iter(r.values()))).strip()
                    for r in drows
                    if r and next(iter(r.values()), None) is not None
                })
                if values:
                    out.setdefault(table_name, {})[col_name] = values
                    logger.info(
                        "sampled %d enum values for %s.%s",
                        len(values), table_name, col_name,
                    )
            except Exception as e:
                logger.warning(
                    "enum sample failed for %s.%s: %s", table_name, col_name, e
                )
                continue

    return out


def inject_enum_block(file_path: Path, table_enums: dict[str, list[str]]) -> bool:
    if not table_enums:
        return False

    file_path = Path(file_path)
    if not file_path.exists():
        return False

    now_str = datetime.now(UTC).isoformat()
    lines = [
        ENUM_BLOCK_START,
        "",
        "## Sampled Values",
        f"*Auto-updated by vault sync. Last sampled: {now_str}*",
        "",
    ]
    for col, values in sorted(table_enums.items()):
        rendered = ", ".join(f"`{v}`" for v in values)
        lines.append(f"- **{col}**: {rendered}")
    lines.extend(["", ENUM_BLOCK_END])
    new_block = "\n".join(lines)

    content = file_path.read_text()
    block_re = re.compile(
        re.escape(ENUM_BLOCK_START) + r".*?" + re.escape(ENUM_BLOCK_END),
        re.DOTALL,
    )
    existing = block_re.search(content)

    def normalize(block: str) -> str:
        return re.sub(r"\*Auto-updated by vault sync\. Last sampled: [^*]+\*", "", block)

    if existing:
        if normalize(existing.group(0)) == normalize(new_block):
            return False
        new_content = block_re.sub(new_block, content, count=1)
    else:
        new_content = content.rstrip() + "\n\n" + new_block + "\n"

    file_path.write_text(new_content)
    return True
PYEOF
  ok "created sampler module"
fi

# --- Part 2: rewire VaultSyncService.sync() (idempotent) --------------------
python3 - "$SYNC" <<'PYEOF'
import sys, pathlib

OLD = '''    async def sync(self) -> dict:
        """Run the full synchronization process."""
        logger.info("Starting vault sync for workspace %s", self.workspace_id)

        # 1. Fetch live DB schema
        live_tables = await self._fetch_live_schema()

        # 2. Parse existing markdown files
        existing_tables = self._read_existing_vault()

        stats = {"added": 0, "updated": 0, "unchanged": 0, "deleted": 0}

        # 3. Compare and generate markdown
        for table_name, live_columns in live_tables.items():
            if table_name in existing_tables:
                # Table exists, check if columns changed
                changed = self._update_markdown_if_changed(
                    table_name, live_columns, existing_tables[table_name]
                )
                if changed:
                    stats["updated"] += 1
                else:
                    stats["unchanged"] += 1
            else:
                # New table
                self._generate_new_markdown(table_name, live_columns)
                stats["added"] += 1

        return stats'''

NEW = '''    async def sync(self) -> dict:
        """Run the full synchronization process."""
        from backend.app.services.vault_enum_sampler import (
            inject_enum_block,
            sample_enum_values,
        )

        logger.info("Starting vault sync for workspace %s", self.workspace_id)

        # 1. Fetch live DB schema
        live_tables = await self._fetch_live_schema()

        # 1b. Live-sample DISTINCT values for low-cardinality VARCHAR columns
        # so the LLM sees real enum literals (e.g. "Bundles" not "Bundle").
        # Per-column errors are swallowed inside sample_enum_values.
        enum_map = await sample_enum_values(self.db_config, live_tables)

        # 2. Parse existing markdown files
        existing_tables = self._read_existing_vault()

        stats = {"added": 0, "updated": 0, "unchanged": 0, "deleted": 0, "enum_updated": 0}

        # 3. Compare and generate markdown
        for table_name, live_columns in live_tables.items():
            if table_name in existing_tables:
                # Table exists, check if columns changed
                changed = self._update_markdown_if_changed(
                    table_name, live_columns, existing_tables[table_name]
                )
                if changed:
                    stats["updated"] += 1
                else:
                    stats["unchanged"] += 1
            else:
                # New table
                self._generate_new_markdown(table_name, live_columns)
                stats["added"] += 1

            # 3b. Inject sampled enum-value block (idempotent — skips if unchanged).
            table_enums = enum_map.get(table_name)
            if table_enums:
                file_path = self.vault_path / f"{table_name}.md"
                if inject_enum_block(file_path, table_enums):
                    stats["enum_updated"] += 1

        return stats'''

SENTINEL = 'sample_enum_values(self.db_config, live_tables)'

p = pathlib.Path(sys.argv[1])
src = p.read_text()
if SENTINEL in src:
    print(f"already patched ({p.name})")
elif OLD not in src:
    sys.exit(f"[patch] ERROR: target sync() block not found in {p.name}. "
             f"File may already be modified or repo version differs.")
else:
    p.write_text(src.replace(OLD, NEW, 1))
    print(f"patched ({p.name})")
PYEOF

ok "done."
log ""
log "now restart backend so the new module is loaded:"
log "  cd $REPO_DIR && docker compose -f docker-compose.dev.yml restart backend"
log ""
log "then trigger a vault resync from the ARIA admin UI (Workspaces → STC →"
log "Resync Vault) and inspect a table file, e.g.:"
log "  grep -A 20 'ARIA:ENUM-VALUES-START' docs/vaults/stc-kuwait/tables/FCT_PREP_PROVISION.md"
log ""
log "you should see a 'Sampled Values' block with the real DB literals"
log "(e.g. 'Bundles' instead of 'Bundle')."
