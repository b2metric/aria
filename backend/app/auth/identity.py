"""Deterministic identity → UUID resolution.

Real Keycloak ``sub`` values are UUIDs and pass through unchanged. Legacy/dev
identifiers (e.g. ``admin-001``) are mapped via ``uuid5`` so the SAME identity
always yields the SAME UUID across JIT-sync, audit writes, and dashboard reads —
making per-user attribution consistent instead of dropping to NULL.
"""

import uuid

# Fixed namespace (frozen). Do NOT regenerate — changing it re-maps every derived
# identity and breaks attribution continuity.
_IDENTITY_NAMESPACE = uuid.UUID("b1d9f0c2-7a3e-4e2a-9c1b-2f6a8e4d5c30")


def resolve_identity_uuid(identifier: str | None) -> uuid.UUID | None:
    """Map an identity string to a stable UUID, or None when empty."""
    if not identifier:
        return None
    try:
        return uuid.UUID(str(identifier))
    except (ValueError, AttributeError):
        return uuid.uuid5(_IDENTITY_NAMESPACE, str(identifier))
