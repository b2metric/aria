"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# The placeholder key LiteLLM ships with. If the real key is missing the backend
# used to silently fall back to this and every LLM call 401'd -> garbage SQL.
# It is now treated as a FATAL misconfiguration at startup (see validate_runtime).
DUMMY_LITELLM_KEY = "sk-1234"


class Settings(BaseSettings):
    """ARIA application configuration.

    All values can be overridden via environment variables or a ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_file="backend/.env",  # Look for .env in backend/ folder
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars not in the model
    )

    # ── App ──────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "debug"

    # ── Database ─────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://aria:aria_dev@localhost:5433/aria"

    # ── Oracle Thick Mode ──────────────────────────────────────────────
    # Path to Oracle Instant Client lib dir (required for thick mode)
    # macOS: /opt/oracle/instantclient_23_3 or ~/instantclient_23_3
    # Linux: /opt/oracle/instantclient_23_3
    oracle_client_lib_dir: str | None = None

    # ── Vault (Knowledge Base) ──────────────────────────────────────
    # Base path for Obsidian vault files
    vault_base_path: str = "docs/vaults"

    # ── Redis ────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6380/0"
    schema_cache_ttl: int = 1800  # TTL (s) for cached schema snapshots in Redis

    # ── MinIO ────────────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "aria-artifacts"
    minio_secure: bool = False

    # ── Keycloak ─────────────────────────────────────────────────────
    keycloak_url: str = "http://localhost:8080/auth"
    keycloak_realm: str = "aria"
    keycloak_client_id: str = "aria-backend"
    keycloak_verify_ssl: bool = False
    jwt_leeway_seconds: int = 60

    # ── LiteLLM ──────────────────────────────────────────────────────
    litellm_api_base: str = "http://localhost:4000"
    litellm_api_key: str | None = None  # Falls back to LITELLM_API_KEY env var
    llm_model: str = "deepseek-chat"  # Default model for SQL generation
    llm_temperature: float = 0.1  # Low temperature for deterministic SQL
    llm_max_tokens: int = 2000  # Max tokens for SQL generation

    # ── Qdrant (Memory/Vector Store) ─────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "aria_memory"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # If litellm_api_key not set from .env, try system env. The dummy fallback
        # is kept so import never crashes, but validate_runtime() rejects it loudly.
        if not self.litellm_api_key:
            self.litellm_api_key = os.environ.get("LITELLM_API_KEY", DUMMY_LITELLM_KEY)

    def validate_runtime(self) -> list[str]:
        """Return a list of FATAL misconfigurations (empty = healthy).

        Catches the failure classes that previously shipped silently:
        a dummy/empty LiteLLM key -> every LLM call 401s -> garbage SQL.
        Called at startup (see main.py lifespan) so the app fails loudly instead
        of running degraded. Skippable via ARIA_SKIP_STARTUP_CHECKS=1 (tests/CI).
        """
        problems: list[str] = []
        if not self.litellm_api_key or self.litellm_api_key == DUMMY_LITELLM_KEY:
            problems.append(
                f"LITELLM_API_KEY is missing or the dummy '{DUMMY_LITELLM_KEY}'. "
                "LLM calls would 401 and silently degrade to garbage SQL. "
                "Set a valid proxy key in backend/.env or the LITELLM_API_KEY env var."
            )
        return problems

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env.lower() in ("development", "dev", "local")

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
