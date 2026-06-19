"""Obsidian vault generator from schema snapshots.

Generates Obsidian-compatible markdown files with YAML frontmatter
for each table in the schema. These files serve as the semantic
knowledge base for NL2SQL generation.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.app.schema_discovery.models import (
    ColumnInfo,
    SchemaSnapshot,
    TableInfo,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Semantic keyword inference
# ══════════════════════════════════════════════════════════════════════════════

# Common telecom/business keywords mapped from column patterns
_KEYWORD_PATTERNS: list[tuple[str, list[str]]] = [
    # Revenue & financial
    (
        r"(?i)(revenue|billamount|amount|price|cost|fee|rental|charge)",
        ["revenue", "billing", "financial", "money", "income", "payment"],
    ),
    (r"(?i)(recharge|topup|top_up)", ["recharge", "topup", "balance", "prepaid", "credit"]),
    # Subscriber/customer
    (r"(?i)(subno|msisdn|phone|mobile)", ["subscriber", "phone number", "msisdn", "mobile"]),
    (r"(?i)(contrno|contract)", ["contract", "subscriber", "customer", "account"]),
    (r"(?i)(nationality|country)", ["nationality", "country", "demographic", "geography"]),
    # Product/service
    (
        r"(?i)(offer|product|bundle|package|plan)",
        ["product", "offer", "package", "bundle", "tariff"],
    ),
    (
        r"(?i)(provision|subscription|service)",
        ["provision", "subscription", "service", "activation"],
    ),
    # Usage
    (r"(?i)(voice|call|minute|duration)", ["voice", "call", "usage", "minutes"]),
    (r"(?i)(sms|message)", ["sms", "message", "usage"]),
    (r"(?i)(data|gprs|mb|gb|internet)", ["data", "internet", "usage", "bandwidth"]),
    (r"(?i)(roaming|international)", ["roaming", "international", "travel"]),
    # Time/date
    (r"(?i)(date|_dt$|time)", ["date", "time", "temporal"]),
    (r"(?i)(snapshot|exec_date|log)", ["snapshot", "etl", "batch"]),
    # State/status
    (r"(?i)(state|status|active|flag)", ["state", "status", "lifecycle"]),
    (r"(?i)(churn|grace|disable)", ["churn", "retention", "lifecycle"]),
    # Channel
    (r"(?i)(channel|ussd|ivr|app|web|dealer)", ["channel", "touchpoint", "acquisition"]),
]

# Table name patterns for description inference
_TABLE_DESCRIPTIONS: dict[str, str] = {
    "DIM_": "Dimension table containing reference/master data for ",
    "FCT_": "Fact table containing transactional/event data for ",
    "VW_": "View aggregating data for ",
    "AGG_": "Aggregate table summarizing ",
}


def _infer_keywords_from_table(table: TableInfo) -> list[str]:
    """Infer semantic keywords from table name and columns."""
    keywords: set[str] = set()

    # Check table name
    table_upper = table.name.upper()
    for pattern, kws in _KEYWORD_PATTERNS:
        if re.search(pattern, table.name):
            keywords.update(kws)

    # Common table prefixes
    if "PREP" in table_upper:
        keywords.update(["prepaid", "subscriber"])
    if "POST" in table_upper:
        keywords.update(["postpaid", "subscriber"])
    if "MASTER" in table_upper:
        keywords.update(["master", "subscriber", "360 view"])
    if "HIST" in table_upper:
        keywords.update(["history", "historical", "time series"])
    if "SCD2" in table_upper:
        keywords.update(["slowly changing dimension", "history", "versioned"])

    # Check all columns
    for col in table.columns:
        for pattern, kws in _KEYWORD_PATTERNS:
            if re.search(pattern, col.name):
                keywords.update(kws)

    return sorted(keywords)


def _infer_description_from_table(table: TableInfo) -> str:
    """Generate a human-readable description for the table."""
    name = table.name

    # Check prefix
    prefix_desc = ""
    for prefix, desc in _TABLE_DESCRIPTIONS.items():
        if name.upper().startswith(prefix):
            prefix_desc = desc
            break

    # Extract meaningful parts from name
    # e.g., FCT_PREP_RECHARGE -> Prepaid Recharge
    parts = name.replace("FCT_", "").replace("DIM_", "").replace("VW_", "").replace("AGG_", "")
    parts = parts.replace("_", " ").title()

    if prefix_desc:
        return f"{prefix_desc}{parts}"

    return f"Table containing {parts} data"


def _format_column_type(col: ColumnInfo) -> str:
    """Format column type for documentation."""
    type_str = col.data_type
    if col.is_primary_key:
        type_str += " (PK)"
    if not col.nullable:
        type_str += " NOT NULL"
    return type_str


# ══════════════════════════════════════════════════════════════════════════════
# Markdown generation
# ══════════════════════════════════════════════════════════════════════════════


def generate_table_markdown(
    table: TableInfo,
    workspace_id: str,
    db_type: str,
    custom_metadata: dict[str, Any] | None = None,
) -> str:
    """Generate Obsidian-compatible markdown for a single table.

    Format:
    ---
    table: TABLE_NAME
    schema: SCHEMA_NAME
    database: DATABASE_TYPE
    workspace: WORKSPACE_ID
    keywords: [keyword1, keyword2, ...]
    row_count: N
    ---

    # TABLE_NAME

    **Description:** ...

    ## Columns

    | Column | Type | Description |
    |--------|------|-------------|
    | COL1   | TYPE | ...         |

    ## Relationships

    - FK_NAME: COL -> TARGET.COL
    """
    keywords = _infer_keywords_from_table(table)
    description = _infer_description_from_table(table)

    # YAML frontmatter
    lines = [
        "---",
        f"table: {table.name}",
    ]
    if table.schema_name:
        lines.append(f"schema: {table.schema_name}")
    lines.extend(
        [
            f"database: {db_type}",
            f"workspace: {workspace_id}",
            f"keywords: [{', '.join(keywords)}]",
        ]
    )
    if table.row_count_estimate is not None:
        lines.append(f"row_count: {table.row_count_estimate}")
    if custom_metadata:
        for key, value in custom_metadata.items():
            lines.append(f"{key}: {value}")
    lines.append(f"generated_at: {datetime.now(UTC).isoformat()}")
    lines.append("---")
    lines.append("")

    # Title and description
    lines.append(f"# {table.name}")
    lines.append("")
    lines.append(f"**Description:** {description}")
    lines.append("")

    # Columns table
    lines.append("## Columns")
    lines.append("")
    lines.append("| Column | Type | Nullable | PK | Description |")
    lines.append("|--------|------|----------|----|-----------—|")

    for col in table.columns:
        nullable = "✓" if col.nullable else "✗"
        pk = "✓" if col.is_primary_key else ""
        col_desc = col.comment or _infer_column_description(col.name)
        lines.append(f"| {col.name} | {col.data_type} | {nullable} | {pk} | {col_desc} |")

    lines.append("")

    # Foreign keys / relationships
    if table.foreign_keys:
        lines.append("## Relationships")
        lines.append("")
        for fk in table.foreign_keys:
            lines.append(
                f"- **{fk.constraint_name or 'FK'}**: `{fk.source_column}` → `{fk.target_table}.{fk.target_column}`"
            )
        lines.append("")

    # Keywords section (redundant but helps with grep/search)
    lines.append("## Keywords")
    lines.append("")
    lines.append(", ".join(keywords))
    lines.append("")

    return "\n".join(lines)


def _infer_column_description(col_name: str) -> str:
    """Generate a basic description from column name."""
    # Common patterns
    patterns = {
        r"(?i)^exec_date$": "ETL execution date",
        r"(?i)^snapshot_date$": "Data snapshot date",
        r"(?i)^contrno$": "Contract number (subscriber identifier)",
        r"(?i)^subno$": "MSISDN (phone number)",
        r"(?i)^appdate$": "Application/activation date",
        r"(?i)^nationality$": "Customer nationality",
        r"(?i)^contract_category$": "Contract category (Individual, Corporate, VIP)",
        r"(?i)^bs_type$": "Basic service type (Voice, Data, M2M)",
        r"(?i)billamount$": "Billed amount (revenue)",
        r"(?i)topup_amount$": "Recharge amount",
        r"(?i)prepaid_balance": "Prepaid account balance",
        r"(?i)^region$": "Geographic region",
        r"(?i)^channel": "Transaction channel",
        r"(?i)_dt$": "Date/timestamp field",
        r"(?i)_cnt$": "Count metric",
        r"(?i)_mb$": "Data volume in MB",
        r"(?i)_min$": "Duration in minutes",
    }

    for pattern, desc in patterns.items():
        if re.search(pattern, col_name):
            return desc

    # Fallback: humanize column name
    return col_name.replace("_", " ").title()


# ══════════════════════════════════════════════════════════════════════════════
# Vault generation
# ══════════════════════════════════════════════════════════════════════════════


def generate_vault(
    snapshot: SchemaSnapshot,
    vault_base_path: str | Path,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Generate Obsidian vault files from a schema snapshot.

    Args:
        snapshot: The discovered schema snapshot
        vault_base_path: Base path for vault files (e.g., docs/vaults)
        overwrite: Whether to overwrite existing files

    Returns:
        Statistics about generated files
    """
    vault_path = Path(vault_base_path) / snapshot.workspace_id / "tables"
    vault_path.mkdir(parents=True, exist_ok=True)

    logger.info("Generating vault at %s", vault_path)

    stats = {
        "workspace_id": snapshot.workspace_id,
        "vault_path": str(vault_path),
        "tables_total": len(snapshot.tables),
        "files_created": 0,
        "files_skipped": 0,
        "errors": [],
    }

    for table in snapshot.tables:
        filename = f"{table.name.lower()}.md"
        filepath = vault_path / filename

        if filepath.exists() and not overwrite:
            stats["files_skipped"] += 1
            continue

        try:
            content = generate_table_markdown(
                table=table,
                workspace_id=snapshot.workspace_id,
                db_type=snapshot.db_type,
            )
            filepath.write_text(content, encoding="utf-8")
            stats["files_created"] += 1
            logger.debug("Generated %s", filepath)
        except Exception as e:
            stats["errors"].append({"table": table.name, "error": str(e)})
            logger.error("Failed to generate %s: %s", table.name, e)

    # Generate index.md
    index_path = vault_path.parent / "index.md"
    index_content = _generate_index(snapshot)
    index_path.write_text(index_content, encoding="utf-8")

    logger.info(
        "Vault generation complete: %d created, %d skipped, %d errors",
        stats["files_created"],
        stats["files_skipped"],
        len(stats["errors"]),
    )

    return stats


