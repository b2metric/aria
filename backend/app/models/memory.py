"""Memory and knowledge-vault models with pgvector embeddings."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDMixin
from backend.app.models.enums import KnowledgeType


class MemoryEntry(Base, UUIDMixin, TimestampMixin):
    """Agent memory entry — contextual recall with optional embedding."""

    __tablename__ = "memory_entries"

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ttl_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    embedding: Mapped[Vector | None] = mapped_column(Vector(1536), nullable=True)  # type: ignore[valid-type]

    def __repr__(self) -> str:
        return f"<MemoryEntry {self.key}>"


class VaultKnowhow(Base, UUIDMixin, TimestampMixin):
    """Curated knowledge-base entry (SQL patterns, business terms, metrics)."""

    __tablename__ = "vault_knowhow"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[KnowledgeType] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    embedding: Mapped[Vector | None] = mapped_column(Vector(1536), nullable=True)  # type: ignore[valid-type]

    def __repr__(self) -> str:
        return f"<VaultKnowhow {self.title} [{self.type.value}]>"
