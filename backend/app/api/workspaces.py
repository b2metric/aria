"""Workspace management API endpoints.

Provides endpoints for:
- Schema discovery (introspect external database)
- Vault generation (create Obsidian knowledge base)
- Vault enrichment (add metadata from Excel/JSON)
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from backend.app.auth.dependencies import CurrentUser, WorkspaceID
from backend.app.auth.models import Role
from backend.app.auth.rbac import require_role
from backend.app.core.config import get_settings
from backend.app.db.models import DatabaseType, DBConfig
from backend.app.schema_discovery.cache import set_schema
from backend.app.schema_discovery.discovery import discover_schema_async
from backend.app.schema_discovery.enrichment import (
    ColumnEnrichment,
    ExcelImportConfig,
    RelationshipEnrichment,
    TableEnrichment,
    VaultEnrichmentPayload,
    enrich_from_excel,
    enrich_vault_bulk,
    enrich_vault_table,
    parse_excel_metadata,
)
from backend.app.schema_discovery.models import SchemaSnapshot
from backend.app.schema_discovery.vault_generator import (
    generate_vault_async,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


# ══════════════════════════════════════════════════════════════════════════════
# Request/Response models
# ══════════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field


class DBConnectionRequest(BaseModel):
    """Database connection parameters for schema discovery."""
    
    db_type: str = Field(..., description="Database type: postgresql, mysql, oracle, mssql")
    host: str
    port: int | None = None
    database: str
    username: str
    password: str
    db_config_id: str = Field(default="default", description="Identifier for this DB config")
    include_row_counts: bool = Field(default=True, description="Include estimated row counts")


class DiscoverSchemaResponse(BaseModel):
    """Response from schema discovery."""
    
    workspace_id: str
    db_config_id: str
    table_count: int
    total_columns: int
    total_foreign_keys: int
    cached: bool = False
    message: str


class GenerateVaultRequest(BaseModel):
    """Request to generate vault from cached schema."""
    
    db_config_id: str = "default"
    overwrite: bool = True


class GenerateVaultResponse(BaseModel):
    """Response from vault generation."""
    
    workspace_id: str
    vault_path: str
    tables_total: int
    files_created: int
    files_skipped: int
    errors: list[dict[str, Any]] = Field(default_factory=list)


class EnrichTableRequest(BaseModel):
    """Request to enrich a single table."""
    
    table_name: str
    description: str | None = None
    business_name: str | None = None
    keywords: list[str] | None = None
    columns: list[ColumnEnrichment] = Field(default_factory=list)
    relationships: list[RelationshipEnrichment] = Field(default_factory=list)
    business_owner: str | None = None
    data_domain: str | None = None
    update_frequency: str | None = None
    notes: str | None = None


class BulkEnrichRequest(BaseModel):
    """Request for bulk enrichment via JSON."""
    
    tables: list[TableEnrichment]


class ColumnDescriptionUpdate(BaseModel):
    """Simple column description update for frontend."""
    
    column_name: str
    description: str
    keywords: list[str] | None = None


class TableMetadataUpdate(BaseModel):
    """Simple table metadata update for frontend."""
    
    table_name: str
    description: str | None = None
    business_name: str | None = None
    keywords: list[str] | None = None
    data_domain: str | None = None
    columns: list[ColumnDescriptionUpdate] | None = None


class VaultTableResponse(BaseModel):
    """Response with table metadata for frontend display."""
    
    table_name: str
    description: str | None = None
    business_name: str | None = None
    keywords: list[str] = Field(default_factory=list)
    data_domain: str | None = None
    column_count: int = 0
    columns: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
# Schema Discovery endpoints
# ══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/schema/discover",
    response_model=DiscoverSchemaResponse,
    summary="Discover database schema",
)
async def discover_database_schema(
    request: DBConnectionRequest,
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> DiscoverSchemaResponse:
    """Introspect an external database and discover its schema.
    
    This connects to the specified database, reads table/column metadata,
    and caches the result. Use this before generating a vault.
    
    Requires admin role.
    """
    try:
        db_type = DatabaseType(request.db_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid db_type: {request.db_type}. Must be one of: postgresql, mysql, oracle, mssql",
        )
    
    config = DBConfig(
        db_type=db_type,
        host=request.host,
        port=request.port,
        database=request.database,
        username=request.username,
        password=request.password,
    )
    
    try:
        snapshot = await discover_schema_async(
            config=config,
            workspace_id=workspace_id,
            db_config_id=request.db_config_id,
            include_row_counts=request.include_row_counts,
        )
    except Exception as e:
        logger.exception("Schema discovery failed for workspace %s", workspace_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema discovery failed: {str(e)}",
        )
    
    # Cache the snapshot
    await set_schema(snapshot)
    
    return DiscoverSchemaResponse(
        workspace_id=workspace_id,
        db_config_id=request.db_config_id,
        table_count=snapshot.table_count,
        total_columns=snapshot.total_columns,
        total_foreign_keys=snapshot.total_foreign_keys,
        cached=True,
        message=f"Discovered {snapshot.table_count} tables with {snapshot.total_columns} columns",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Vault Generation endpoints
# ══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/vault/generate",
    response_model=GenerateVaultResponse,
    summary="Generate Obsidian vault from schema",
)
async def generate_vault_from_schema(
    request: GenerateVaultRequest,
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> GenerateVaultResponse:
    """Generate Obsidian vault files from a cached schema snapshot.
    
    First call /schema/discover to discover and cache the schema,
    then call this endpoint to generate the markdown files.
    
    Requires admin role.
    """
    from backend.app.schema_discovery.cache import get_schema
    
    snapshot = await get_schema(workspace_id, request.db_config_id)
    
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No cached schema found for workspace={workspace_id}, db_config_id={request.db_config_id}. "
                   f"Call POST /schema/discover first.",
        )
    
    settings = get_settings()
    vault_base_path = Path(settings.vault_base_path)
    
    try:
        stats = await generate_vault_async(
            snapshot=snapshot,
            vault_base_path=vault_base_path,
            overwrite=request.overwrite,
        )
    except Exception as e:
        logger.exception("Vault generation failed for workspace %s", workspace_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vault generation failed: {str(e)}",
        )
    
    return GenerateVaultResponse(
        workspace_id=workspace_id,
        vault_path=stats["vault_path"],
        tables_total=stats["tables_total"],
        files_created=stats["files_created"],
        files_skipped=stats["files_skipped"],
        errors=stats.get("errors", []),
    )


@router.post(
    "/vault/sync",
    summary="Synchronize Vault Markdown files with live DB Schema",
)
async def sync_vault_with_db(
    workspace_id: WorkspaceID,
    user: CurrentUser,
):
    """Sync Vault Markdown schemas by introspecting the live DB.

    Only available to admins. Uses the credentials saved in Tenant Config.
    """
    from backend.app.services.vault_sync import VaultSyncService
    from backend.app.models.database import CustomerDBConfig
    from backend.app.models.organization import Customer
    from backend.app.db.session import get_sessionmaker
    from sqlalchemy import select

    if not user.can_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to synchronize vault schemas"
        )

    try:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            customer = (await session.execute(
                select(Customer).where(Customer.slug == workspace_id)
            )).scalar_one_or_none()

            if not customer:
                raise HTTPException(status_code=404, detail="Workspace/Customer not found in DB")

            db_config = (await session.execute(
                select(CustomerDBConfig).where(CustomerDBConfig.customer_id == customer.id)
            )).scalar_one_or_none()

            if not db_config:
                raise HTTPException(
                    status_code=400,
                    detail="No database connection configured for this tenant. Please configure it in Tenant Settings first."
                )

            # We must decrypt the password before handing config to the executor
            from backend.app.services.crypto import decrypt_password
            from backend.app.db.models import DBConfig
            db_type_val = db_config.db_type.value if hasattr(db_config.db_type, "value") else str(db_config.db_type)
            safe_db_config = DBConfig(
                db_type=db_type_val,
                host=db_config.host,
                port=db_config.port,
                database=db_config.database,
                username=db_config.username,
                password=decrypt_password(db_config.encrypted_password),
                options=db_config.extra_params,
                max_row_limit=getattr(db_config, "max_row_limit", 1000)
            )

            sync_svc = VaultSyncService(workspace_id, safe_db_config)
            stats = await sync_svc.sync()

            return {
                "message": "Vault synchronization complete.",
                "stats": stats
            }

    except Exception as e:
        logger.exception("Vault sync failed")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

@router.post(
    "/vault/discover-and-generate",
    response_model=GenerateVaultResponse,
    summary="One-shot: discover schema and generate vault",
)
async def discover_and_generate_vault(
    request: DBConnectionRequest,
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
    overwrite: bool = True,
) -> GenerateVaultResponse:
    """Convenience endpoint that discovers schema and generates vault in one call.
    
    Combines /schema/discover and /vault/generate into a single operation.
    
    Requires admin role.
    """
    # First, discover
    discover_response = await discover_database_schema(
        request=request,
        workspace_id=workspace_id,
        user=user,
        _=None,
    )
    
    # Then generate
    generate_request = GenerateVaultRequest(
        db_config_id=request.db_config_id,
        overwrite=overwrite,
    )
    
    return await generate_vault_from_schema(
        request=generate_request,
        workspace_id=workspace_id,
        user=user,
        _=None,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Vault Enrichment endpoints
# ══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/vault/enrich",
    summary="Enrich a single table with metadata",
)
async def enrich_single_table(
    request: EnrichTableRequest,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> dict[str, Any]:
    """Add business metadata to a single table's vault file.
    
    Use this to add:
    - Column descriptions
    - Business-friendly names
    - Keywords for semantic search
    - Manual relationships (for tables without FK constraints)
    """
    settings = get_settings()
    vault_base_path = Path(settings.vault_base_path)
    
    enrichment = TableEnrichment(
        table_name=request.table_name,
        description=request.description,
        business_name=request.business_name,
        keywords=request.keywords,
        columns=request.columns,
        relationships=request.relationships,
        business_owner=request.business_owner,
        data_domain=request.data_domain,
        update_frequency=request.update_frequency,
        notes=request.notes,
    )
    
    result = enrich_vault_table(
        vault_base_path=vault_base_path,
        workspace_id=workspace_id,
        enrichment=enrichment,
    )
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Enrichment failed"),
        )
    
    return result


@router.post(
    "/vault/enrich/bulk",
    summary="Bulk enrich vault with JSON payload",
)
async def enrich_bulk_json(
    request: BulkEnrichRequest,
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Bulk enrich multiple tables via JSON payload.
    
    Use this to programmatically add metadata to multiple tables.
    
    Requires admin role.
    """
    settings = get_settings()
    vault_base_path = Path(settings.vault_base_path)
    
    payload = VaultEnrichmentPayload(
        workspace_id=workspace_id,
        source="api",
        tables=request.tables,
    )
    
    return enrich_vault_bulk(vault_base_path, payload)


