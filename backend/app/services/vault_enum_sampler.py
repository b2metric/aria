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
    # Identifiers from ALL_TAB_COLUMNS / information_schema are safe; quote
    # defensively in case of reserved-word column names.
    return '"' + name.replace('"', '""') + '"'


async def sample_enum_values(
    db_config: Any,
    live_tables: dict[str, list[dict]],
    max_cardinality: int | None = None,
) -> dict[str, dict[str, list[str]]]:
    """For each VARCHAR/CHAR column whose DISTINCT count <= max_cardinality,
    fetch up to max_cardinality DISTINCT values. Per-column errors are
    swallowed so a single bad column doesn't break vault sync.

    Returns: {table_name: {column_name: [v1, v2, ...]}}
    """
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
                rows = await loop.run_in_executor(None, lambda s=count_sql: executor.execute(s, {}))
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
                values = sorted(
                    {
                        str(next(iter(r.values()))).strip()
                        for r in drows
                        if r and next(iter(r.values()), None) is not None
                    }
                )
                if values:
                    out.setdefault(table_name, {})[col_name] = values
                    logger.info(
                        "sampled %d enum values for %s.%s",
                        len(values),
                        table_name,
                        col_name,
                    )
            except Exception as e:
                logger.warning("enum sample failed for %s.%s: %s", table_name, col_name, e)
                continue

    return out


def inject_enum_block(file_path: Path, table_enums: dict[str, list[str]]) -> bool:
    """Insert or replace the enum-values block in a vault markdown file.

    Idempotent: skips writing if the block's value content is unchanged
    (ignoring the timestamp line).

    Returns True if the file was modified, False otherwise.
    """
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
