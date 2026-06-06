"""Token quota and usage tracking models."""

import uuid
from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, String
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
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    period: Mapped[QuotaPeriod] = mapped_column(default=QuotaPeriod.DAILY, server_default="daily")
    token_limit: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    def __repr__(self) -> str:
        return f"<TokenQuota {self.token_limit:,} tokens/{self.period.value}>"


class TokenUsageDaily(Base, UUIDMixin):
    """Daily aggregated token consumption per user."""

    __tablename__ = "token_usage_daily"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tokens_used: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TokenUsage {self.tokens_used:,} on {self.usage_date}>"