@router.post(
    "/vault/enrich/excel",
    summary="Enrich vault from Excel file",
)
async def enrich_from_excel_upload(
    file: Annotated[UploadFile, File(description="Excel file with table/column metadata")],
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Upload an Excel file to enrich the vault with column descriptions.
    
    Expected format: Each sheet is a table name, with:
    - Column A: Column name
    - Column B: Column description
    
    The Excel file from the database documentation works directly.
    
    Requires admin role.
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an Excel file (.xlsx or .xls)",
        )
    
    settings = get_settings()
    vault_base_path = Path(settings.vault_base_path)
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        result = enrich_from_excel(
            excel_path=tmp_path,
            vault_base_path=vault_base_path,
            workspace_id=workspace_id,
        )
        return result
    except Exception as e:
        logger.exception("Excel enrichment failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Excel processing failed: {str(e)}",
        )
    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)


@router.post(
    "/vault/enrich/relationship",
    summary="Add a manual relationship between tables",
)
async def add_manual_relationship(
    source_table: str,
    source_column: str,
    target_table: str,
    target_column: str,
    relationship_type: str = "foreign_key",
    description: str | None = None,
    workspace_id: WorkspaceID = None,
    user: CurrentUser = None,
) -> dict[str, Any]:
    """Add a manual relationship between two tables.
    
    Use this for tables that don't have formal FK constraints
    but have logical relationships (e.g., CONTRNO in multiple tables).
    """
    settings = get_settings()
    vault_base_path = Path(settings.vault_base_path)
    
    enrichment = TableEnrichment(
        table_name=source_table,
        relationships=[
            RelationshipEnrichment(
                source_column=source_column,
                target_table=target_table,
                target_column=target_column,
                relationship_type=relationship_type,
                description=description,
            )
        ],
    )
    
    result = enrich_vault_table(
        vault_base_path=vault_base_path,
        workspace_id=workspace_id,
        enrichment=enrichment,
    )
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to add relationship"),
        )
    
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Frontend-friendly Vault Read/Update endpoints
# ══════════════════════════════════════════════════════════════════════════════


