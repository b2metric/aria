"""Vault enrichment service for adding metadata from external sources.

This module provides APIs to enrich existing Obsidian vault files with:
- Column descriptions from Excel/JSON imports
- Custom business keywords
- Manual relationship definitions
- Business glossary terms

The enrichment is additive — it merges with existing content rather than
overwriting the entire file.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic models for enrichment payloads
# ══════════════════════════════════════════════════════════════════════════════


class ColumnEnrichment(BaseModel):
    """Enrichment data for a single column."""

    name: str = Field(..., description="Column name (case-insensitive match)")
    description: str | None = Field(None, description="Human-readable description")
    business_name: str | None = Field(None, description="Business-friendly name")
    keywords: list[str] | None = Field(None, description="Additional keywords")
    example_values: list[str] | None = Field(None, description="Example values")
    is_sensitive: bool = Field(False, description="Contains PII or sensitive data")
    notes: str | None = Field(None, description="Additional notes")


class RelationshipEnrichment(BaseModel):
    """Manual relationship definition (for tables without FK constraints)."""

    source_column: str
    target_table: str
    target_column: str
    relationship_type: str = Field("foreign_key", description="Type: foreign_key, lookup, derived")
    description: str | None = None


class TableEnrichment(BaseModel):
    """Enrichment data for a single table."""

    table_name: str = Field(..., description="Table name (case-insensitive match)")
    description: str | None = Field(None, description="Table description")
    business_name: str | None = Field(None, description="Business-friendly name")
    keywords: list[str] | None = Field(None, description="Additional keywords")
    columns: list[ColumnEnrichment] = Field(default_factory=list)
    relationships: list[RelationshipEnrichment] = Field(default_factory=list)
    business_owner: str | None = Field(None, description="Business owner/steward")
    data_domain: str | None = Field(
        None, description="Data domain (e.g., Customer, Product, Finance)"
    )
    update_frequency: str | None = Field(None, description="How often data is refreshed")
    notes: str | None = None


class VaultEnrichmentPayload(BaseModel):
    """Bulk enrichment payload for multiple tables."""

    workspace_id: str
    source: str = Field("manual", description="Source of enrichment: manual, excel, json, api")
    tables: list[TableEnrichment] = Field(default_factory=list)


class ExcelImportConfig(BaseModel):
    """Configuration for Excel import."""

    column_name_header: str = Field(default="Column", description="Header for column name")
    description_header: str = Field(default="Description", description="Header for description")
    skip_rows: int = Field(default=0, description="Rows to skip at the start")


# ══════════════════════════════════════════════════════════════════════════════
# Excel/JSON parsing
# ══════════════════════════════════════════════════════════════════════════════


def parse_excel_metadata(
    excel_path: str | Path,
    config: ExcelImportConfig | None = None,
) -> list[TableEnrichment]:
    """Parse Excel file with table/column metadata.

    Expected format: Each sheet is a table, with columns:
    - First column: Column name
    - Second column: Description

    Or custom headers specified in config.
    """
    import pandas as pd

    config = config or ExcelImportConfig()
    xlsx = pd.ExcelFile(excel_path)

    tables: list[TableEnrichment] = []

    for sheet_name in xlsx.sheet_names:
        # Skip view definitions (they contain SQL, not metadata)
        if sheet_name.upper().startswith("VW_"):
            logger.info("Skipping view sheet: %s", sheet_name)
            continue

        df = pd.read_excel(xlsx, sheet_name=sheet_name, header=None)

        if df.empty:
            continue

        columns: list[ColumnEnrichment] = []

        for _idx, row in df.iterrows():
            # First column is column name, second is description
            col_name = row.iloc[0] if pd.notna(row.iloc[0]) else None
            col_desc = row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) else None

            if col_name and str(col_name).strip():
                col_name_str = str(col_name).strip()
                col_desc_str = str(col_desc).strip() if col_desc else None

                # Skip if it looks like a header row
                if col_name_str.upper() in ("COLUMN", "COLUMN_NAME", "FIELD", "FIELD_NAME"):
                    continue

                columns.append(
                    ColumnEnrichment(
                        name=col_name_str,
                        description=col_desc_str,
                    )
                )

        if columns:
            tables.append(
                TableEnrichment(
                    table_name=sheet_name,
                    columns=columns,
                )
            )
            logger.info("Parsed %s: %d columns", sheet_name, len(columns))

    return tables


def parse_json_metadata(json_path: str | Path) -> list[TableEnrichment]:
    """Parse JSON file with table/column metadata.

    Expected format:
    {
        "tables": [
            {
                "table_name": "FCT_PREP_REV",
                "description": "Revenue fact table",
                "columns": [
                    {"name": "BILLAMOUNT", "description": "Billed amount in KD"}
                ]
            }
        ]
    }
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    tables: list[TableEnrichment] = []

    for table_data in data.get("tables", []):
        columns = [ColumnEnrichment(**col) for col in table_data.get("columns", [])]

        tables.append(
            TableEnrichment(
                table_name=table_data["table_name"],
                description=table_data.get("description"),
                business_name=table_data.get("business_name"),
                keywords=table_data.get("keywords"),
                columns=columns,
                relationships=[
                    RelationshipEnrichment(**rel) for rel in table_data.get("relationships", [])
                ],
                business_owner=table_data.get("business_owner"),
                data_domain=table_data.get("data_domain"),
                update_frequency=table_data.get("update_frequency"),
                notes=table_data.get("notes"),
            )
        )

    return tables


