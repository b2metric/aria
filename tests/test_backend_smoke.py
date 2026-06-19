"""Backend smoke tests for ARIA API endpoints.

Tests API endpoints, database connections, vault loading.
Run: pytest tests/test_backend_smoke.py -v
"""

import pytest
import httpx
import os


# Test configuration
API_BASE = os.getenv("ARIA_API_BASE", "http://localhost:8000")
WORKSPACE_ID = "stc-kuwait"


@pytest.mark.integration
class TestHealthEndpoints:
    """Health check endpoint tests.

    Hits a live backend at ``API_BASE`` — runs only in the live-stack
    (integration) context, not the unit pytest gate.
    """

    def test_health_check(self):
        """Test /health endpoint."""
        with httpx.Client() as client:
            resp = client.get(f"{API_BASE}/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert "version" in data

    def test_root_redirect_or_docs(self):
        """Test root endpoint returns something."""
        with httpx.Client(follow_redirects=True) as client:
            resp = client.get(f"{API_BASE}/")
            # 200 (docs), 404 (not implemented yet), or redirect
            assert resp.status_code in [200, 307, 308, 404]


@pytest.mark.integration
class TestAPIEndpoints:
    """API endpoint tests.

    Hits a live backend at ``API_BASE`` — runs only in the live-stack
    (integration) context, not the unit pytest gate.
    """

    def test_query_endpoint_exists(self):
        """Test /api/query endpoint exists."""
        with httpx.Client() as client:
            # POST without body should return 422 (validation error), not 404
            resp = client.post(f"{API_BASE}/api/query")
            assert resp.status_code != 404, f"Got {resp.status_code}"

    def test_conversations_endpoint(self):
        """Test /api/conversations endpoint exists."""
        with httpx.Client() as client:
            resp = client.get(f"{API_BASE}/api/conversations")
            # May require auth
            assert resp.status_code in [200, 401, 403, 422]

    def test_workspaces_vault_tables(self):
        """Test /api/workspaces/vault/tables endpoint."""
        with httpx.Client() as client:
            resp = client.get(f"{API_BASE}/api/workspaces/vault/tables")
            # May require workspace param
            assert resp.status_code in [200, 401, 403, 422]


class TestVaultLoading:
    """Vault loading tests."""

    def test_vault_directory_exists(self):
        """Test that vault directory exists."""
        vault_path = os.path.join(
            os.path.dirname(__file__), "..", "docs", "vaults", WORKSPACE_ID, "tables"
        )
        assert os.path.isdir(vault_path), f"Vault directory not found: {vault_path}"

    def test_vault_has_md_files(self):
        """Test that vault has .md files."""
        vault_path = os.path.join(
            os.path.dirname(__file__), "..", "docs", "vaults", WORKSPACE_ID, "tables"
        )
        md_files = [f for f in os.listdir(vault_path) if f.endswith(".md")]
        assert len(md_files) > 0, "No .md files in vault"

    def test_vault_file_has_frontmatter(self):
        """Test that vault files have YAML frontmatter."""
        vault_path = os.path.join(
            os.path.dirname(__file__), "..", "docs", "vaults", WORKSPACE_ID, "tables"
        )
        md_files = [f for f in os.listdir(vault_path) if f.endswith(".md") and not f.startswith("_")]
        
        if not md_files:
            pytest.skip("No table .md files found")
        
        # Check first file
        with open(os.path.join(vault_path, md_files[0])) as f:
            content = f.read()
        
        # Should start with --- (YAML frontmatter)
        assert content.strip().startswith("---"), f"File {md_files[0]} missing YAML frontmatter"


class TestDatabaseConnections:
    """Database connection tests."""

    @pytest.mark.integration
    def test_postgres_metadata_db(self):
        """Test PostgreSQL metadata DB connection."""
        import asyncio
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        
        # Use environment or default
        db_url = os.getenv(
            "ARIA_DATABASE_URL",
            "postgresql+asyncpg://aria:aria_dev@localhost:5433/aria"
        )
        
        async def check_connection():
            engine = create_async_engine(db_url)
            try:
                async with engine.connect() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    row = result.fetchone()
                    return row[0] == 1
            finally:
                await engine.dispose()
        
        assert asyncio.run(check_connection())

    @pytest.mark.integration
    def test_redis_connection(self):
        """Test Redis connection."""
        import redis
        
        redis_url = os.getenv("ARIA_REDIS_URL", "redis://localhost:6380/0")
        r = redis.from_url(redis_url)
        
        try:
            assert r.ping()
        finally:
            r.close()

    @pytest.mark.integration
    def test_qdrant_connection(self):
        """Test Qdrant connection."""
        qdrant_url = os.getenv("ARIA_QDRANT_URL", "http://localhost:6333")
        
        with httpx.Client() as client:
            resp = client.get(f"{qdrant_url}/collections")
            assert resp.status_code == 200
            data = resp.json()
            assert "result" in data

    @pytest.mark.integration
    def test_minio_connection(self):
        """Test MinIO connection."""
        minio_url = os.getenv("ARIA_MINIO_URL", "http://localhost:9000")
        
        with httpx.Client() as client:
            resp = client.get(f"{minio_url}/minio/health/live")
            assert resp.status_code == 200


class TestLiteLLMProxy:
    """LiteLLM proxy tests."""

    @pytest.mark.integration
    def test_litellm_health(self):
        """Test LiteLLM proxy health."""
        litellm_url = os.getenv("LITELLM_API_BASE", "http://localhost:4000")
        
        with httpx.Client() as client:
            resp = client.get(f"{litellm_url}/health")
            # 200 or 401 (if auth required)
            assert resp.status_code in [200, 401]

    @pytest.mark.integration
    def test_litellm_models(self):
        """Test LiteLLM model list."""
        litellm_url = os.getenv("LITELLM_API_BASE", "http://localhost:4000")
        litellm_key = os.getenv("LITELLM_API_KEY", "")
        
        with httpx.Client() as client:
            resp = client.get(
                f"{litellm_url}/models",
                headers={"Authorization": f"Bearer {litellm_key}"} if litellm_key else {},
            )
            # 200 or 401 (if key required)
            assert resp.status_code in [200, 401]

    @pytest.mark.integration
    def test_embedding_endpoint(self):
        """Test embedding generation."""
        litellm_url = os.getenv("LITELLM_API_BASE", "http://localhost:4000")
        litellm_key = os.getenv("LITELLM_API_KEY", "")

        if not litellm_key:
            pytest.skip("LITELLM_API_KEY is required for embedding test")

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{litellm_url}/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {litellm_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gemini-embedding",
                    "input": "test query",
                },
            )
            
            if resp.status_code == 200:
                data = resp.json()
                assert "data" in data
                assert len(data["data"]) > 0
                assert "embedding" in data["data"][0]
                # Gemini embedding should be 3072 dims
                assert len(data["data"][0]["embedding"]) == 3072


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
