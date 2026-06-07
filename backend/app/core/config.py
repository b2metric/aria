"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    redis_url: str = "redis://localhost:6379/0"

    # ── MinIO / Artifact Store ──────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "aria-artifacts"
    minio_secure: bool = False

    # ── LLM / LiteLLM ───────────────────────────────────────────────
    # LiteLLM proxy for multi-model routing
    litellm_api_base: str = "http://localhost:4000"
    litellm_api_key: str = ""
    
    # Default model for SQL generation
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096

    # ── Qdrant (Vector DB for Mem0) ─────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "aria_memory"

    # ── Keycloak / Auth ─────────────────────────────────────────────
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "aria"
    keycloak_client_id: str = "aria-backend"
    keycloak_client_secret: str = ""

    # ── Computed properties ─────────────────────────────────────────

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
