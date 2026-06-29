import uuid

from backend.app.auth.identity import resolve_identity_uuid


def test_valid_uuid_passes_through():
    u = uuid.uuid4()
    assert resolve_identity_uuid(str(u)) == u

def test_non_uuid_is_deterministic():
    a = resolve_identity_uuid("admin-001")
    b = resolve_identity_uuid("admin-001")
    assert isinstance(a, uuid.UUID) and a == b
    assert resolve_identity_uuid("other") != a

def test_empty_returns_none():
    assert resolve_identity_uuid(None) is None
    assert resolve_identity_uuid("") is None