def _parse_vault_file_for_api(filepath: Path) -> dict[str, Any]:
    """Parse vault markdown file and return structured data for API."""
    import yaml
    
    content = filepath.read_text(encoding="utf-8")
    
    # Parse frontmatter
    frontmatter = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1].strip()) or {}
            body = parts[2].strip()
    
    # Extract columns from markdown table
    columns = []
    in_columns = False
    for line in body.split("\n"):
        if "## Columns" in line:
            in_columns = True
            continue
        if in_columns and line.strip().startswith("| Column"):
            continue  # header
        if in_columns and line.strip().startswith("|---"):
            continue  # separator
        if in_columns and line.strip().startswith("|"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                columns.append({
                    "name": parts[1],
                    "type": parts[2],
                    "nullable": parts[3] == "✓",
                    "is_pk": parts[4] == "✓",
                    "description": parts[5] if len(parts) > 5 else "",
                })
        elif in_columns and line.strip().startswith("##"):
            in_columns = False
    
    # Extract relationships
    relationships = []
    in_relationships = False
    for line in body.split("\n"):
        if "## Relationships" in line or "### Manual Relationships" in line:
            in_relationships = True
            continue
        if in_relationships and line.strip().startswith("- "):
            relationships.append({"raw": line.strip()[2:]})
        elif in_relationships and line.strip().startswith("##"):
            in_relationships = False
    
    # Keywords handling
    keywords = frontmatter.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.strip("[]").split(",")]
    
    return {
        "table_name": frontmatter.get("table", filepath.stem.upper()),
        "description": frontmatter.get("description"),
        "business_name": frontmatter.get("business_name"),
        "keywords": keywords,
        "data_domain": frontmatter.get("data_domain"),
        "column_count": len(columns),
        "columns": columns,
        "relationships": relationships,
        "enriched_at": frontmatter.get("enriched_at"),
        "generated_at": frontmatter.get("generated_at"),
    }