# ══════════════════════════════════════════════════════════════════════════════
# Vault enrichment logic
# ══════════════════════════════════════════════════════════════════════════════


def _parse_vault_file(filepath: Path) -> tuple[dict[str, Any], str]:
    """Parse a vault markdown file into frontmatter dict and body."""
    content = filepath.read_text(encoding="utf-8")

    # Split frontmatter and body
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter_str = parts[1].strip()
            body = parts[2].strip()

            # Parse YAML frontmatter
            import yaml

            frontmatter = yaml.safe_load(frontmatter_str) or {}
            return frontmatter, body

    return {}, content


def _rebuild_vault_file(frontmatter: dict[str, Any], body: str) -> str:
    """Rebuild a vault file from frontmatter and body."""
    import yaml

    # Custom representer for lists to use flow style
    def list_representer(dumper, data):
        if all(isinstance(item, str) for item in data):
            return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)
        return dumper.represent_sequence("tag:yaml.org,2002:seq", data)

    yaml.add_representer(list, list_representer)

    frontmatter_str = yaml.dump(
        frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False
    )

    return f"---\n{frontmatter_str}---\n\n{body}"


def _update_columns_section(body: str, columns_enrichment: list[ColumnEnrichment]) -> str:
    """Update the Columns section with enriched descriptions."""
    # Build lookup dict (case-insensitive)
    enrichment_map = {c.name.upper(): c for c in columns_enrichment}

    lines = body.split("\n")
    new_lines = []
    in_columns_table = False

    for line in lines:
        # Detect columns table
        if line.strip().startswith("| Column"):
            in_columns_table = True
            new_lines.append(line)
            continue

        if in_columns_table and line.strip().startswith("|---"):
            new_lines.append(line)
            continue

        if in_columns_table and line.strip().startswith("|"):
            # Parse existing row
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:  # |, col, type, nullable, pk, desc, |
                col_name = parts[1]
                col_upper = col_name.upper()

                if col_upper in enrichment_map:
                    enrichment = enrichment_map[col_upper]
                    if enrichment.description:
                        # Update description (last column before closing |)
                        # Remove the [:100] truncate limit to save full user descriptions
                        parts[-2] = enrichment.description
                        line = " | ".join(parts)

            new_lines.append(line)
            continue

        if in_columns_table and not line.strip().startswith("|"):
            in_columns_table = False

        new_lines.append(line)

    return "\n".join(new_lines)


