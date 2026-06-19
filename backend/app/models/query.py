"""Natural-language query and execution history models."""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin
from backend.app.models.enums import QueryStatus


class Query(Base, UUIDMixin, TimestampMixin):
    """A natural-language query submitted by a user."""

    __tablename__ = "queries"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    natural_language: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[QueryStatus] = mapped_column(
        default=QueryStatus.PENDING, server_default="pending"
    )
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rows_returned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    db_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_db_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # relationships
    history: Mapped[list["QueryHistory"]] = relationship(back_populates="query", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Query {self.id} [{self.status.value}]>"


class QueryHistory(Base, UUIDMixin):
    """Immutable log of each query execution attempt."""

    __tablename__ = "query_history"

    query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sql_executed: Mapped[str] = mapped_column(Text, nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_returned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # relationships
    query: Mapped["Query"] = relationship(back_populates="history")

    def __repr__(self) -> str:
        return f"<QueryHistory query={self.query_id} {self.execution_time_ms}ms>"
