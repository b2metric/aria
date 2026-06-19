import asyncio
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from backend.app.api.query import _get_redis
from backend.app.auth.dependencies import get_current_user
from backend.app.core.config import get_settings
from backend.app.db.session import get_engine

log = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def get_system_health(current_user: Any = Depends(get_current_user)):
    """Get detailed health status of all system dependencies."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
        
    settings = get_settings()
    results = {
        "postgres": {"status": "unknown", "latency_ms": 0},
        "redis": {"status": "unknown", "latency_ms": 0},
        "keycloak": {"status": "unknown", "latency_ms": 0},
        "qdrant": {"status": "unknown", "latency_ms": 0},
        "litellm": {"status": "unknown", "latency_ms": 0},
        "customer_dbs": {"status": "unknown", "latency_ms": 0}
    }

    # 0. Check Customer Database Connectivities
    try:
        from backend.app.db.executor import get_executor
        from backend.app.db.models import DBConfig
        from backend.app.services.crypto import async_decrypt_password

        workspace_id = getattr(current_user, "workspace_id", None) or "default"
        async with get_engine().connect() as conn:
            # Only ping THIS tenant's own database(s) — never other customers' DBs.
            cid = (
                await conn.execute(
                    text("SELECT id FROM customers WHERE slug = :ws"), {"ws": workspace_id}
                )
            ).scalar()
            configs = await conn.execute(
                text(
                    "SELECT id, customer_id, db_type, host, port, database, username, encrypted_password "
                    "FROM customer_db_configs WHERE is_active = true AND customer_id = :cid"
                ),
                {"cid": cid},
            )
            conf_rows = configs.fetchall() if cid else []

            if not conf_rows:
                results["customer_dbs"] = {"status": "healthy", "error": "No active customer DBs configured yet"}
            else:
                db_success = 0
                db_errors = []
                start = asyncio.get_event_loop().time()
                for c in conf_rows:
                    db_type_val = c.db_type if hasattr(c, "db_type") and isinstance(c.db_type, str) else (c.db_type.value if hasattr(c.db_type, "value") else str(c.db_type))
                    c_config = DBConfig(
                        db_type=db_type_val,
                        host=c.host,
                        port=c.port,
                        database=c.database,
                        username=c.username,
                        password=await async_decrypt_password(c.encrypted_password, c.customer_id, conn)
                    )
                    executor = get_executor(c_config)
                    # We can't really do an async ping easily via sync executor without run_in_executor,
                    # but since this is health check let's run a quick SELECT 1
                    try:
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, lambda conf=c_config: get_executor(conf).execute("SELECT 1" if db_type_val != "oracle" else "SELECT 1 FROM DUAL"))
                        db_success += 1
                    except Exception as e:
                        log.warning("Customer DB %s (%s) unreachable: %s", c.id, c.host, e)
                        db_errors.append(f"DB config {c.id} unreachable")

                latency = round((asyncio.get_event_loop().time() - start) * 1000)
                if db_success == len(conf_rows):
                    results["customer_dbs"] = {"status": "healthy", "latency_ms": latency}
                else:
                    results["customer_dbs"] = {
                        "status": "warning" if db_success > 0 else "unhealthy",
                        "latency_ms": latency,
                        "error": " | ".join(db_errors)
                    }
    except Exception:
        log.exception("Customer DB health check failed")
        results["customer_dbs"] = {"status": "unhealthy", "error": "health check setup failed"}
    
    # 1. Postgres
    try:
        engine = get_engine()
        start = asyncio.get_event_loop().time()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        results["postgres"] = {
            "status": "healthy",
            "latency_ms": round((asyncio.get_event_loop().time() - start) * 1000)
        }
    except Exception as e:
        results["postgres"] = {"status": "unhealthy", "error": str(e)}

    # 2. Redis
    try:
        redis = await _get_redis()
        start = asyncio.get_event_loop().time()
        await redis.ping()
        results["redis"] = {
            "status": "healthy",
            "latency_ms": round((asyncio.get_event_loop().time() - start) * 1000)
        }
        await redis.aclose()
    except Exception as e:
        results["redis"] = {"status": "unhealthy", "error": str(e)}

    # Check external services via HTTP
    async with httpx.AsyncClient(timeout=5.0) as client:
        # 3. Keycloak
        try:
            jwks_url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"
            start = asyncio.get_event_loop().time()
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            results["keycloak"] = {
                "status": "healthy",
                "latency_ms": round((asyncio.get_event_loop().time() - start) * 1000)
            }
        except Exception as e:
            results["keycloak"] = {"status": "unhealthy", "error": str(e)}

        # 4. Qdrant
        try:
            start = asyncio.get_event_loop().time()
            # Qdrant ready endpoint
            resp = await client.get(f"{settings.qdrant_url}/readyz")
            if resp.status_code in [200, 404]: # 404 might happen if endpoint varies, but connection succeeds
                results["qdrant"] = {
                    "status": "healthy",
                    "latency_ms": round((asyncio.get_event_loop().time() - start) * 1000)
                }
            else:
                results["qdrant"] = {"status": "unhealthy", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            results["qdrant"] = {"status": "unhealthy", "error": str(e)}

        # 5. LiteLLM — liveness probe only. The proxy's /health endpoint requires the
        # master key (returns 401 without it) AND runs an expensive per-model check;
        # /health/liveliness is unauthenticated and just answers "is the proxy up?".
        try:
            base = str(settings.litellm_api_base).rstrip("/")
            if base.endswith("/v1"):
                base = base[:-len("/v1")].rstrip("/")
            start = asyncio.get_event_loop().time()
            resp = await client.get(f"{base}/health/liveliness")
            latency_ms = round((asyncio.get_event_loop().time() - start) * 1000)
            if resp.status_code == 200:
                results["litellm"] = {
                    "status": "healthy",
                    "latency_ms": latency_ms
                }
            else:
                results["litellm"] = {
                    "status": "unhealthy",
                    "latency_ms": latency_ms,
                    "error": f"HTTP {resp.status_code}"
                }
        except Exception as e:
            results["litellm"] = {"status": "unhealthy", "error": str(e)}

    return results
