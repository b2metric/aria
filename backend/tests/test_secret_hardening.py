"""TIER 1 secret-management hardening (gap analysis items 2/3/4).

- The master KEK must NOT silently derive from the well-known dev fallback in a
  non-development environment.
- Keycloak admin credentials must come from config; no hardcoded admin/admin.
- ``create_user`` must not default to the shared ``123456`` password and must
  create users as ``temporary`` (force reset).
"""

from __future__ import annotations

import inspect

import pytest

from backend.app.core.config import DEV_FALLBACK_SECRET, Settings


def _settings(**kw) -> Settings:
    # _env_file=None → ignore a local .env so validation is deterministic.
    return Settings(_env_file=None, **kw)


# ── config.validate_runtime: fail loud in prod ───────────────────────────────


def test_prod_requires_secret_key_and_kc_admin_password():
    problems = _settings(app_env="production").validate_runtime()
    assert any("ARIA_SECRET_KEY" in p for p in problems)
    assert any("KEYCLOAK_ADMIN_PASSWORD" in p for p in problems)


def test_dev_does_not_require_them():
    problems = _settings(app_env="development").validate_runtime()
    assert not any("ARIA_SECRET_KEY" in p for p in problems)
    assert not any("KEYCLOAK_ADMIN_PASSWORD" in p for p in problems)


def test_prod_with_secrets_set_is_clean_of_those():
    problems = _settings(
        app_env="production",
        aria_secret_key="a-strong-unique-production-secret",
        keycloak_admin_password="kc-admin-pw",
    ).validate_runtime()
    assert not any("ARIA_SECRET_KEY" in p for p in problems)
    assert not any("KEYCLOAK_ADMIN_PASSWORD" in p for p in problems)


# ── crypto: refuse the dev-fallback KEK in prod ──────────────────────────────


def test_app_kek_refuses_dev_fallback_in_prod(monkeypatch):
    from backend.app.services import crypto

    monkeypatch.setattr(crypto, "get_settings", lambda: _settings(app_env="production"))
    with pytest.raises(RuntimeError):
        crypto.AppKEKProvider.get_kek_fernet()


def test_app_kek_allows_dev_fallback_in_dev(monkeypatch):
    from backend.app.services import crypto

    monkeypatch.setattr(crypto, "get_settings", lambda: _settings(app_env="development"))
    assert crypto.AppKEKProvider.get_kek_fernet() is not None
    # Sanity: the dev fallback constant is still what we guard against.
    assert "dev_only" in DEV_FALLBACK_SECRET


# ── keycloak create_user: no shared default password, temporary by default ───


def test_create_user_has_no_default_password_and_is_temporary():
    from backend.app.services.keycloak_admin import KeycloakAdminService

    sig = inspect.signature(KeycloakAdminService.create_user)
    assert sig.parameters["password"].default is inspect.Parameter.empty
    assert sig.parameters["temporary"].default is True
