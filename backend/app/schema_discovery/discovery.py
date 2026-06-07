"""Database schema introspection for different database backends.

This module provides the actual discovery logic — connecting to external
databases and extracting table/column/FK metadata. Each backend has its
own SQL dialect for information_schema queries.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.db.executor import get_executor
from backend.app.db.models import DatabaseType, DBConfig
from backend.app.schema_discovery.models import (
    ColumnInfo,
    ForeignKeyInfo,
    SchemaSnapshot,
    TableInfo,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Backend-specific introspection queries
# ══════════════════════════════════════════════════════════════════════════════

# PostgreSQL uses information_schema
_POSTGRES_TABLES_SQL = """
SELECT 
    table_name,
    table_schema
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND table_type = 'BASE TABLE'
ORDER BY table_schema, table_name
"""

_POSTGRES_COLUMNS_SQL = """
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = :schema_name AND table_name = :table_name
ORDER BY ordinal_position
"""

_POSTGRES_PKS_SQL = """
SELECT kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
  ON tc.constraint_name = kcu.constraint_name 
  AND tc.table_schema = kcu.table_schema
WHERE tc.table_schema = :schema_name 
  AND tc.table_name = :table_name 
  AND tc.constraint_type = 'PRIMARY KEY'
"""

_POSTGRES_FKS_SQL = """
SELECT
    kcu.column_name AS source_column,
    ccu.table_name AS target_table,
    ccu.column_name AS target_column,
    tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.table_schema = :schema_name
  AND tc.table_name = :table_name
  AND tc.constraint_type = 'FOREIGN KEY'
"""

_POSTGRES_ROW_COUNT_SQL = """
SELECT reltuples::bigint AS estimate
FROM pg_class
WHERE relname = :table_name
"""

# Oracle uses USER_* / ALL_* views
_ORACLE_TABLES_SQL = """
SELECT table_name, NULL as table_schema
FROM user_tables
ORDER BY table_name
"""

_ORACLE_COLUMNS_SQL = """
SELECT 
    column_name,
    data_type,
    CASE WHEN nullable = 'Y' THEN 'YES' ELSE 'NO' END AS is_nullable,
    data_default,
    column_id AS ordinal_position
FROM user_tab_columns
WHERE table_name = :table_name
ORDER BY column_id
"""

_ORACLE_PKS_SQL = """
SELECT cols.column_name
FROM user_constraints cons
JOIN user_cons_columns cols ON cons.constraint_name = cols.constraint_name
WHERE cons.table_name = :table_name
  AND cons.constraint_type = 'P'
ORDER BY cols.position
"""

_ORACLE_FKS_SQL = """
SELECT 
    a.column_name AS source_column,
    c_pk.table_name AS target_table,
    b.column_name AS target_column,
    a.constraint_name
FROM user_cons_columns a
JOIN user_constraints c ON a.constraint_name = c.constraint_name
JOIN user_constraints c_pk ON c.r_constraint_name = c_pk.constraint_name
JOIN user_cons_columns b ON c_pk.constraint_name = b.constraint_name AND a.position = b.position
WHERE c.table_name = :table_name
  AND c.constraint_type = 'R'
"""

_ORACLE_ROW_COUNT_SQL = """
SELECT num_rows AS estimate
FROM user_tables
WHERE table_name = :table_name
"""

# MySQL uses information_schema
_MYSQL_TABLES_SQL = """
SELECT 
    table_name,
    table_schema
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_type = 'BASE TABLE'
ORDER BY table_name
"""

_MYSQL_COLUMNS_SQL = """
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = DATABASE() AND table_name = :table_name
ORDER BY ordinal_position
"""

_MYSQL_PKS_SQL = """
SELECT column_name
FROM information_schema.key_column_usage
WHERE table_schema = DATABASE()
  AND table_name = :table_name
  AND constraint_name = 'PRIMARY'
ORDER BY ordinal_position
"""

_MYSQL_FKS_SQL = """
SELECT
    kcu.column_name AS source_column,
    kcu.referenced_table_name AS target_table,
    kcu.referenced_column_name AS target_column,
    kcu.constraint_name
FROM information_schema.key_column_usage kcu
WHERE kcu.table_schema = DATABASE()
  AND kcu.table_name = :table_name
  AND kcu.referenced_table_name IS NOT NULL
