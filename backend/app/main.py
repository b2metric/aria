"""ARIA FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.app import __version__
from backend.app.api.query import router as query_router
from backend.app.api.schema import router as schema_router
from backend.app.api.workspaces import router as workspaces_router
from backend.app.auth.dependencies import CurrentUser, WorkspaceID, get_current_user
from backend.app.auth.models import Role
from backend.app.auth.rbac import require_role, require_sql_access

# ── Lifespan ─────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
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

# ── CORS (dev: allow all) ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