def _add_enrichment_section(body: str, enrichment: TableEnrichment) -> str:
    """Add or update enrichment metadata section."""
    # Check if enrichment section exists
    if "## Business Metadata" in body:
        # Remove existing section and rebuild
        body = re.sub(
            r"## Business Metadata.*?(?=## |$)",
            "",
            body,
            flags=re.DOTALL,
        ).strip()

    # Build new section
    section_lines = ["", "## Business Metadata", ""]

    if enrichment.business_name:
        section_lines.append(f"**Business Name:** {enrichment.business_name}")
    if enrichment.description:
        section_lines.append(f"**Description:** {enrichment.description}")
    if enrichment.data_domain:
        section_lines.append(f"**Data Domain:** {enrichment.data_domain}")
    if enrichment.business_owner:
        section_lines.append(f"**Business Owner:** {enrichment.business_owner}")
    if enrichment.update_frequency:
        section_lines.append(f"**Update Frequency:** {enrichment.update_frequency}")
    if enrichment.notes:
        section_lines.append(f"**Notes:** {enrichment.notes}")

    section_lines.append("")

    # Add column descriptions if any
    cols_with_desc = [c for c in enrichment.columns if c.description]
    if cols_with_desc:
        section_lines.append("### Column Descriptions")
        section_lines.append("")
        for col in cols_with_desc:
            desc = col.description.replace("\n", " ").strip() if col.description else ""
            section_lines.append(f"- **{col.name}**: {desc}")
        section_lines.append("")

    # NOTE: relationships are intentionally NOT written here. They live in a
    # single canonical "## Relationships" section managed by append_relationship/
    # remove_relationship, so repeated enrichment never stacks duplicate
    # relationship sections.

    return body + "\n".join(section_lines)