"""

_MYSQL_ROW_COUNT_SQL = """
SELECT table_rows AS estimate
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name = :table_name
"""

# MSSQL uses INFORMATION_SCHEMA and sys views
_MSSQL_TABLES_SQL = """
SELECT 
    table_name,
    table_schema
FROM information_schema.tables
WHERE table_type = 'BASE TABLE'
  AND table_schema NOT IN ('sys', 'INFORMATION_SCHEMA')
ORDER BY table_schema, table_name
"""

_MSSQL_COLUMNS_SQL = """
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = :schema_name AND table_name = :table_name
ORDER BY ordinal_position
"""

_MSSQL_PKS_SQL = """
SELECT ccu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.constraint_column_usage ccu
  ON tc.constraint_name = ccu.constraint_name
WHERE tc.table_schema = :schema_name
  AND tc.table_name = :table_name
  AND tc.constraint_type = 'PRIMARY KEY'
"""

_MSSQL_FKS_SQL = """
SELECT
    kcu.column_name AS source_column,
    ccu.table_name AS target_table,
    ccu.column_name AS target_column,
    tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.referential_constraints rc
  ON tc.constraint_name = rc.constraint_name
JOIN information_schema.constraint_column_usage ccu
  ON rc.unique_constraint_name = ccu.constraint_name
WHERE tc.table_schema = :schema_name
  AND tc.table_name = :table_name
  AND tc.constraint_type = 'FOREIGN KEY'
"""

_MSSQL_ROW_COUNT_SQL = """
SELECT SUM(p.rows) AS estimate
FROM sys.tables t
JOIN sys.partitions p ON t.object_id = p.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE s.name = :schema_name
  AND t.name = :table_name
  AND p.index_id IN (0, 1)
