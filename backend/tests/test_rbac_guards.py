"""TIER 2 item 7 — mutating vault/schema-cache endpoints must require admin.

Six mutating endpoints were authenticated but had no role guard (their siblings
all require admin), letting any logged-in user poison workspace-wide NL2SQL
grounding / schema cache. This test inspects the live route table and asserts the
``require_role(Role.ADMIN)`` dependency is wired on each — no tokens/DB needed.
"""

from __future__ import annotations

from backend.app.main import app

GUARDED_ENDPOINTS = {
    # vault writes (workspaces.py)
    "enrich_single_table",
    "add_manual_relationship",
    "update_vault_table",
    "update_column_description",
    # schema-cache writes (schema.py)
    "cache_schema",
    "delete_cached_schema",
    "delete_workspace_cache",
}


def test_mutating_vault_and_cache_endpoints_require_admin():
    guarded: dict[str, bool] = {}
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        name = getattr(endpoint, "__name__", None)
        if name in GUARDED_ENDPOINTS:
            deps = getattr(getattr(route, "dependant", None), "dependencies", [])
            # require_role(Role.ADMIN) tags its guard __qualname__ as
            # "RoleGuard.require_admin" precisely for introspection (see rbac.py).
            quals = [getattr(getattr(d, "call", None), "__qualname__", "") for d in deps]
            guarded[name] = any("require_admin" in q for q in quals)

    for name in GUARDED_ENDPOINTS:
        assert name in guarded, f"endpoint {name} not found in the route table"
        assert guarded[name], f"{name} is missing a require_role(ADMIN) guard"
