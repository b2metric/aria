"""SQLAlchemy declarative base and common mixins for ARIA."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Shared declarative base for all ARIA models."""

    pass


class UUIDMixin:
    """UUID v4 primary key for every table."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class TimestampMixin:
    """created_at / updated_at columns, auto-managed."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=utcnow,
        nullable=False,
    )
