"""Shared fixtures for the mocked unit suite under ``backend/tests/``.

These tests sign their own RS256 JWTs with a fixed issuer
(``http://localhost:8080/realms/aria``) and mock the JWKS endpoint.  The
backend validates the token issuer against ``Settings.keycloak_issuer``,
which is derived from ``KEYCLOAK_URL`` / ``KEYCLOAK_REALM``.

Locally a gitignored ``.env`` happens to set ``KEYCLOAK_URL`` so the issuer
matches; CI has no ``.env`` and falls back to the default
``http://localhost:8080/auth`` (note the ``/auth`` suffix), so the issuer
would NOT match and every token would be rejected with 401.

This autouse fixture pins the Keycloak settings so JWT issuer validation is
deterministic in *every* environment, then clears the ``get_settings`` cache
so the next lookup re-reads the pinned values.
"""

from __future__ import annotations

import pytest

from backend.app.core.config import get_settings


@pytest.fixture(autouse=True)
def _pin_keycloak_issuer(monkeypatch: pytest.MonkeyPatch):
    """Pin KEYCLOAK_URL/REALM to match the issuer in test-signed tokens."""
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "aria")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_sse_app_status():
    """Reset sse_starlette's process-global shutdown Event between tests.

    ``EventSourceResponse`` lazily binds a module-global ``anyio.Event`` to the
    running loop the first time it streams. TestClient spins up a fresh loop per
    request, so a leftover Event from an earlier test is bound to a dead loop and
    a later SSE test fails with "bound to a different event loop". Clearing it to
    ``None`` makes sse_starlette recreate the Event on the current loop.
    """
    try:
        from sse_starlette.sse import AppStatus

        AppStatus.should_exit_event = None
        yield
        AppStatus.should_exit_event = None
    except ImportError:  # pragma: no cover - sse_starlette always installed
        yield