@router.get(
    "/vault/tables",
    summary="List all tables in the vault",
)
async def list_vault_tables(
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> list[dict[str, Any]]:
    """Get a list of all tables in the workspace vault.
    
    Returns basic info for each table (name, description, column count).
    Use GET /vault/tables/{table_name} for full details.
    """
    settings = get_settings()
    vault_path = Path(settings.vault_base_path) / workspace_id / "tables"
    
    if not vault_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vault not found for workspace: {workspace_id}",
        )
    
    tables = []
    for md_file in sorted(vault_path.glob("*.md")):
        try:
            data = _parse_vault_file_for_api(md_file)
            tables.append({
                "table_name": data["table_name"],
                "description": data["description"],
                "business_name": data["business_name"],
                "keywords": data["keywords"][:5] if data["keywords"] else [],  # Top 5
                "column_count": data["column_count"],
                "data_domain": data["data_domain"],
            })
        except Exception as e:
            logger.warning("Failed to parse %s: %s", md_file, e)
    
    return tables


@router.get(
    "/vault/tables/{table_name}",
    response_model=VaultTableResponse,
    summary="Get table details from vault",
)
async def get_vault_table(
    table_name: str,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> VaultTableResponse:
    """Get full details for a specific table including all columns and metadata."""
    settings = get_settings()
    vault_path = Path(settings.vault_base_path) / workspace_id / "tables"
    filepath = vault_path / f"{table_name.lower()}.md"
    
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table not found: {table_name}",
        )
    
    data = _parse_vault_file_for_api(filepath)
    return VaultTableResponse(**data)


@router.patch(
    "/vault/tables/{table_name}",
    summary="Update table metadata",
)
async def update_vault_table(
    table_name: str,
    update: TableMetadataUpdate,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> dict[str, Any]:
    """Update table and column metadata.
    
    Frontend-friendly endpoint for editing vault content.
    Only provided fields are updated (PATCH semantics).
    """
    settings = get_settings()
    vault_base_path = Path(settings.vault_base_path)
    
    # Convert to enrichment format
    columns = []
    if update.columns:
        for col in update.columns:
            columns.append(ColumnEnrichment(
                name=col.column_name,
                description=col.description,
                keywords=col.keywords,
            ))
    
    enrichment = TableEnrichment(
        table_name=table_name,
        description=update.description,
        business_name=update.business_name,
        keywords=update.keywords,
        data_domain=update.data_domain,
        columns=columns,
    )
    
    result = enrich_vault_table(
        vault_base_path=vault_base_path,
        workspace_id=workspace_id,
        enrichment=enrichment,
    )
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Update failed"),
        )
    
    return result


@router.patch(
    "/vault/tables/{table_name}/columns/{column_name}",
    summary="Update single column description",
)
async def update_column_description(
    table_name: str,
    column_name: str,
    update: ColumnDescriptionUpdate,
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> dict[str, Any]:
    """Update description for a single column.
    
    Simplest endpoint for inline editing in the frontend.
    """
    settings = get_settings()
    vault_base_path = Path(settings.vault_base_path)
    
    enrichment = TableEnrichment(
        table_name=table_name,
        description="",  # Mute missing parameter warnings
        business_name=None,
        keywords=[],
        business_owner=None,
        data_domain=None,
        update_frequency=None,
        columns=[ColumnEnrichment(
            name=column_name,
            description=update.description,
            keywords=update.keywords or [],
            business_name=None,
            example_values=[],
            is_sensitive=False,
            notes=None,
        )],
    )
    
    result = enrich_vault_table(
        vault_base_path=vault_base_path,
        workspace_id=workspace_id,
        enrichment=enrichment,
    )
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Update failed"),
        )
    
    return {
        "status": "success",
        "table": table_name,
        "column": column_name,
        "description": update.description,
    }