def _resolve_vault_file(vault_path: Path, table_name: str) -> Path:
    """Resolve a table's md file case-insensitively.

    Vault files are generated with the DB's native casing (Oracle = UPPERCASE,
    Postgres = lowercase), so a fixed-case lookup misses on the case-sensitive
    Linux container (STC files are ``FCT_*.md``, Medianova ``ds_*.md``). Try
    exact / upper / lower, then a case-insensitive directory scan. Falls back to
    the lowercase name (preserving prior new-file-creation behavior) when no
    existing file matches.
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


def remove_relationship(
    vault_base_path: str | Path,
    workspace_id: str,
    table_name: str,
    raw: str,
) -> dict[str, Any]:
    """Remove a single relationship bullet (matched by its rendered text) from a
    table's vault file. ``raw`` is the text the API returned for the row (the
    line content after the "- " bullet). Only bullets inside a Relationships
    section are eligible, so unrelated bullets are never touched.

    Returns {status: ok|not_found|error, removed: bool}.
    """
    vault_path = Path(vault_base_path) / workspace_id / "tables"
    filepath = _resolve_vault_file(vault_path, table_name)
    if not filepath.exists():
        return {
            "status": "error",
            "error": f"Vault file not found: {filepath.name}",
            "removed": False,
        }

    target = (raw or "").strip()
    if not target:
        return {"status": "error", "error": "raw relationship text is required", "removed": False}

    lines = filepath.read_text(encoding="utf-8").split("\n")
    out: list[str] = []
    removed = False
    in_rel = False
    for line in lines:
        s = line.strip()
        if s.startswith("## ") or s.startswith("### "):
            in_rel = "Relationships" in s
        if (not removed) and in_rel and s.startswith("- ") and s[2:].strip() == target:
            removed = True
            continue  # drop this bullet
        out.append(line)

    if removed:
        filepath.write_text("\n".join(out), encoding="utf-8")
    return {"status": "ok" if removed else "not_found", "removed": removed}


def _build_rel_bullet(rel: RelationshipEnrichment) -> str:
    """Render a relationship as a canonical bullet line (without leading '- ')."""
    desc = f" — {rel.description}" if rel.description else ""
    return (
        f"`{rel.source_column}` → `{rel.target_table}.{rel.target_column}` "
        f"({rel.relationship_type}){desc}"
    )


def append_relationship(
    vault_base_path: str | Path,
    workspace_id: str,
    table_name: str,
    rel: RelationshipEnrichment,
) -> dict[str, Any]:
    """Append a relationship to the SINGLE canonical '## Relationships' section
    (created if missing), de-duplicated. This is the only writer for
    relationships, so sections never stack. Returns {status, added}.
    """
    vault_path = Path(vault_base_path) / workspace_id / "tables"
    filepath = _resolve_vault_file(vault_path, table_name)
    if not filepath.exists():
        return {
            "status": "error",
            "error": f"Vault file not found: {filepath.name}",
            "added": False,
        }

    bullet = _build_rel_bullet(rel)
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")

    # already present anywhere in a Relationships section?
    in_rel = False
    for line in lines:
        s = line.strip()
        if s.startswith("## ") or s.startswith("### "):
            in_rel = "Relationships" in s
        if in_rel and s.startswith("- ") and s[2:].strip() == bullet:
            return {"status": "exists", "added": False}

    # find an existing canonical "## Relationships" header to append under
    rel_idx = next((i for i, ln in enumerate(lines) if ln.strip() == "## Relationships"), None)
    if rel_idx is not None:
        # insert after the header's bullet list (before next header / EOF)
        j = rel_idx + 1
        while j < len(lines) and not (lines[j].startswith("## ") or lines[j].startswith("### ")):
            j += 1
        # back up over trailing blanks
        k = j
        while k > rel_idx + 1 and lines[k - 1].strip() == "":
            k -= 1
        lines.insert(k, f"- {bullet}")
        new_content = "\n".join(lines)
    else:
        new_content = content.rstrip() + "\n\n## Relationships\n\n- " + bullet + "\n"

    filepath.write_text(new_content, encoding="utf-8")
    return {"status": "ok", "added": True}


def parse_example_queries(filepath: Path) -> list[dict[str, str]]:
    """Parse the '## Example Queries' section into [{question, answer, sql}].

    Format per item:  ### Q: <question>  then optional explanation text (the
    "answer" shown alongside results)  then a ```sql ... ``` fence.
    """
    if not filepath.exists():
        return []
    content = filepath.read_text(encoding="utf-8")
    # isolate the Example Queries section (## Example Queries .. next ## )
    m = re.search(r"^## Example Queries\s*\n(.*?)(?=^## |\Z)", content, re.DOTALL | re.MULTILINE)
    if not m:
        return []
    section = m.group(1)
    out: list[dict[str, str]] = []
    # each ### Q: question  ... ```sql ... ```
    for q in re.finditer(
        r"^###\s*Q:\s*(.+?)\s*\n(.*?)(?=^###\s*Q:|\Z)", section, re.DOTALL | re.MULTILINE
    ):
        question = q.group(1).strip()
        body = q.group(2)
        sm = re.search(r"```(?:sql)?\s*\n(.*?)```", body, re.DOTALL)
        sql = sm.group(1).strip() if sm else ""
        # explanation = the markdown text BEFORE the code fence
        answer = body[: sm.start()].strip() if sm else body.strip()
        out.append({"question": question, "answer": answer, "sql": sql})
    return out


def add_example_query(
    vault_base_path: str | Path,
    workspace_id: str,
    table_name: str,
    question: str,
    sql: str,
    answer: str = "",
) -> dict[str, Any]:
    """Append a Q→(answer)→SQL example under '## Example Queries' (created if missing)."""
    vault_path = Path(vault_base_path) / workspace_id / "tables"
    filepath = _resolve_vault_file(vault_path, table_name)
    if not filepath.exists():
        return {"status": "error", "error": f"Vault file not found: {filepath.name}"}
    question = (question or "").strip()
    sql = (sql or "").strip()
    answer = (answer or "").strip()
    if not question or not sql:
        return {"status": "error", "error": "question and sql are required"}

    answer_part = f"{answer}\n\n" if answer else ""
    block = f"\n### Q: {question}\n\n{answer_part}```sql\n{sql}\n```\n"
    content = filepath.read_text(encoding="utf-8")
    if "## Example Queries" in content:
        # insert at the end of the Example Queries section (before next ## / EOF)
        lines = content.split("\n")
        start = next(i for i, ln in enumerate(lines) if ln.strip() == "## Example Queries")
        j = start + 1
        while j < len(lines) and not lines[j].startswith("## "):
            j += 1
        k = j
        while k > start + 1 and lines[k - 1].strip() == "":
            k -= 1
        lines[k:k] = block.split("\n")
        new_content = "\n".join(lines)
    else:
        new_content = content.rstrip() + "\n\n## Example Queries\n" + block
    filepath.write_text(new_content, encoding="utf-8")
    return {"status": "ok"}


def remove_example_query(
    vault_base_path: str | Path, workspace_id: str, table_name: str, question: str
) -> dict[str, Any]:
    """Remove the '### Q: <question>' block (matched by question text)."""
    vault_path = Path(vault_base_path) / workspace_id / "tables"
    filepath = _resolve_vault_file(vault_path, table_name)
    if not filepath.exists():
        return {
            "status": "error",
            "error": f"Vault file not found: {filepath.name}",
            "removed": False,
        }
    target = (question or "").strip()
    content = filepath.read_text(encoding="utf-8")
    # remove a ### Q: <target> block up to the next ### or ## or EOF
    pattern = re.compile(
        r"\n?###\s*Q:\s*" + re.escape(target) + r"\s*\n.*?(?=\n###\s*Q:|\n## |\Z)",
        re.DOTALL,
    )
    new_content, n = pattern.subn("", content, count=1)
    if n:
        new_content = re.sub(r"\n{3,}", "\n\n", new_content)
        filepath.write_text(new_content, encoding="utf-8")
    return {"status": "ok" if n else "not_found", "removed": bool(n)}


def enrich_vault_table(
    vault_base_path: str | Path,
    workspace_id: str,
    enrichment: TableEnrichment,
    replace_keywords: bool = False,
) -> dict[str, Any]:
    """Enrich a single table's vault file with metadata.

    ``replace_keywords``: when False (default — LLM enrichment / Excel / JSON
    import) keywords are UNIONed with existing so an auto-pass never clobbers
    curation. When True (explicit user edit via the PATCH endpoint) the provided
    list REPLACES the frontmatter keywords — including clearing to ``[]`` — so a
    keyword the user deleted in the UI does not reappear from the old set.

    Returns:
        Status dict with success/error info
    """
    vault_path = Path(vault_base_path) / workspace_id / "tables"
    filepath = _resolve_vault_file(vault_path, enrichment.table_name)

    if not filepath.exists():
        return {
            "table": enrichment.table_name,
            "status": "error",
            "error": f"Vault file not found: {filepath}",
        }

    try:
        frontmatter, body = _parse_vault_file(filepath)

        # Drop any legacy body "**Description:** No description provided yet."
        # placeholder. We set frontmatter `description` below (the single source of
        # truth the RAG pipeline reads), so leaving the body line is the exact
        # stale-placeholder drift the vault contract forbids.
        body = re.sub(
            r"^\*\*Description:\*\* No description provided yet\.\s*$\n?",
            "",
            body,
            flags=re.MULTILINE,
        )

        # Update frontmatter keywords
        if replace_keywords:
            # Explicit user edit: the provided list IS the new set (None = leave
            # untouched, [] = clear). No union, so deletions stick.
            if enrichment.keywords is not None:
                frontmatter["keywords"] = sorted(set(enrichment.keywords))
        elif enrichment.keywords:
            # Enrichment pass: union with existing so we never clobber curation.
            existing_keywords = frontmatter.get("keywords", [])
            if isinstance(existing_keywords, str):
                existing_keywords = [k.strip() for k in existing_keywords.strip("[]").split(",")]
            merged_keywords = sorted(set(existing_keywords) | set(enrichment.keywords))
            frontmatter["keywords"] = merged_keywords

        # Update description in frontmatter
        if enrichment.description:
            frontmatter["description"] = enrichment.description

        if enrichment.business_name:
            frontmatter["business_name"] = enrichment.business_name

        if enrichment.data_domain:
            frontmatter["data_domain"] = enrichment.data_domain

        # Add enrichment timestamp
        frontmatter["enriched_at"] = datetime.now(UTC).isoformat()

        # Update columns section in body
        if enrichment.columns:
            body = _update_columns_section(body, enrichment.columns)

        # Add/update business metadata section
        body = _add_enrichment_section(body, enrichment)

        # Rebuild and save
        new_content = _rebuild_vault_file(frontmatter, body)
        filepath.write_text(new_content, encoding="utf-8")

        # Relationships go into the single canonical "## Relationships" section
        # (append_relationship re-reads the file), so they never stack.
        rels_added = 0
        for rel in enrichment.relationships:
            if append_relationship(vault_base_path, workspace_id, enrichment.table_name, rel).get(
                "added"
            ):
                rels_added += 1

        return {
            "table": enrichment.table_name,
            "status": "success",
            "columns_enriched": len([c for c in enrichment.columns if c.description]),
            "relationships_added": rels_added,
        }

    except Exception as e:
        logger.exception("Failed to enrich %s", enrichment.table_name)
        return {
            "table": enrichment.table_name,
            "status": "error",
            "error": str(e),
        }


def enrich_vault_bulk(
    vault_base_path: str | Path,
    payload: VaultEnrichmentPayload,
) -> dict[str, Any]:
    """Enrich multiple tables in a vault.

    Returns:
        Summary statistics and per-table results
    """
    results = []

    for table_enrichment in payload.tables:
        result = enrich_vault_table(
            vault_base_path=vault_base_path,
            workspace_id=payload.workspace_id,
            enrichment=table_enrichment,
        )
        results.append(result)

    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")

    return {
        "workspace_id": payload.workspace_id,
        "source": payload.source,
        "tables_processed": len(results),
        "success_count": success_count,
        "error_count": error_count,
        "results": results,
    }


# ══════════════════════════════════════════════════════════════════════════════
# High-level convenience functions
# ══════════════════════════════════════════════════════════════════════════════


def enrich_from_excel(
    excel_path: str | Path,
    vault_base_path: str | Path,
    workspace_id: str,
    config: ExcelImportConfig | None = None,
) -> dict[str, Any]:
    """One-shot: parse Excel and enrich vault.

    Args:
        excel_path: Path to Excel file with metadata
        vault_base_path: Base path for vault files
        workspace_id: Target workspace ID
        config: Optional Excel parsing configuration

    Returns:
        Enrichment results summary
    """
    tables = parse_excel_metadata(excel_path, config)

    payload = VaultEnrichmentPayload(
        workspace_id=workspace_id,
        source="excel",
        tables=tables,
    )

    return enrich_vault_bulk(vault_base_path, payload)


def enrich_from_json(
    json_path: str | Path,
    vault_base_path: str | Path,
    workspace_id: str,
) -> dict[str, Any]:
    """One-shot: parse JSON and enrich vault.

    Args:
        json_path: Path to JSON file with metadata
        vault_base_path: Base path for vault files
        workspace_id: Target workspace ID

    Returns:
        Enrichment results summary
    """
    tables = parse_json_metadata(json_path)

    payload = VaultEnrichmentPayload(
        workspace_id=workspace_id,
        source="json",
        tables=tables,
    )

    return enrich_vault_bulk(vault_base_path, payload)


def enrich_from_metadata_json(
    json_path: str | Path,
    vault_base_path: str | Path,
    workspace_id: str,
) -> dict[str, Any]:
    """Import a ``scripts/extract-db-metadata.py`` JSON into the vault.

    Two passes:
    1. Standard enrichment (description / keywords / column descriptions /
       relationships) via ``enrich_from_json`` — the extra ``enum_values`` /
       ``sample_rows`` / ``row_count`` / ``data_type`` keys are ignored by
       ``parse_json_metadata`` (Pydantic ignores unknown fields).
    2. Enum-value blocks written via ``inject_enum_block`` — the canonical enum
       rendering the SQL pipeline relies on. ``sample_rows`` are intentionally
       NOT written into the vault (PII; the LLM needs enum literals, not raw
       rows — they live only in the extraction JSON for human review).
    """
    import json as _json

    from backend.app.schema_discovery.models import ColumnInfo, TableInfo
    from backend.app.schema_discovery.vault_generator import generate_table_markdown
    from backend.app.services.vault_enum_sampler import inject_enum_block

    with open(json_path, encoding="utf-8") as f:
        data = _json.load(f)

    tables_dir = Path(vault_base_path) / workspace_id / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    # Pass 0: create vault files that don't exist yet, straight from the JSON
    # columns. For an air-gapped customer DB the offline extractor JSON is the
    # ONLY schema source — there is no live discovery to /vault/generate from.
    # Existing files are left untouched (the enrich passes below update them).
    db_type = data.get("db_type") or "oracle"
    tables_created = 0
    for t in data.get("tables", []):
        cols = t.get("columns") or []
        fp = _resolve_vault_file(tables_dir, t["table_name"])
        if not cols or fp.exists():
            continue
        table = TableInfo(
            name=t["table_name"],
            schema_name=data.get("owner"),
            row_count_estimate=t.get("row_count"),
            columns=[
                ColumnInfo(
                    name=c["name"],
                    data_type=c.get("data_type") or "",
                    nullable=bool(c.get("nullable", True)),
                    is_primary_key=bool(c.get("is_pk", False)),
                )
                for c in cols
            ],
        )
        fp.write_text(generate_table_markdown(table, workspace_id, db_type), encoding="utf-8")
        tables_created += 1

    base = enrich_from_json(json_path, vault_base_path, workspace_id)

    enum_updates = 0
    for t in data.get("tables", []):
        enums = t.get("enum_values")
        if not enums:
            continue
        fp = _resolve_vault_file(tables_dir, t["table_name"])
        if fp.exists() and inject_enum_block(fp, enums):
            enum_updates += 1

    base["tables_created"] = tables_created
    base["enum_blocks_updated"] = enum_updates
    return base
