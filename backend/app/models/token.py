"""Token quota and usage tracking models."""

import uuid
from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDMixin
from backend.app.models.enums import QuotaPeriod


class TokenQuota(Base, UUIDMixin, TimestampMixin):
    """Token quota allocation — at customer, team, or user level.

    Precedence (lowest → highest):
        customer default → team → user
    """

    __tablename__ = "token_quotas"

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    period: Mapped[QuotaPeriod] = mapped_column(
        postgresql.ENUM("daily", "monthly", name="quota_period", create_type=False),
        default=QuotaPeriod.DAILY,
        server_default="daily",
    )
    token_limit: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    def __repr__(self) -> str:
        return f"<TokenQuota {self.token_limit:,} tokens/{self.period.value}>"


class TokenUsageDaily(Base, UUIDMixin):
    """Daily aggregated token consumption per user."""

    __tablename__ = "token_usage_daily"
    __table_args__ = (
        sa.UniqueConstraint(
            "customer_id", "user_id", "usage_date", name="uix_token_usage_customer_user_date"
        ),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tokens_used: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 6), default=0, server_default="0", nullable=False
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TokenUsage {self.tokens_used:,} tok / ${self.cost_usd} on {self.usage_date}>"


class TokenUsageEvent(Base, UUIDMixin):
    """Append-only per-LLM-call usage record — the granular source of truth for
    per-operation, per-model, per-conversation token & USD-cost breakdowns.

    One row per LLM call (sql_generation / insight / suggestion / chart /
    self_correction / vault_*). ``user_id`` and ``conversation_id`` are nullable so
    background/system ops (vault enrichment, embeddings) that are not tied to a user
    or a chat turn can still be metered. Aggregates (dashboard today, per-conversation
    totals, per-operation breakdown) are SUM queries over this table.
    """

    __tablename__ = "token_usage_events"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    completion_tokens: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), default=0, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<TokenUsageEvent {self.operation}/{self.model} {self.total_tokens} tok ${self.cost_usd}>"
