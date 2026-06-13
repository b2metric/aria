"""Admin API router — aggregates all admin endpoint sub-routers."""

from fastapi import APIRouter

from backend.app.api.endpoints.admin import audit
from backend.app.api.endpoints.admin import memory
from backend.app.api.endpoints.admin import team_memory
from backend.app.api.endpoints.admin import tenant
from backend.app.api.endpoints.admin import vault_policies

router = APIRouter()
router.include_router(memory.router, prefix="/memory", tags=["admin", "memory"])
router.include_router(team_memory.router, prefix="/team-memory", tags=["admin", "team-memory"])
router.include_router(tenant.router, prefix="/tenant", tags=["admin", "tenant"])
router.include_router(audit.router, prefix="/audit-logs", tags=["admin", "audit"])
router.include_router(vault_policies.router, prefix="/vault-policies", tags=["admin", "vault-policies"])
