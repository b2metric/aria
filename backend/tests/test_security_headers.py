"""TIER 2 item 8 — security headers on every response.

The app previously registered only CORS; no CSP/HSTS/X-Frame-Options/nosniff.
These assert the security-headers middleware tags responses (checked on the
unauthenticated /health endpoint so no token/DB is needed).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_security_headers_present_on_health():
    from backend.app.main import app

    with patch("backend.app.auth.jwt._fetch_jwks", AsyncMock(return_value={"keys": []})):
        client = TestClient(app)
        resp = client.get("/health")

    h = {k.lower(): v for k, v in resp.headers.items()}
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert "default-src 'none'" in h["content-security-policy"]
    assert "frame-ancestors 'none'" in h["content-security-policy"]
    assert h["strict-transport-security"].startswith("max-age=")
    assert h["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in h["permissions-policy"]
