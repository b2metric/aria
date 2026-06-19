"""Authentication and authorization data models."""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field

# ── Roles ────────────────────────────────────────────────────────────────


class Role(enum.StrEnum):
    """ARIA platform roles.

    These map directly to Keycloak realm roles.  Only the four role names
    that appear in JWT ``realm_access.roles`` are listed — Keycloak may
    define extra roles (e.g. ``default-roles-aria``) that are not
    considered application roles.
    """

    ADMIN = "admin"
    TEAM_LEAD = "team_lead"
    ANALYST = "analyst"
    VIEWER = "viewer"

    @staticmethod
    def from_string(value: str) -> Role:
        """Parse a role string case-insensitively."""
        try:
            return Role(value.lower())
        except ValueError:
            raise ValueError(
                f"Unknown role: {value!r}. Valid roles: {[r.value for r in Role]}"
            ) from None

    @classmethod
    def hierarchy(cls, role: Role) -> int:
        """Return a numeric priority (higher = more permissive)."""
        order = {cls.VIEWER: 0, cls.ANALYST: 1, cls.TEAM_LEAD: 2, cls.ADMIN: 3}
        return order[role]

    def can(self, minimum: Role) -> bool:
        """Check whether this role meets or exceeds *minimum*."""
        return self.hierarchy(self) >= self.hierarchy(minimum)


# ── JWT Claims ───────────────────────────────────────────────────────────


class TokenPayload(BaseModel):
    """Decoded JWT access-token claims from Keycloak.

    All fields are populated from the token body after successful
    validation (signature, issuer, audience, expiration).
    """

    model_config = {"extra": "allow"}

    sub: str | None = Field(default=None, description="Keycloak user UUID")
    iss: str | None = Field(default=None, description="Token issuer (Keycloak realm URL)")
    aud: str | list[str] | None = Field(default=None, description="Audience (client ID)")
    exp: int | None = Field(default=None, description="Expiration timestamp (UNIX)")
    iat: int | None = Field(default=None, description="Issued-at timestamp (UNIX)")

    # ── Custom ARIA claims (injected by aria-claims client scope) ────
    workspace_id: str | None = Field(
        default=None,
        description="Current workspace UUID — set by Keycloak aria-claims mapper",
    )
    user_id: str | None = Field(
        default=None,
        description="Application-level user ID (may differ from sub)",
    )
    team_id: str | None = Field(
        default=None,
        description="Team UUID the user belongs to",
    )
    role: str | None = Field(
        default=None,
        description="ARIA role name (admin, team_lead, analyst, viewer)",
    )

    # ── Keycloak standard claims ─────────────────────────────────
    preferred_username: str | None = None
    email: str | None = None
    email_verified: bool = False
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None

    # ── Keycloak realm / resource access ──────────────────────────
    realm_access: dict | None = None
    resource_access: dict | None = None


# ── Request-scoped User ──────────────────────────────────────────────────


class UserContext(BaseModel):
    """Authenticated user injected into every request via dependency.

    Populated by :func:`backend.app.auth.dependencies.get_current_user`.
    """

    sub: str | None = None  # Keycloak user UUID
    user_id: str | None = None
    workspace_id: str | None = None
    team_id: str | None = None
    role: Role | None = None
    email: str | None = None
    name: str | None = None
    preferred_username: str | None = None

    # ── Permissions ────────────────────────────────────────────────
    can_view_sql: bool = False
    can_manage_team: bool = False
    can_manage_workspace: bool = False
    can_admin: bool = False
