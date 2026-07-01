"""MECHANICAL GATE (model-independent, CI-blocking) for token/quota user attribution.

Root cause of the "Tokens Today = 0" regression: the token/quota path strict-parsed
the caller with ``uuid.UUID(user_id)`` while the incoming ``user_id`` is the Keycloak
*effective identity string* (``payload.user_id or payload.sub``), NOT ``users.id``.
Non-UUID identities (``admin-001``) raised → ``user_uuid=None`` → no recording;
UUID-subs parsed but ≠ ``users.id`` → the ``TokenUsageDaily.user_id`` FK rejected the
insert. The audit path never had this bug because it coerces via
``_coerce_user_uuid`` (= ``resolve_identity_uuid``), which is exactly how JIT-sync
provisions ``users.id``. This gate pins the token path to that same coercion so the
two can never diverge again — under any model/provider.
"""

from __future__ import annotations

import inspect
import re
import uuid

from backend.app.auth.identity import resolve_identity_uuid
from backend.app.query import pipeline


def test_coerce_user_uuid_matches_audit_resolution() -> None:
    # Non-UUID identity → deterministic uuid5, and MUST match the audit path's value
    # (this is the users.id JIT-sync creates).
    assert pipeline._coerce_user_uuid("admin-001") == resolve_identity_uuid("admin-001")
    assert pipeline._coerce_user_uuid("admin-001") is not None
    # A real UUID identity passes through unchanged.
    real = "f903c0ec-d72e-4f05-878f-cc420b2e5d6b"
    assert pipeline._coerce_user_uuid(real) == uuid.UUID(real)
    # Empty → None.
    assert pipeline._coerce_user_uuid(None) is None


def test_token_path_does_not_strict_parse_user_id() -> None:
    """The token/quota attribution must coerce via _coerce_user_uuid, never a bare
    uuid.UUID(user_id) which drops non-UUID identities and breaks the users.id FK."""
    src = inspect.getsource(pipeline)
    assert not re.search(r"user_uuid\s*=\s*_uuid\.UUID\(\s*user_id", src), (
        "token/quota path strict-parses user_id — drops non-UUID identities and breaks "
        "the users.id FK. Use `user_uuid = _coerce_user_uuid(user_id)` (same as audit)."
    )
    assert "user_uuid = _coerce_user_uuid(user_id)" in src
