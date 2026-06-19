"""Data governance models: team-level vault access policies and audit logging."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class TeamVaultPolicy(Base, UUIDMixin, TimestampMixin):
    """Row-level access policy controlling which vault data a team can access.

    Each policy is scoped to a customer and optionally a team.  When ``team_id``
    is NULL the policy applies organisation-wide as a default for that customer.
    """

    __tablename__ = "team_vault_policies"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="NULL means customer-wide default policy",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    allowed_tables: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}",
        comment="Whitelist of table names the team may query",
    )
    deny_columns: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='Per-table deny-lists, e.g. {"sales": ["revenue", "margin"]}',
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    def __repr__(self) -> str:
        return f"<TeamVaultPolicy {self.name}>"


class DataAuditLog(Base, UUIDMixin):
    """Immutable audit trail recording every data-access event for governance."""

    __tablename__ = "data_audit_logs"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="e.g. query, export, view, schema_discovery, vault_read",
    )
    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="e.g. table, query, artifact, vault_entry, db_config",
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Identifier of the accessed resource"
    )
    details: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Arbitrary payload: SQL text, filters applied, row-count, etc.",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True, comment="Client IP (IPv4 or IPv6)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    def __repr__(self) -> str:
        return f"<DataAuditLog {self.action} on {self.resource_type}>"
