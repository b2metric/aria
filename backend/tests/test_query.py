"""Tests for the /api/query SSE endpoint."""

from __future__ import annotations

import base64
import json
import os
import time
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from backend.app.main import app as _app

# ── Key generation ───────────────────────────────────────────────────


@pytest.fixture(scope="session")
def rsa_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    return key


@pytest.fixture(scope="session")
def jwks(rsa_key):
    pub_numbers = rsa_key.public_key().public_numbers()

    def _b64url_int(n: int) -> str:
        n_bytes = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode()

    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-kid",
                "use": "sig",
                "alg": "RS256",
                "n": _b64url_int(pub_numbers.n),
                "e": _b64url_int(pub_numbers.e),
            }
        ]
    }


@pytest.fixture
def auth_token(rsa_key):
    now = int(time.time())
    payload = {
        "sub": "test-user-uuid",
        "iss": "http://localhost:8080/realms/aria",
        "aud": "aria-backend",
        "exp": now + 3600,
        "iat": now,
        "workspace_id": "ws-test-001",
        "user_id": "user-001",
        "team_id": "team-001",
        "role": "analyst",
        "email": "test@b2metric.com",
        "name": "Test User",
        "preferred_username": "testuser",
    }
    return jose_jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": "test-kid"})


# ── Mock SSE event generator ─────────────────────────────────────────

SAMPLE_CHART_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body><div id="chart"></div>
<script src="https://cdn.plot.ly/plotly-3.2.0.min.js"></script>
</body></html>"""


async def _mock_process_query(redis, engine, request, workspace_id, user_id):
    """Mock pipeline that yields SSE events with chart_html."""
    cid = "conv-test-123"
    yield {"event": "status", "data": json.dumps({"status": "thinking", "message": "Analyzing..."})}
    yield {
        "event": "status",
        "data": json.dumps({"status": "generating_sql", "message": "Generating SQL..."}),
    }
    yield {
        "event": "sql",
        "data": json.dumps(
            {
                "sql": "SELECT category, SUM(value) AS total FROM sales GROUP BY category",
                "explanation": "Grouped sales by category.",
            }
        ),
    }
    yield {
        "event": "status",
        "data": json.dumps({"status": "sql_ready", "message": "SQL generated"}),
    }
    yield {
        "event": "status",
        "data": json.dumps({"status": "executing", "message": "Executing..."}),
    }
    yield {
        "event": "status",
        "data": json.dumps(
            {"status": "rendering_chart", "message": "Building chart from 3 rows..."}
        ),
    }
    yield {
        "event": "chart",
        "data": json.dumps(
            {
                "chart_type": "bar",
                "chart_html": SAMPLE_CHART_HTML,
                "chart_url": "",
                "csv_url": "",
                "chart_config": {"type": "bar", "title": "Test Chart", "confidence": 0.85},
                "row_count": 3,
            }
        ),
    }
    yield {
        "event": "status",
        "data": json.dumps({"status": "complete", "message": "Done", "conversation_id": cid}),
    }
    yield {"event": "done", "data": json.dumps({"conversation_id": cid})}


# ── Client fixture ───────────────────────────────────────────────────


@pytest.fixture
def client(jwks):
    """Create a test client with mocked pipeline and auth."""
    mock_redis = AsyncMock()
    mock_redis.aclose.return_value = None
    mock_engine = AsyncMock()
    mock_engine.dispose.return_value = None

    with (
        patch("backend.app.auth.jwt._fetch_jwks", return_value=jwks),
        patch("backend.app.api.query._get_redis", return_value=mock_redis),
        patch("backend.app.api.query._get_engine", return_value=mock_engine),
        patch("backend.app.api.query.process_query", side_effect=_mock_process_query),
        patch("backend.app.api.query.list_conversations", return_value=[]),
        patch(
            "backend.app.api.query.get_conversation",
            return_value=None,
        ),
        patch(
            "backend.app.api.query.delete_conversation",
            return_value=True,
        ),
    ):
        os.environ["ENV"] = "testing"
        yield TestClient(_app)
        os.environ["ENV"] = "development"


class TestQueryEndpoint:
    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_query_requires_auth(self, client):
        resp = client.post("/api/query", json={"question": "test"})
        assert resp.status_code == 401

    def test_conversations_list_requires_auth(self, client):
        resp = client.get("/api/conversations")
        assert resp.status_code == 401

    def test_query_with_valid_token_returns_sse(self, client, auth_token):
        """Verify SSE stream includes chart event with chart_html."""
        with client.stream(
            "POST",
            "/api/query",
            json={"question": "Show sales by category"},
            headers={"Authorization": f"Bearer {auth_token}"},
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")

            body = b""
            for chunk in response.iter_bytes():
                body += chunk
                if b"done" in body:
                    break

            text = body.decode()
            assert "event: status" in text
            assert "event: sql" in text
            assert "event: chart" in text
            assert "chart_html" in text
            assert "plotly" in text.lower()

    def test_conversations_list_authenticated(self, client, auth_token):
        resp = client.get(
            "/api/conversations",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_conversation_not_found(self, client, auth_token):
        resp = client.get(
            "/api/conversations/nonexistent-id",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 404

    def test_chart_event_has_chart_html(self, client, auth_token):
        """Verify chart_html content is present in the mock process (structure test).

        The full SSE integration is verified in test_query_with_valid_token_returns_sse.
        This test validates the data structure our mock produces.
        """
        # Run the mock directly to verify data shape
        events = []

        async def collect():
            async for event in _mock_process_query(None, None, None, None, None):
                events.append(event)

        import asyncio

        asyncio.run(collect())

        chart_events = [e for e in events if e["event"] == "chart"]
        assert len(chart_events) == 1
        data = json.loads(chart_events[0]["data"])
        assert "chart_html" in data
        assert "chart_type" in data
        assert data["chart_type"] == "bar"
        assert "plotly" in data["chart_html"].lower()


# ── Helper ───────────────────────────────────────────────────────────


def _extract_sse_event_data(sse_text: str, event_name: str) -> dict | None:
    lines = sse_text.split("\n")
    current_event = ""
    current_data = ""
    for line in lines:
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: "):
            current_data += line[6:]
        elif line == "" and current_event:
            if current_event == event_name:
                try:
                    return json.loads(current_data)
                except json.JSONDecodeError:
                    return None
            current_event = ""
            current_data = ""
    return None