"""


# ══════════════════════════════════════════════════════════════════════════════
# Discovery functions
# ══════════════════════════════════════════════════════════════════════════════


def _get_queries(db_type: DatabaseType) -> dict[str, str]:
    """Return the correct SQL queries for the given database type."""
    if db_type == DatabaseType.POSTGRESQL:
        return {
            "tables": _POSTGRES_TABLES_SQL,
            "columns": _POSTGRES_COLUMNS_SQL,
            "pks": _POSTGRES_PKS_SQL,
            "fks": _POSTGRES_FKS_SQL,
            "row_count": _POSTGRES_ROW_COUNT_SQL,
        }
    elif db_type == DatabaseType.ORACLE:
        return {
            "tables": _ORACLE_TABLES_SQL,
            "columns": _ORACLE_COLUMNS_SQL,
            "pks": _ORACLE_PKS_SQL,
            "fks": _ORACLE_FKS_SQL,
            "row_count": _ORACLE_ROW_COUNT_SQL,
        }
    elif db_type == DatabaseType.MYSQL:
        return {
            "tables": _MYSQL_TABLES_SQL,
            "columns": _MYSQL_COLUMNS_SQL,
            "pks": _MYSQL_PKS_SQL,
            "fks": _MYSQL_FKS_SQL,
            "row_count": _MYSQL_ROW_COUNT_SQL,
        }
    elif db_type == DatabaseType.MSSQL:
        return {
            "tables": _MSSQL_TABLES_SQL,
            "columns": _MSSQL_COLUMNS_SQL,
            "pks": _MSSQL_PKS_SQL,
            "fks": _MSSQL_FKS_SQL,
            "row_count": _MSSQL_ROW_COUNT_SQL,
        }
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def discover_schema(
    config: DBConfig,
    workspace_id: str,
    db_config_id: str,
    include_row_counts: bool = True,
) -> SchemaSnapshot:
    """Discover database schema by introspecting the target database.
    
    Args:
        config: Database connection configuration
        workspace_id: The workspace this schema belongs to
        db_config_id: Identifier for this database configuration
        include_row_counts: Whether to fetch estimated row counts (can be slow)
        
    Returns:
        A complete SchemaSnapshot with all tables, columns, and foreign keys.
    """
    executor = get_executor(config)
    queries = _get_queries(config.db_type)
    
    logger.info(
        "Discovering schema for %s://%s:%d/%s",
        config.db_type.value,
        config.host,
        config.get_port(),
        config.database,
    )
    
    # 1. Get all tables
    tables_result = executor.execute(queries["tables"])
    logger.info("Found %d tables", len(tables_result))
    
    tables: list[TableInfo] = []
    
    for table_row in tables_result:
        table_name = table_row.get("TABLE_NAME") or table_row.get("table_name")
        schema_name = table_row.get("TABLE_SCHEMA") or table_row.get("table_schema")
        
        if not table_name:
            continue
            
        # 2. Get columns for this table
        col_params = {"table_name": table_name}
        if schema_name and config.db_type != DatabaseType.ORACLE:
            col_params["schema_name"] = schema_name
            
        columns_result = executor.execute(queries["columns"], col_params)
        
        # 3. Get primary keys
        pk_params = {"table_name": table_name}
        if schema_name and config.db_type != DatabaseType.ORACLE:
            pk_params["schema_name"] = schema_name
        pk_result = executor.execute(queries["pks"], pk_params)
        pk_columns = {
            (r.get("COLUMN_NAME") or r.get("column_name"))
            for r in pk_result
        }
        
        # Build column list
        columns: list[ColumnInfo] = []
        for col_row in columns_result:
            col_name = col_row.get("COLUMN_NAME") or col_row.get("column_name")
            data_type = col_row.get("DATA_TYPE") or col_row.get("data_type")
            is_nullable = (col_row.get("IS_NULLABLE") or col_row.get("is_nullable")) in ("YES", "Y", True)
            
            columns.append(ColumnInfo(
                name=col_name,
                data_type=data_type.upper() if data_type else "UNKNOWN",
                nullable=is_nullable,
                is_primary_key=col_name in pk_columns,
            ))
        
        # 4. Get foreign keys
        fk_params = {"table_name": table_name}
        if schema_name and config.db_type != DatabaseType.ORACLE:
            fk_params["schema_name"] = schema_name
        fk_result = executor.execute(queries["fks"], fk_params)
        
        foreign_keys: list[ForeignKeyInfo] = []
        for fk_row in fk_result:
            foreign_keys.append(ForeignKeyInfo(
                source_table=table_name,
                source_column=fk_row.get("SOURCE_COLUMN") or fk_row.get("source_column"),
                target_table=fk_row.get("TARGET_TABLE") or fk_row.get("target_table"),
                target_column=fk_row.get("TARGET_COLUMN") or fk_row.get("target_column"),
                constraint_name=fk_row.get("CONSTRAINT_NAME") or fk_row.get("constraint_name"),
            ))
        
        # 5. Get row count estimate (optional)
        row_count = None
        if include_row_counts:
            try:
                rc_params = {"table_name": table_name}
                if schema_name and config.db_type not in (DatabaseType.ORACLE, DatabaseType.MYSQL):
                    rc_params["schema_name"] = schema_name
                rc_result = executor.execute(queries["row_count"], rc_params)
                if rc_result:
                    row_count = rc_result[0].get("ESTIMATE") or rc_result[0].get("estimate")
                    if row_count is not None:
                        row_count = int(row_count)
            except Exception as e:
                logger.warning("Could not get row count for %s: %s", table_name, e)
        
        tables.append(TableInfo(
            name=table_name,
            schema_name=schema_name,
            columns=columns,
            foreign_keys=foreign_keys,
            row_count_estimate=row_count,
        ))
    
    snapshot = SchemaSnapshot(
        workspace_id=workspace_id,
        db_config_id=db_config_id,
        db_type=config.db_type.value,
        database_name=config.database,
        tables=tables,
        metadata={
            "host": config.host,
            "port": config.get_port(),
        },
    )
    
    logger.info(
        "Schema discovery complete: %d tables, %d columns, %d foreign keys",
        snapshot.table_count,
        snapshot.total_columns,
        snapshot.total_foreign_keys,
    )
    
    return snapshot


async def discover_schema_async(
    config: DBConfig,
    workspace_id: str,
    db_config_id: str,
    include_row_counts: bool = True,
) -> SchemaSnapshot:
    """Async wrapper for discover_schema (runs in thread pool)."""
    import asyncio
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: discover_schema(config, workspace_id, db_config_id, include_row_counts),
    )
