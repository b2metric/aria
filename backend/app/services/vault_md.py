"""Service-layer helpers for reading vault markdown.

A small, dependency-free parser used by services (e.g. vault_llm_enrich) that
must NOT import the API layer (``backend.app.api.workspaces`` already has an
equivalent private parser, but importing it from a service would create an
api→service→api cycle). Keep this in sync with that parser's output shape.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ENUM_BLOCK_START = "<!-- ARIA:ENUM-VALUES-START -->"
ENUM_BLOCK_END = "<!-- ARIA:ENUM-VALUES-END -->"


def resolve_vault_file(vault_path: Path, table_name: str) -> Path:
    """Resolve a table's md file case-insensitively (Oracle UPPER vs PG lower).

    Falls back to the lowercase name when nothing matches.
    """
    for cand in (
        f"{table_name}.md",
        f"{table_name.upper()}.md",
        f"{table_name.lower()}.md",
    ):
        p = vault_path / cand
        if p.exists():
            return p
    target = f"{table_name.lower()}.md"
    if vault_path.exists():
        for p in vault_path.glob("*.md"):
            if p.name.lower() == target:
                return p
    return vault_path / target


def parse_vault_file(filepath: Path) -> dict[str, Any]:
    """Parse a vault markdown file into structured fields.

    Returns: table_name, description, business_name, keywords[],
    data_domain, columns[{name,type,nullable,is_pk,description}],
    relationships[{raw}], enriched_at, generated_at.
    """
    import yaml

    content = filepath.read_text(encoding="utf-8")

    frontmatter: dict[str, Any] = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1].strip()) or {}
            body = parts[2].strip()

    columns: list[dict[str, Any]] = []
    in_columns = False
    for line in body.split("\n"):
        if "## Columns" in line:
            in_columns = True
            continue
        if in_columns and line.strip().startswith("| Column"):
            continue
        if in_columns and line.strip().startswith("|---"):
            continue
        if in_columns and line.strip().startswith("|"):
            cells = [p.strip() for p in line.split("|")]
            if len(cells) >= 6:
                columns.append(
                    {
                        "name": cells[1],
                        "type": cells[2],
                        "nullable": cells[3] == "✓",
                        "is_pk": cells[4] == "✓",
                        "description": cells[5] if len(cells) > 5 else "",
                    }
                )
        elif in_columns and line.strip().startswith("##"):
            in_columns = False

    relationships: list[dict[str, Any]] = []
    in_rel = False
    for line in body.split("\n"):
        if "## Relationships" in line or "### Manual Relationships" in line:
            in_rel = True
            continue
        if in_rel and line.strip().startswith("- "):
            relationships.append({"raw": line.strip()[2:]})
        elif in_rel and line.strip().startswith("##"):
            in_rel = False

    keywords = frontmatter.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.strip("[]").split(",") if k.strip()]

    return {
        "table_name": frontmatter.get("table", filepath.stem.upper()),
        "description": frontmatter.get("description"),
        "business_name": frontmatter.get("business_name"),
        "keywords": keywords or [],
        "data_domain": frontmatter.get("data_domain"),
        "column_count": len(columns),
        "columns": columns,
        "relationships": relationships,
        "enriched_at": frontmatter.get("enriched_at"),
        "generated_at": frontmatter.get("generated_at"),
    }


def read_sections(filepath: Path, headers: list[str], max_chars: int = 6000) -> str:
    """Return the markdown of named ``## `` sections (e.g. "Domain Mapping",
    "Example Queries") concatenated. A header matches if any entry in ``headers``
    is a case-insensitive substring of the section title. Capture runs until the
    next non-matching ``## `` header (so ``### `` sub-headers and ```` ```sql ````
    fences inside are kept). Returns "" if the file/sections are absent.
    """
    if not filepath.exists():
        return ""
    out: list[str] = []
    capturing = False
    for line in filepath.read_text(encoding="utf-8").split("\n"):
        if line.startswith("## "):
            title = line[3:].strip().lower()
            capturing = any(h.lower() in title for h in headers)
        if capturing:
            out.append(line)
    return "\n".join(out).strip()[:max_chars]


def read_enum_block(filepath: Path) -> dict[str, list[str]]:
    """Extract sampled enum values from the ENUM-VALUES sentinel block.

    Returns {column_name: [values...]}. Empty dict if no block / unparseable.
    """
    if not filepath.exists():
        return {}
    content = filepath.read_text(encoding="utf-8")
    m = re.search(
        re.escape(ENUM_BLOCK_START) + r"(.*?)" + re.escape(ENUM_BLOCK_END),
        content,
        re.DOTALL,
    )
    if not m:
        return {}
    out: dict[str, list[str]] = {}
    for line in m.group(1).split("\n"):
        line = line.strip()
        # lines look like:  - **COL**: `v1`, `v2`, `v3`
        cm = re.match(r"- \*\*(.+?)\*\*:\s*(.+)", line)
        if not cm:
            continue
        col = cm.group(1).strip()
        vals = [v.strip().strip("`") for v in cm.group(2).split(",") if v.strip().strip("`")]
        if vals:
            out[col] = vals
    return out
