"""Workspace management API endpoints.

Provides endpoints for:
- Schema discovery (introspect external database)
- Vault generation (create Obsidian knowledge base)
- Vault enrichment (add metadata from Excel/JSON)
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.app.auth.dependencies import CurrentUser, WorkspaceID
from backend.app.auth.models import Role
from backend.app.auth.rbac import require_role
from backend.app.core.config import get_settings
from backend.app.db.models import DatabaseType, DBConfig
from backend.app.schema_discovery.cache import set_schema
from backend.app.schema_discovery.discovery import discover_schema_async
from backend.app.schema_discovery.enrichment import (
    ColumnEnrichment,
    RelationshipEnrichment,
    TableEnrichment,
    VaultEnrichmentPayload,
    add_example_query,
    enrich_from_excel,
    enrich_from_metadata_json,
    enrich_vault_bulk,
    enrich_vault_table,
    parse_example_queries,
    remove_example_query,
    remove_relationship,
)
from backend.app.schema_discovery.suggestions import generate_vault_suggestions
from backend.app.schema_discovery.vault_generator import (
    generate_vault_async,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


# ══════════════════════════════════════════════════════════════════════════════
# Request/Response models
# ══════════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field  # noqa: E402


class VaultSyncRequest(BaseModel):
    """Optional body for POST /vault/sync to scope enum sampling."""

    tables: list[str] | None = Field(
        None, description="Explicit table names to scope enum sampling to."
    )
    active_only: bool = Field(
        False,
        description="Scope to the union of active TeamVaultPolicy.allowed_tables.",
    )


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
    # Without these, the response_model silently drops them from the payload even
    # though _parse_vault_file_for_api populates them — the bug that hid curated
    # Example Queries from the admin UI.
    example_queries: list[dict[str, Any]] = Field(default_factory=list)
    enriched_at: str | None = None
    generated_at: str | None = None


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
        ) from None

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
        ) from e

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

        # Background task to generate dynamic suggestions for the frontend
        asyncio.create_task(generate_vault_suggestions(snapshot, vault_base_path))
    except Exception as e:
        logger.exception("Vault generation failed for workspace %s", workspace_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vault generation failed: {str(e)}",
        ) from e

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
    body: VaultSyncRequest | None = None,
):
    """Sync Vault Markdown schemas by introspecting the live DB.

    Only available to admins. Uses the credentials saved in Tenant Config.

    Optional JSON body scopes the expensive enum sampling:
    - ``{"tables": [...]}``   — sample only these tables (explicit, highest precedence)
    - ``{"active_only": true}`` — sample only the union of active TeamVaultPolicy
      allowed_tables; falls back to a full sync (with a warning) if none exist
    - no body                  — full sync (back-compat)
    """
    from sqlalchemy import select

    from backend.app.db.session import get_sessionmaker
    from backend.app.models.database import CustomerDBConfig
    from backend.app.models.organization import Customer
    from backend.app.query.pipeline import get_active_tables
    from backend.app.services.vault_sync import VaultSyncService

    if not user.can_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to synchronize vault schemas",
        )

    try:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            customer = (
                await session.execute(select(Customer).where(Customer.slug == workspace_id))
            ).scalar_one_or_none()

            if not customer:
                raise HTTPException(status_code=404, detail="Workspace/Customer not found in DB")

            db_config = (
                await session.execute(
                    select(CustomerDBConfig).where(CustomerDBConfig.customer_id == customer.id)
                )
            ).scalar_one_or_none()

            if not db_config:
                raise HTTPException(
                    status_code=400,
                    detail="No database connection configured for this tenant. Please configure it in Tenant Settings first.",
                )

            # We must decrypt the password before handing config to the executor
            from backend.app.db.models import DBConfig
            from backend.app.services.crypto import async_decrypt_password

            db_type_val = (
                db_config.db_type.value
                if hasattr(db_config.db_type, "value")
                else str(db_config.db_type)
            )
            safe_db_config = DBConfig(
                db_type=db_type_val,
                host=db_config.host,
                port=db_config.port,
                database=db_config.database,
                username=db_config.username,
                password=await async_decrypt_password(
                    db_config.encrypted_password, db_config.customer_id, session
                ),
                options=db_config.extra_params,
                max_row_limit=getattr(db_config, "max_row_limit", 1000),
            )

            # Resolve table scope: explicit list > active_only > full.
            active_tables: set[str] | None = None
            if body and body.tables:
                active_tables = {t.lower() for t in body.tables}
            elif body and body.active_only:
                active_tables = await get_active_tables(workspace_id, session)
                if not active_tables:
                    logger.warning(
                        "active_only sync requested for %s but no active policy "
                        "tables found; falling back to full sync",
                        workspace_id,
                    )
                    active_tables = None

            sync_svc = VaultSyncService(workspace_id, safe_db_config)
            stats = await sync_svc.sync(active_tables=active_tables)

            return {"message": "Vault synchronization complete.", "stats": stats}

    except Exception as e:
        logger.exception("Vault sync failed")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}") from e


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
    await discover_database_schema(
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
        ) from e
    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)


@router.post(
    "/vault/import-metadata",
    summary="Import extracted DB metadata JSON (from extract-db-metadata.py) into the vault",
)
async def import_metadata_upload(
    file: Annotated[UploadFile, File(description="JSON produced by extract-db-metadata.py")],
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Upload the JSON produced offline by ``scripts/extract-db-metadata.py``.

    Applies descriptions / keywords / column descriptions / relationships AND
    writes enum-value blocks per table. Re-indexes embeddings afterward so
    semantic retrieval reflects the new metadata. Requires admin role.
    """
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a .json file produced by extract-db-metadata.py",
        )

    settings = get_settings()
    vault_base_path = Path(settings.vault_base_path)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = enrich_from_metadata_json(
            json_path=tmp_path,
            vault_base_path=vault_base_path,
            workspace_id=workspace_id,
        )
        # Best-effort embedding refresh (hash-idempotent — only changed md re-embed).
        try:
            from backend.app.services.vault_retrieval import index_workspace_vault

            result["embeddings"] = await index_workspace_vault(workspace_id)
        except Exception as embed_err:  # noqa: BLE001
            logger.warning("Embedding refresh after import failed: %s", embed_err)
            result["embeddings"] = {"error": str(embed_err)}
        return result
    except Exception as e:
        logger.exception("Metadata import failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Metadata import failed: {str(e)}",
        ) from e
    finally:
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
    # Reject empty parts — otherwise a blank `` -> `.` relationship gets written.
    if not (
        source_table.strip()
        and source_column.strip()
        and target_table.strip()
        and target_column.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_table, source_column, target_table and target_column are all required.",
        )

    settings = get_settings()
    vault_base_path = Path(settings.vault_base_path)

    enrichment = TableEnrichment(
        table_name=source_table,
        relationships=[
            RelationshipEnrichment(
                source_column=source_column.strip(),
                target_table=target_table.strip(),
                target_column=target_column.strip(),
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


class JoinKeysSaveRequest(BaseModel):
    """Curated conformed join keys: which shared columns are real join keys."""

    keys: list[dict[str, Any]] = Field(default_factory=list)


@router.get(
    "/vault/join-keys",
    summary="List conformed join-key candidates (shared columns) + curation",
)
async def list_join_keys(
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> dict[str, Any]:
    """Columns shared by >= 2 tables, merged with saved is_join_key/grain/note."""
    from backend.app.services.vault_join_keys import get_join_keys

    return {"workspace_id": workspace_id, "keys": get_join_keys(workspace_id)}


@router.put(
    "/vault/join-keys",
    summary="Save curated conformed join keys",
)
async def save_join_keys(
    request: JoinKeysSaveRequest,
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    from backend.app.services.vault_join_keys import save_curation

    result = save_curation(workspace_id, request.keys)
    return {"workspace_id": workspace_id, **result}


@router.post(
    "/vault/join-keys/infer-grains",
    summary="LLM-infer free-text grain for shared columns (vault processing)",
)
async def infer_join_key_grains(
    workspace_id: WorkspaceID,
    user: CurrentUser,
    overwrite: bool = False,
    _: None = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Fill each shared column's grain via the LLM (only empty ones unless overwrite)."""
    from backend.app.db.session import get_sessionmaker
    from backend.app.services.llm_resolver import resolve_llm
    from backend.app.services.vault_join_keys import get_join_keys, infer_grains

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        llm = await resolve_llm(workspace_id, session, operation="suggestion")
    result = await infer_grains(workspace_id, llm=llm, overwrite=overwrite)
    return {"workspace_id": workspace_id, **result, "keys": get_join_keys(workspace_id)}


class ExampleQueryRequest(BaseModel):
    """A natural-language question + optional explanation + its SQL."""

    source_table: str
    question: str
    sql: str
    answer: str = ""


@router.post(
    "/vault/example-query",
    summary="Add an example question→SQL to a table",
)
async def add_example_query_endpoint(
    request: ExampleQueryRequest,
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    settings = get_settings()
    result = add_example_query(
        vault_base_path=Path(settings.vault_base_path),
        workspace_id=workspace_id,
        table_name=request.source_table,
        question=request.question,
        sql=request.sql,
        answer=request.answer,
    )
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to add example query"),
        )
    return result


@router.delete(
    "/vault/example-query",
    summary="Remove an example query from a table (matched by question)",
)
async def delete_example_query_endpoint(
    source_table: str,
    question: str,
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    settings = get_settings()
    result = remove_example_query(
        vault_base_path=Path(settings.vault_base_path),
        workspace_id=workspace_id,
        table_name=source_table,
        question=question,
    )
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to remove example query"),
        )
    return result


@router.delete(
    "/vault/relationship",
    summary="Remove a manual relationship from a table",
)
async def delete_manual_relationship(
    source_table: str,
    raw: str,
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Remove a relationship bullet (matched by its rendered ``raw`` text)."""
    settings = get_settings()
    result = remove_relationship(
        vault_base_path=Path(settings.vault_base_path),
        workspace_id=workspace_id,
        table_name=source_table,
        raw=raw,
    )
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to remove relationship"),
        )
    return result


# ══════════════════════════════════════════════════════════════════════════════
# LLM-assisted metadata backfill (draft → review → apply)
# ══════════════════════════════════════════════════════════════════════════════


class LLMEnrichRequest(BaseModel):
    """Generate LLM draft enrichment for (empty) table metadata."""

    tables: list[str] = Field(
        default_factory=list, description="Empty → active-table union → all vault"
    )
    mode: str = Field("fill_empty", description="fill_empty | overwrite")
    fields: list[str] | None = Field(
        None, description="Subset of description/keywords/columns/relationships"
    )


class LLMEnrichApplyRequest(BaseModel):
    """Apply (possibly edited) LLM drafts to the vault."""

    drafts: list[dict[str, Any]] = Field(default_factory=list)
    mode: str = "fill_empty"
    fields: list[str] | None = None


def _list_vault_table_names(workspace_id: str) -> list[str]:
    settings = get_settings()
    tables_dir = Path(settings.vault_base_path) / workspace_id / "tables"
    if not tables_dir.exists():
        return []
    return sorted(p.stem for p in tables_dir.glob("*.md"))


_LLM_ENRICH_MAX_TABLES = 50


@router.post(
    "/vault/enrich/llm",
    summary="Generate LLM draft enrichment for empty table metadata (no write)",
)
async def enrich_vault_llm(
    request: LLMEnrichRequest,
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Return review DRAFTS — does NOT write. Default scope = active-table union."""
    from backend.app.db.session import get_sessionmaker
    from backend.app.query.pipeline import get_active_tables
    from backend.app.services.llm_resolver import resolve_llm
    from backend.app.services.vault_llm_enrich import generate_table_enrichment

    all_names = _list_vault_table_names(workspace_id)
    targets = list(request.tables)
    if not targets:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            active = await get_active_tables(workspace_id, session)
        targets = [n for n in all_names if n.lower() in active] if active else all_names

    truncated = len(targets) > _LLM_ENRICH_MAX_TABLES
    remaining = targets[_LLM_ENRICH_MAX_TABLES:] if truncated else []
    targets = targets[:_LLM_ENRICH_MAX_TABLES]

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        llm = await resolve_llm(workspace_id, session)

    sem = asyncio.Semaphore(5)

    async def _one(name: str):
        async with sem:
            return await generate_table_enrichment(
                workspace_id=workspace_id,
                table_name=name,
                mode=request.mode,
                fields=request.fields,
                llm=llm,
                neighbor_tables=all_names,
            )

    drafts = await asyncio.gather(*[_one(n) for n in targets])
    return {
        "workspace_id": workspace_id,
        "mode": request.mode,
        "drafts": [d.model_dump() for d in drafts],
        "truncated": truncated,
        "remaining": remaining,
    }


@router.post(
    "/vault/enrich/llm/apply",
    summary="Apply reviewed LLM enrichment drafts to the vault",
)
async def apply_vault_llm(
    request: LLMEnrichApplyRequest,
    workspace_id: WorkspaceID,
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Write reviewed drafts via the existing enrich_vault_table merge path."""
    from backend.app.services.vault_llm_enrich import (
        TableEnrichmentDraft,
        draft_to_enrichment,
    )

    settings = get_settings()
    vault_base_path = Path(settings.vault_base_path)

    results = []
    success = 0
    for raw in request.drafts:
        try:
            draft = TableEnrichmentDraft(**raw)
            enrichment = draft_to_enrichment(draft, request.mode, request.fields)
            res = enrich_vault_table(
                vault_base_path=vault_base_path,
                workspace_id=workspace_id,
                enrichment=enrichment,
            )
            results.append(res)
            if res.get("status") != "error":
                success += 1
        except Exception as e:  # noqa: BLE001
            results.append(
                {"table": raw.get("table_name", "?"), "status": "error", "error": str(e)}
            )

    # Refresh embeddings so retrieval reflects the new metadata (best-effort).
    try:
        from backend.app.services.vault_retrieval import index_workspace_vault

        await index_workspace_vault(workspace_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("Embedding refresh after LLM apply failed: %s", e)

    return {
        "workspace_id": workspace_id,
        "tables_processed": len(request.drafts),
        "success_count": success,
        "error_count": len(request.drafts) - success,
        "results": results,
    }


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
                columns.append(
                    {
                        "name": parts[1],
                        "type": parts[2],
                        "nullable": parts[3] == "✓",
                        "is_pk": parts[4] == "✓",
                        "description": parts[5] if len(parts) > 5 else "",
                    }
                )
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
        "example_queries": parse_example_queries(filepath),
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
            tables.append(
                {
                    "table_name": data["table_name"],
                    "description": data["description"],
                    "business_name": data["business_name"],
                    "keywords": data["keywords"][:5] if data["keywords"] else [],  # Top 5
                    "column_count": data["column_count"],
                    "data_domain": data["data_domain"],
                }
            )
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
            columns.append(
                ColumnEnrichment(
                    name=col.column_name,
                    description=col.description,
                    keywords=col.keywords,
                )
            )

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
        # Explicit user edit: replace keywords with exactly what the editor sent
        # (None = untouched, [] = cleared) so deletions stick instead of being
        # re-unioned with the old set.
        replace_keywords=True,
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
        columns=[
            ColumnEnrichment(
                name=column_name,
                description=update.description,
                keywords=update.keywords or [],
                business_name=None,
                example_values=[],
                is_sensitive=False,
                notes=None,
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
            detail=result.get("error", "Update failed"),
        )

    return {
        "status": "success",
        "table": table_name,
        "column": column_name,
        "description": update.description,
    }


@router.get(
    "/{workspace_id}/suggestions",
    summary="Get dynamic chat suggestions",
)
async def get_workspace_suggestions(
    workspace_id: WorkspaceID,
    user: CurrentUser,
) -> list[str]:
    """Return auto-generated sample questions for the workspace schema."""
    settings = get_settings()
    suggestions_file = Path(settings.vault_base_path) / workspace_id / "suggestions.json"

    if suggestions_file.exists():
        try:
            import json

            with open(suggestions_file) as f:
                return json.load(f)
        except Exception:
            pass

    # Fallback if not generated yet
    return [
        "Show monthly revenue by region",
        "Top 10 customers by volume",
        "Daily active users trend",
    ]
