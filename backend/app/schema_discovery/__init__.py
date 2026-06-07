"""Schema discovery, vault generation, and enrichment module for ARIA."""

from backend.app.schema_discovery.models import (
    ColumnInfo,
    ForeignKeyInfo,
    SchemaSnapshot,
    TableInfo,
)
from backend.app.schema_discovery.discovery import (
    discover_schema,
    discover_schema_async,
)
from backend.app.schema_discovery.vault_generator import (
    generate_vault,
    generate_vault_async,
    generate_table_markdown,
)
from backend.app.schema_discovery.enrichment import (
    ColumnEnrichment,
    RelationshipEnrichment,
    TableEnrichment,
    VaultEnrichmentPayload,
    enrich_vault_table,
    enrich_vault_bulk,
    enrich_from_excel,
    enrich_from_json,
    parse_excel_metadata,
    parse_json_metadata,
)

__all__ = [
    # Models
    "ColumnInfo",
    "ForeignKeyInfo",
    "SchemaSnapshot",
    "TableInfo",
    # Discovery
    "discover_schema",
    "discover_schema_async",
    # Vault generation
    "generate_vault",
    "generate_vault_async",
    "generate_table_markdown",
    # Enrichment
    "ColumnEnrichment",
    "RelationshipEnrichment",
    "TableEnrichment",
    "VaultEnrichmentPayload",
    "enrich_vault_table",
    "enrich_vault_bulk",
    "enrich_from_excel",
    "enrich_from_json",
    "parse_excel_metadata",
    "parse_json_metadata",
]
