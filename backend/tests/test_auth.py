"""Tests for JWT validation, auth dependencies, and RBAC guards.

These tests simulate Keycloak-issued JWTs by generating RS256-signed
tokens locally and mocking the JWKS endpoint that the auth layer calls.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt
from jose.constants import Algorithms

# ── Key generation for test signing ──────────────────────────────────────


@pytest.fixture(scope="session")
def rsa_key():
    """Generate an RSA keypair once per test session."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    return key


@pytest.fixture(scope="session")
def jwks(rsa_key):
    """Build a JWKS representation of the public key."""
    pub_numbers = rsa_key.public_key().public_numbers()
    import base64

    def _b64url_int(n: int) -> str:
        """Encode an integer as base64url (no padding)."""
        n_bytes = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode()

    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-kid-001",
                "use": "sig",
                "alg": "RS256",
                "n": _b64url_int(pub_numbers.n),
                "e": _b64url_int(pub_numbers.e),
            }
        ]
    }


@pytest.fixture(scope="session")
def public_pem(rsa_key):
    """Public key in PEM format (optional, for debugging)."""
    return (
        rsa_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )


# ── Token factory ────────────────────────────────────────────────────────


def make_token(
    rsa_key,
    *,
    sub: str = "user-uuid-1234",
    workspace_id: str = "ws-abc",
    user_id: str = "user-uuid-1234",
    team_id: str = "team-xyz",
    role: str = "analyst",
    exp: int | None = None,
    iat: int | None = None,
    iss: str = "http://localhost:8080/realms/aria",
    aud: str = "aria-backend",
    extra_claims: dict | None = None,
    kid: str = "test-kid-001",
) -> str:
    """Create a signed JWT that looks like a Keycloak access token."""
    now = int(time.time())
    payload = {
        "sub": sub,
        "iss": iss,
        "aud": aud,
        "exp": exp or now + 300,
        "iat": iat or now,
        "workspace_id": workspace_id,
        "user_id": user_id,
        "team_id": team_id,
        "role": role,
        "email": f"{sub}@example.com",
        "name": "Test User",
        "preferred_username": "testuser",
        "email_verified": True,
        "realm_access": {"roles": [role]},
    }
    if extra_claims:
        payload.update(extra_claims)

    headers = {"kid": kid}
    return jose_jwt.encode(payload, rsa_key, algorithm=Algorithms.RS256, headers=headers)


# ── FastAPI test app ─────────────────────────────────────────────────────


@pytest.fixture
def app_with_mock_jwks(jwks, monkeypatch):
    """Create a test FastAPI app with mocked JWKS endpoint."""
    # Disable dev-mode auth bypass for tests
    monkeypatch.setenv("ENV", "testing")

    # Patch the JWKS fetch to return our local key.
    mock_get = AsyncMock(return_value=jwks)

    with patch("backend.app.auth.jwt._fetch_jwks", mock_get):
        from backend.app.main import app as _app

        yield _app


@pytest.fixture
def client(app_with_mock_jwks):
    """Synchronous test client."""
    return TestClient(app_with_mock_jwks)


# ── JWKS fetch is patched globally for all token tests ───────────────────


@pytest.fixture(autouse=True)
def _patch_jwks(jwks):
    """Auto-patch JWKS fetch so all token tests work without Keycloak."""
    mock_get = AsyncMock(return_value=jwks)
    with patch("backend.app.auth.jwt._fetch_jwks", mock_get):
        yield


# ── Tests: Token validation ──────────────────────────────────────────────


