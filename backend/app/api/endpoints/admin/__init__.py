"""Admin API router — aggregates all admin endpoint sub-routers."""

from fastapi import APIRouter

from backend.app.api.endpoints.admin import (
    audit,
    consoles,
    conversations,
    encryption,
    health,
    llm_config,
    memory,
    metrics,
    team_memory,
    teams,
    tenant,
    tokens,
    users,
    vault_policies,
)

router = APIRouter()
router.include_router(memory.router, prefix="/memory", tags=["admin", "memory"])
router.include_router(team_memory.router, prefix="/team-memory", tags=["admin", "team-memory"])
router.include_router(teams.router, prefix="/teams", tags=["Admin / Teams"])
router.include_router(users.router, prefix="/users", tags=["Admin / Users"])
router.include_router(tenant.router, prefix="/tenant", tags=["admin", "tenant"])
router.include_router(audit.router, prefix="/audit-logs", tags=["admin", "audit"])
router.include_router(tokens.router, prefix="/tokens", tags=["admin", "tokens"])
router.include_router(
    vault_policies.router, prefix="/vault-policies", tags=["admin", "vault-policies"]
)
router.include_router(encryption.router, prefix="/encryption", tags=["admin", "encryption"])
router.include_router(llm_config.router, prefix="/llm-config", tags=["Admin / LLM Config"])

router.include_router(metrics.router, prefix="/metrics", tags=["Admin / Metrics"])

router.include_router(
    conversations.router, prefix="/conversations", tags=["Admin / Conversations"]
)

router.include_router(health.router, prefix="/health", tags=["Admin / Health"])
router.include_router(consoles.router, prefix="/consoles", tags=["Admin / Consoles"])
