"""Schema discovery data models.

Pydantic models and dataclasses for representing discovered database
schema snapshots. These are JSON-serializable for Redis caching.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ColumnInfo(BaseModel):
    """Column metadata discovered from an external database."""

    name: str
    data_type: str
    nullable: bool = True
    is_primary_key: bool = False
    comment: str | None = None


class ForeignKeyInfo(BaseModel):
    """A foreign key relationship between two tables."""

    source_table: str
    source_column: str
    target_table: str
    target_column: str
    constraint_name: str | None = None


class TableInfo(BaseModel):
    """Complete table metadata including columns and foreign keys."""

    name: str
    schema_name: str | None = None
    columns: list[ColumnInfo] = Field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = Field(default_factory=list)
    row_count_estimate: int | None = None


class SchemaSnapshot(BaseModel):
    """A point-in-time snapshot of a database schema.

    This is the top-level object stored in Redis cache.
    """

    workspace_id: str
    db_config_id: str
    db_type: str
    database_name: str
    tables: list[TableInfo] = Field(default_factory=list)
    discovered_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def total_columns(self) -> int:
        return sum(len(t.columns) for t in self.tables)

    @property
    def total_foreign_keys(self) -> int:
        return sum(len(t.foreign_keys) for t in self.tables)