class TestTokenValidation:
    def test_valid_token_returns_200(self, rsa_key, client):
        token = make_token(rsa_key, role="analyst")
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "analyst"
        assert data["workspace_id"] == "ws-abc"
        assert data["permissions"]["can_view_sql"] is True
        assert data["permissions"]["can_admin"] is False

    def test_viewer_has_no_sql_access(self, rsa_key, client):
        token = make_token(rsa_key, role="viewer")
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["permissions"]["can_view_sql"] is False

    def test_admin_has_full_access(self, rsa_key, client):
        token = make_token(rsa_key, role="admin")
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        perms = resp.json()["permissions"]
        assert all(perms.values())

    def test_missing_token_returns_401(self, client):
        resp = client.get("/me")
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, rsa_key, client):
        now = int(time.time())
        # Expired well beyond the configured clock-skew leeway (jwt_leeway_seconds=60).
        token = make_token(rsa_key, exp=now - 300, iat=now - 3600)
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    def test_wrong_issuer_returns_401(self, rsa_key, client):
        token = make_token(rsa_key, iss="http://evil.com/realms/aria")
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_audience_is_not_a_security_boundary(self, rsa_key, client):
        # Keycloak access tokens minted for the "aria-web" client carry `azp`,
        # not a backend `aud` (real tokens have no `aud` claim at all), so the
        # auth layer intentionally disables `verify_aud`. Audience is NOT a
        # security boundary here — signature, issuer, expiry and the
        # role/workspace claims are. Enabling verify_aud would reject every
        # live Keycloak token. A "wrong" aud must therefore still be accepted.
        token = make_token(rsa_key, aud="wrong-client")
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_missing_role_claim_returns_403(self, rsa_key, client):
        token = make_token(rsa_key, role=None, extra_claims={"role": None})
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert "role" in resp.json()["detail"].lower()

    def test_missing_workspace_id_returns_403(self, rsa_key, client):
        token = make_token(rsa_key, workspace_id=None, extra_claims={"workspace_id": None})
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert "workspace" in resp.json()["detail"].lower()

    def test_invalid_role_name_returns_403(self, rsa_key, client):
        token = make_token(rsa_key, role="superuser")
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


# ── Tests: RBAC guards ───────────────────────────────────────────────────


class TestRBACGuards:
    def test_admin_can_access_admin_dashboard(self, rsa_key, client):
        token = make_token(rsa_key, role="admin")
        resp = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_analyst_cannot_access_admin_dashboard(self, rsa_key, client):
        token = make_token(rsa_key, role="analyst")
        resp = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_viewer_cannot_access_admin_dashboard(self, rsa_key, client):
        token = make_token(rsa_key, role="viewer")
        resp = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_team_lead_can_manage_team(self, rsa_key, client):
        token = make_token(rsa_key, role="team_lead")
        resp = client.get("/team/manage", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_admin_can_manage_team(self, rsa_key, client):
        token = make_token(rsa_key, role="admin")
        resp = client.get("/team/manage", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_analyst_cannot_manage_team(self, rsa_key, client):
        token = make_token(rsa_key, role="analyst")
        resp = client.get("/team/manage", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


# ── Tests: SQL visibility ────────────────────────────────────────────────


class TestSQLVisibility:
    def test_admin_can_preview_sql(self, rsa_key, client):
        token = make_token(rsa_key, role="admin")
        resp = client.get("/queries/sql-preview", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_analyst_can_preview_sql(self, rsa_key, client):
        token = make_token(rsa_key, role="analyst")
        resp = client.get("/queries/sql-preview", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_viewer_cannot_preview_sql(self, rsa_key, client):
        token = make_token(rsa_key, role="viewer")
        resp = client.get("/queries/sql-preview", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_team_lead_cannot_preview_sql(self, rsa_key, client):
        token = make_token(rsa_key, role="team_lead")
        resp = client.get("/queries/sql-preview", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


# ── Tests: Workspace isolation ───────────────────────────────────────────


class TestWorkspaceIsolation:
    def test_can_access_own_workspace(self, rsa_key, client):
        token = make_token(rsa_key, workspace_id="ws-abc")
        resp = client.get(
            "/workspace/ws-abc/info",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_cannot_access_other_workspace(self, rsa_key, client):
        token = make_token(rsa_key, workspace_id="ws-abc")
        resp = client.get(
            "/workspace/ws-xyz/info",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_workspace_scoped_endpoint(self, rsa_key, client):
        token = make_token(rsa_key, workspace_id="ws-scoped")
        resp = client.get(
            "/workspace-scoped/query",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["workspace_id"] == "ws-scoped"