def _generate_index(snapshot: SchemaSnapshot) -> str:
    """Generate the vault index file."""
    lines = [
        "---",
        f"workspace: {snapshot.workspace_id}",
        f"database: {snapshot.db_type}",
        f"table_count: {snapshot.table_count}",
        f"generated_at: {datetime.now(UTC).isoformat()}",
        "---",
        "",
        f"# {snapshot.workspace_id} Knowledge Base",
        "",
        f"Database: **{snapshot.database_name}** ({snapshot.db_type})",
        "",
        f"Total tables: **{snapshot.table_count}**",
        "",
        "## Tables",
        "",
    ]

    # Group by prefix
    dim_tables = []
    fct_tables = []
    other_tables = []

    for table in snapshot.tables:
        name = table.name.upper()
        if name.startswith("DIM_"):
            dim_tables.append(table)
        elif name.startswith("FCT_"):
            fct_tables.append(table)
        else:
            other_tables.append(table)

    if dim_tables:
        lines.append("### Dimension Tables")
        lines.append("")
        for t in sorted(dim_tables, key=lambda x: x.name):
            row_info = f" ({t.row_count_estimate:,} rows)" if t.row_count_estimate else ""
            lines.append(f"- [[tables/{t.name.lower()}|{t.name}]]{row_info}")
        lines.append("")

    if fct_tables:
        lines.append("### Fact Tables")
        lines.append("")
        for t in sorted(fct_tables, key=lambda x: x.name):
            row_info = f" ({t.row_count_estimate:,} rows)" if t.row_count_estimate else ""
            lines.append(f"- [[tables/{t.name.lower()}|{t.name}]]{row_info}")
        lines.append("")

    if other_tables:
        lines.append("### Other Tables")
        lines.append("")
        for t in sorted(other_tables, key=lambda x: x.name):
            row_info = f" ({t.row_count_estimate:,} rows)" if t.row_count_estimate else ""
            lines.append(f"- [[tables/{t.name.lower()}|{t.name}]]{row_info}")
        lines.append("")

    return "\n".join(lines)


async def generate_vault_async(
    snapshot: SchemaSnapshot,
    vault_base_path: str | Path,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Async wrapper for generate_vault."""
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: generate_vault(snapshot, vault_base_path, overwrite),
    )
