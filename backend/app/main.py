"""ARIA FastAPI application."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.app import __version__
from backend.app.api.query import router as query_router
from backend.app.api.schema import router as schema_router
from backend.app.api.workspaces import router as workspaces_router
from backend.app.api.endpoints.admin import router as admin_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.auth.dependencies import CurrentUser, WorkspaceID, get_current_user
from backend.app.auth.models import Role
from backend.app.auth.rbac import require_role, require_sql_access

# ── Lifespan ─────────────────────────────────────────────────────────────

logger = logging.getLogger("aria.startup")


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup validation — fail loudly instead of running degraded.

    Catches the "system up but login broken" / "garbage SQL" classes:
    a dummy/missing LiteLLM key, or an unreachable/misconfigured Keycloak JWKS
    endpoint (the ``/auth`` path trap). Probes the EXACT JWKS URL the auth layer
    uses. Skip for tests/offline with ``ARIA_SKIP_STARTUP_CHECKS=1``.
    """
    from backend.app.core.config import get_settings

    if not _truthy(os.environ.get("ARIA_SKIP_STARTUP_CHECKS")):
        settings = get_settings()
        problems = settings.validate_runtime()
        # Keycloak (JVM + realm import) and Traefik routing can lag the backend on
        # a cold `docker compose up`; a single probe races and kills the backend
        # (JWKS 502 -> startup fail -> exit -> api 502, which surfaces in the browser
        # as a CORS error). Retry with backoff up to ~60s before failing loud — this
        # tolerates slow startup WITHOUT weakening the gate: a genuinely unreachable
        # or misconfigured Keycloak still fails after the retries are exhausted.
        attempts = int(os.environ.get("ARIA_JWKS_STARTUP_ATTEMPTS", "30"))
        delay = float(os.environ.get("ARIA_JWKS_STARTUP_DELAY", "2.0"))
        jwks_problem: str | None = None
        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(
                    verify=settings.keycloak_verify_ssl, timeout=5.0
                ) as client:
                    resp = await client.get(settings.keycloak_jwks_url)
                if resp.status_code == 200:
                    jwks_problem = None
                    break
                jwks_problem = (
                    f"Keycloak JWKS {settings.keycloak_jwks_url} returned "
                    f"{resp.status_code} (expected 200). Logins will fail "
                    "(check the /auth path / realm)."
                )
            except Exception as exc:  # noqa: BLE001 — startup gate must report any failure
                jwks_problem = (
                    f"Keycloak JWKS {settings.keycloak_jwks_url} unreachable: {exc!r}. "
                    "Logins will fail."
                )
            if attempt < attempts:
                logger.warning(
                    "Keycloak JWKS not ready (%d/%d): %s — retrying in %.1fs",
                    attempt, attempts, jwks_problem, delay,
                )
                await asyncio.sleep(delay)
        if jwks_problem:
            problems.append(jwks_problem)
        if problems:
            for p in problems:
                logger.critical("STARTUP CHECK FAILED: %s", p)
            raise RuntimeError(
                "ARIA startup checks failed (set ARIA_SKIP_STARTUP_CHECKS=1 to "
                "bypass for offline work):\n  - " + "\n  - ".join(problems)
            )
        logger.info(
            "Startup checks passed: LiteLLM key valid; Keycloak JWKS reachable at %s",
            settings.keycloak_jwks_url,
        )
    yield


app = FastAPI(
    title="ARIA",
    description="AI-Driven Analytics Platform",
    version=__version__,
    lifespan=lifespan,
)

app.include_router(query_router)
app.include_router(schema_router)
app.include_router(workspaces_router)
app.include_router(dashboard_router)
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])

# ── CORS (dev: allow all) ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://aria.localhost", "http://localhost:3000", "http://localhost:3003", "http://127.0.0.1:3000", "http://127.0.0.1:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Public ───────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    """Unauthenticated health check."""
    return {"status": "ok", "version": __version__}


# ── Authenticated ────────────────────────────────────────────────────────


@app.get("/me")
async def me(user: CurrentUser):
    """Return the authenticated user's profile and permissions."""
    return {
        "sub": user.sub,
        "user_id": user.user_id,
        "workspace_id": user.workspace_id,
        "team_id": user.team_id,
        "role": user.role.value,
        "email": user.email,
        "name": user.name,
        "preferred_username": user.preferred_username,
        "permissions": {
            "can_view_sql": user.can_view_sql,
            "can_manage_team": user.can_manage_team,
            "can_manage_workspace": user.can_manage_workspace,
            "can_admin": user.can_admin,
        },
    }


@app.get("/workspace/{workspace_id}/info")
async def workspace_info(
    workspace_id: str,
    user: CurrentUser,
):
    """Return workspace metadata — user must belong to this workspace."""
    if user.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have access to workspace {workspace_id}",
        )
    return {
        "workspace_id": workspace_id,
        "accessed_by": user.user_id,
        "role": user.role.value,
    }


# ── Role-gated ───────────────────────────────────────────────────────────


@app.get("/admin/dashboard")
async def admin_dashboard(
    user: CurrentUser,
    _: None = Depends(require_role(Role.ADMIN)),
):
    """Admin-only dashboard."""
    return {
        "message": "Welcome to the admin dashboard",
        "user": user.user_id,
        "workspace": user.workspace_id,
    }


@app.get("/team/manage")
async def team_management(
    user: CurrentUser,
    _: None = Depends(require_role(Role.TEAM_LEAD)),
):
    """Team management — available to team_lead and admin roles."""
    return {
        "message": "Team management panel",
        "team_id": user.team_id,
        "role": user.role.value,
    }


@app.get("/queries/sql-preview")
async def sql_preview(
    user: CurrentUser,
    _: None = Depends(require_sql_access),
):
    """Preview generated SQL — requires can_view_sql permission."""
    return {
        "message": "SQL preview",
        "can_view_sql": user.can_view_sql,
        "role": user.role.value,
    }


@app.get("/workspace-scoped/query")
async def workspace_scoped_query(workspace_id: WorkspaceID):
    """Example endpoint that only needs workspace_id, not full user."""
    return {
        "workspace_id": workspace_id,
        "message": "Query executed in workspace context",
    }
