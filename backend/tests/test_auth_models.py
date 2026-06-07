"""Smoke test — verify all auth modules import correctly."""
from backend.app.auth.models import Role, TokenPayload, UserContext
from backend.app.core.config import Settings, get_settings


def test_role_enum():
    assert Role.ADMIN.value == "admin"
    assert Role.TEAM_LEAD.value == "team_lead"
    assert Role.ANALYST.value == "analyst"
    assert Role.VIEWER.value == "viewer"


def test_role_hierarchy():
    assert Role.ADMIN.can(Role.ADMIN)
    assert Role.ADMIN.can(Role.ANALYST)
    assert Role.ADMIN.can(Role.VIEWER)
    assert Role.TEAM_LEAD.can(Role.ANALYST)
    assert Role.TEAM_LEAD.can(Role.VIEWER)
    assert not Role.TEAM_LEAD.can(Role.ADMIN)
    assert not Role.ANALYST.can(Role.TEAM_LEAD)
    assert not Role.VIEWER.can(Role.ANALYST)


def test_role_from_string():
    assert Role.from_string("admin") == Role.ADMIN
    assert Role.from_string("ADMIN") == Role.ADMIN
    assert Role.from_string("Admin") == Role.ADMIN
    assert Role.from_string("team_lead") == Role.TEAM_LEAD


def test_settings_defaults():
    s = get_settings()
    assert "localhost:8080" in s.keycloak_url
    assert s.keycloak_realm == "aria"
    assert s.keycloak_client_id == "aria-backend"
    assert "/realms/aria" in s.keycloak_issuer


def test_user_context_permissions():
    admin = UserContext(
        sub="u1",
        user_id="u1",
        workspace_id="ws1",
        team_id="t1",
        role=Role.ADMIN,
        can_view_sql=True,
        can_manage_team=True,
        can_manage_workspace=True,
        can_admin=True,
    )
    assert admin.can_view_sql
    assert admin.can_admin

    viewer = UserContext(
        sub="u2",
        user_id="u2",
        workspace_id="ws1",
        team_id="t1",
        role=Role.VIEWER,
        can_view_sql=False,
        can_manage_team=False,
        can_manage_workspace=False,
        can_admin=False,
    )
    assert not viewer.can_view_sql
    assert not viewer.can_admin
