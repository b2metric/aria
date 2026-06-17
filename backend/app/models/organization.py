"""Organization models: customers (tenants), teams, and users."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin
from backend.app.models.enums import UserRole, TeamRole


class Customer(Base, UUIDMixin, TimestampMixin):
    """Top-level tenant / customer organization."""

    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(50), default="free", server_default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    settings: Mapped[dict | None] = mapped_column(JSONB, default=None)

    # relationships
    teams: Mapped[list["Team"]] = relationship(back_populates="customer", lazy="selectin")
    users: Mapped[list["User"]] = relationship(back_populates="customer", lazy="selectin")
    db_configs: Mapped[list["CustomerDBConfig"]] = relationship(back_populates="customer", lazy="selectin")
    llm_configs: Mapped[list["CustomerLLMConfig"]] = relationship(back_populates="customer", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Customer {self.slug}>"


class Team(Base, UUIDMixin, TimestampMixin):
    """A group of users within a customer tenant."""

    __tablename__ = "teams"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # relationships
    customer: Mapped["Customer"] = relationship(back_populates="teams")
    users: Mapped[list["User"]] = relationship(back_populates="team", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Team {self.name}>"


class User(Base, UUIDMixin, TimestampMixin):
    """A human user within a customer tenant, optionally in a team."""

    __tablename__ = "users"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(postgresql.ENUM("admin", "member", "viewer", name="user_role", create_type=False), default=UserRole.MEMBER, server_default="member")
    external_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, comment="Keycloak user ID"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # relationships
    customer: Mapped["Customer"] = relationship(back_populates="users")
    team: Mapped["Team | None"] = relationship(back_populates="users")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
