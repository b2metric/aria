"""External database configuration and schema relationship models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin
from backend.app.models.enums import DatabaseType, LLMProvider

if TYPE_CHECKING:
    from backend.app.models.organization import Customer


class CustomerDBConfig(Base, UUIDMixin, TimestampMixin):
    """Connection configuration for a customer's external database."""

    __tablename__ = "customer_db_configs"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    db_type: Mapped[DatabaseType] = mapped_column(
        postgresql.ENUM(
            "postgresql",
            "mysql",
            "oracle",
            "bigquery",
            "snowflake",
            "redshift",
            "mssql",
            name="database_type",
            create_type=False,
        ),
        nullable=False,
    )
    host: Mapped[str] = mapped_column(String(512), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    database: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Encrypted at rest"
    )
    ssl_mode: Mapped[str | None] = mapped_column(String(50), default="prefer")
    extra_params: Mapped[dict | None] = mapped_column(
        JSONB, default=None, comment="Extra connection params as JSON"
    )
    max_row_limit: Mapped[int] = mapped_column(
        Integer,
        default=1000,
        server_default="1000",
        comment="Hard limit for rows returned per query",
    )
    max_export_row_limit: Mapped[int] = mapped_column(
        Integer,
        default=100_000,
        server_default="100000",
        comment="Max rows written to a CSV export artifact (export ceiling)",
    )
    export_batch_size: Mapped[int] = mapped_column(
        Integer,
        default=50_000,
        server_default="50000",
        comment="Rows fetched per batch when streaming an export",
    )
    export_link_ttl_days: Mapped[int] = mapped_column(
        Integer,
        default=3,
        server_default="3",
        comment="Days an exported CSV stays downloadable before it expires",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # relationships
    customer: Mapped["Customer"] = relationship(back_populates="db_configs")

    def __repr__(self) -> str:
        return f"<CustomerDBConfig {self.name} [{self.db_type.value}]>"


class CustomerLLMConfig(Base, UUIDMixin, TimestampMixin):
    """LLM provider configuration for a customer's BYOK implementation."""

    __tablename__ = "customer_llm_configs"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[LLMProvider] = mapped_column(
        postgresql.ENUM(
            "openai",
            "azure",
            "anthropic",
            "gemini",
            "litellm",
            name="llm_provider",
            create_type=False,
        ),
        nullable=False,
    )
    upstream_api_base: Mapped[str | None] = mapped_column(String(512), nullable=True)
    encrypted_upstream_api_key: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Encrypted at rest"
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    deployment_or_version: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Azure deployment name or API version"
    )
    encrypted_virtual_key: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="LiteLLM proxy key (encrypted)"
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    extra_params: Mapped[dict | None] = mapped_column(
        JSONB, default=None, comment="Extra provider params as JSON"
    )
    operation_models: Mapped[dict | None] = mapped_column(
        JSONB,
        default=None,
        comment=(
            "Per-operation model routing: "
            "{operation: {model, temperature?, max_tokens?}} where operation is one of "
            "sql_generation/insight/suggestion/chart. Absent → inherit model_name."
        ),
    )

    # relationships
    customer: Mapped["Customer"] = relationship(back_populates="llm_configs")

    def __repr__(self) -> str:
        return f"<CustomerLLMConfig {self.provider.value} | {self.model_name}>"


class CustomerKeyConfig(Base, UUIDMixin, TimestampMixin):
    """Customer Managed Encryption Key (CMEK) configuration."""

    __tablename__ = "customer_key_configs"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(50), default="app", server_default="app", comment="app, aws, gcp, azure"
    )
    key_uri: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="URI to the KEK in the provider"
    )
    encrypted_dek: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Data Encryption Key encrypted by KEK"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # relationships
    customer: Mapped["Customer"] = relationship(back_populates="key_configs")

    def __repr__(self) -> str:
        return f"<CustomerKeyConfig {self.provider}>"


class SchemaRelationship(Base, UUIDMixin):
    """Discovered or manually defined relationship between external-DB tables."""

    __tablename__ = "schema_relationships"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
