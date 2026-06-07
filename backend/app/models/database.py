"""External database configuration and schema relationship models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin
from backend.app.models.enums import DatabaseType


class CustomerDBConfig(Base, UUIDMixin, TimestampMixin):
    """Connection configuration for a customer's external database."""

    __tablename__ = "customer_db_configs"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    db_type: Mapped[DatabaseType] = mapped_column(nullable=False)
    host: Mapped[str] = mapped_column(String(512), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    database: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False, comment="Encrypted at rest")
    ssl_mode: Mapped[str | None] = mapped_column(String(50), default="prefer")
    extra_params: Mapped[dict | None] = mapped_column(JSONB, default=None, comment="Extra connection params as JSON")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # relationships
    customer: Mapped["Customer"] = relationship(back_populates="db_configs")

    def __repr__(self) -> str:
        return f"<CustomerDBConfig {self.name} [{self.db_type.value}]>"


class SchemaRelationship(Base, UUIDMixin):
    """Discovered or manually defined relationship between external-DB tables."""

    __tablename__ = "schema_relationships"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    db_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_db_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_table: Mapped[str] = mapped_column(String(512), nullable=False)
    source_column: Mapped[str] = mapped_column(String(512), nullable=False)
    target_table: Mapped[str] = mapped_column(String(512), nullable=False)
    target_column: Mapped[str] = mapped_column(String(512), nullable=False)
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        default="inferred",
        server_default="inferred",
        comment="one_to_one, one_to_many, many_to_many, inferred",
    )
    confidence: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0.0", comment="0.0 – 1.0 confidence score"
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    def __repr__(self) -> str:
        return f"<SchemaRel {self.source_table}.{self.source_column} → {self.target_table}.{self.target_column}>"
