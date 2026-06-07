"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ARIA application configuration.

    All values can be overridden via environment variables or a ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "debug"

    # ── Database ─────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://aria:aria_dev@localhost:5432/aria"

    # ── Redis ────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    schema_cache_ttl: int = 1800  # 30 minutes

    # ── Keycloak ─────────────────────────────────────────────────────
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "aria"
    keycloak_client_id: str = "aria-backend"
    keycloak_client_secret: str = ""
    keycloak_verify_ssl: bool = False

    # ── Auth / JWT ───────────────────────────────────────────────────
    # When using Keycloak, these are NOT used for signing — instead
    # the Keycloak JWKS endpoint provides the public key.  These fields
    # exist as a fallback for local-only (non-Keycloak) testing.
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "RS256"
    jwt_leeway_seconds: int = 30

    # ── MinIO ────────────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "aria"

    # ── Qdrant ───────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"

    # ── Prefect ──────────────────────────────────────────────────────
    prefect_api_url: str = "http://localhost:4200/api"

    # ── Sentry ───────────────────────────────────────────────────────
    sentry_dsn: str = ""
    sentry_environment: str = "development"

    @property
    def keycloak_openid_config_url(self) -> str:
        """Keycloak OIDC discovery endpoint."""
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/.well-known/openid-configuration"

    @property
    def keycloak_jwks_url(self) -> str:
        """Keycloak JWKS (JSON Web Key Set) endpoint."""
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"

    @property
    def keycloak_issuer(self) -> str:
        """Expected ``iss`` claim in JWT tokens."""
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
