"""Admin API router — aggregates all admin endpoint sub-routers."""

from fastapi import APIRouter

from backend.app.api.endpoints.admin import audit
from backend.app.api.endpoints.admin import memory
from backend.app.api.endpoints.admin import team_memory
from backend.app.api.endpoints.admin import teams
from backend.app.api.endpoints.admin import tenant
from backend.app.api.endpoints.admin import tokens
from backend.app.api.endpoints.admin import users
from backend.app.api.endpoints.admin import metrics
from backend.app.api.endpoints.admin import health
from backend.app.api.endpoints.admin import vault_policies
from backend.app.api.endpoints.admin import encryption

router = APIRouter()
router.include_router(memory.router, prefix="/memory", tags=["admin", "memory"])
router.include_router(team_memory.router, prefix="/team-memory", tags=["admin", "team-memory"])
router.include_router(teams.router, prefix="/teams", tags=["Admin / Teams"])
router.include_router(users.router, prefix="/users", tags=["Admin / Users"])
router.include_router(tenant.router, prefix="/tenant", tags=["admin", "tenant"])
router.include_router(audit.router, prefix="/audit-logs", tags=["admin", "audit"])
router.include_router(tokens.router, prefix="/tokens", tags=["admin", "tokens"])
router.include_router(vault_policies.router, prefix="/vault-policies", tags=["admin", "vault-policies"])
router.include_router(encryption.router, prefix="/encryption", tags=["admin", "encryption"])

router.include_router(metrics.router, prefix="/metrics", tags=["Admin / Metrics"])

router.include_router(health.router, prefix="/health", tags=["Admin / Health"])
