"""Unit tests for Admin Teams API endpoints.

Uses FastAPI TestClient with dependency overrides to mock auth and database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.auth.dependencies import get_current_user as _get_current_user_dep
from backend.app.api.endpoints.admin.teams import get_db as _get_db_dep
from backend.app.auth.models import Role, UserContext
from backend.app.models.organization import Customer, Team
from backend.app.models.enums import UserRole


# ── Test fixtures ───────────────────────────────────────────────────

DEFAULT_CUSTOMER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DEFAULT_TEAM_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DEFAULT_USER_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


@pytest.fixture
def admin_user() -> UserContext:
    """An admin user context for testing."""
    return UserContext(
        sub="test-keycloak-id",
        user_id=str(DEFAULT_USER_ID),
        workspace_id="test-workspace",
        team_id=str(DEFAULT_TEAM_ID),
        role=Role.ADMIN,
        email="admin@test.com",
        name="Test Admin",
        preferred_username="admin",
        can_admin=True,
        can_manage_team=True,
        can_manage_workspace=True,
        can_view_sql=True,
    )


@pytest.fixture
def non_admin_user() -> UserContext:
    """A non-admin user context for testing."""
    return UserContext(
        sub="test-viewer-id",
        user_id=str(uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")),
        workspace_id="test-workspace",
        role=Role.VIEWER,
        email="viewer@test.com",
        name="Test Viewer",
        can_admin=False,
    )


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def make_team(
    name: str = "Engineering",
    id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> Team:
    """Create a Team model instance for testing."""
    now = datetime.now(timezone.utc)
    team = Team(
        name=name,
        customer_id=customer_id or DEFAULT_CUSTOMER_ID,
    )
    team.id = id or uuid.uuid4()
    team.created_at = created_at or now
    team.updated_at = updated_at or now
    return team


def make_customer() -> Customer:
    """Create a Customer model instance for testing."""
    customer = Customer(
        name="Test Corp",
        slug="test-workspace",
    )
    customer.id = DEFAULT_CUSTOMER_ID
    return customer


# ── Test helpers ────────────────────────────────────────────────────


def setup_mock_customer_lookup(mock_db, customer: Customer | None = None):
    """Configure the mock session to return a Customer on ID lookup."""
    c = customer or make_customer()

    async def execute_side_effect(stmt, *args, **kwargs):
        result = MagicMock()
        # Figure out which kind of query this is
        stmt_str = str(stmt)
        if hasattr(stmt, "whereclause"):
            stmt_str = str(stmt.whereclause)

        if "customers" in str(stmt) and "customers.slug" in str(stmt):
            result.scalar_one_or_none.return_value = c.id
        elif "teams" in str(stmt) and "teams.customer_id" in str(stmt):
            # Check if it's a specific team lookup
            if "teams.id" in str(stmt):
                result.scalar_one_or_none.return_value = None  # Default no match
            else:
                result.scalars.return_value.all.return_value = []
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)
    return mock_db


def override_dependencies(admin_user, mock_db):
    """Set up FastAPI dependency overrides for a test."""
    async def get_current_user_override():
        return admin_user

    async def get_db_override():
        yield mock_db

    app.dependency_overrides[_get_current_user_dep] = get_current_user_override
    app.dependency_overrides[_get_db_dep] = get_db_override


def clear_overrides():
    """Clear all FastAPI dependency overrides."""
    app.dependency_overrides.clear()


# ── Tests ───────────────────────────────────────────────────────────


class TestListTeams:
    """GET /api/admin/teams"""

    @pytest.fixture(autouse=True)
    def setup(self, admin_user, mock_db):
        """Setup and teardown dependency overrides."""
        # Build a more complete mock for listing teams
        now = datetime.now(timezone.utc)
        team1 = make_team("Engineering", DEFAULT_TEAM_ID, DEFAULT_CUSTOMER_ID, now, now)
        team2 = make_team("Product", uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"), DEFAULT_CUSTOMER_ID, now, now)

        # We need to handle both the customer lookup AND the team list
        async def execute_side_effect(stmt, *args, **kwargs):
            result = MagicMock()
            stmt_str = str(stmt)
            if "customers.slug" in stmt_str:
                result.scalar_one_or_none.return_value = DEFAULT_CUSTOMER_ID
            elif "teams.customer_id" in stmt_str:
                result.scalars.return_value.all.return_value = [team1, team2]
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        override_dependencies(admin_user, mock_db)
        yield
        clear_overrides()

    def test_list_teams_success(self):
        """Should return list of teams for the workspace."""
        client = TestClient(app)
        response = client.get("/api/admin/teams")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == "Engineering"
        assert data[1]["name"] == "Product"
        assert data[0]["customer_id"] == str(DEFAULT_CUSTOMER_ID)

    def test_list_teams_empty(self, admin_user, mock_db):
        """Should return empty list when no teams exist."""
        async def execute_side_effect(stmt, *args, **kwargs):
            result = MagicMock()
            stmt_str = str(stmt)
            if "customers.slug" in stmt_str:
                result.scalar_one_or_none.return_value = DEFAULT_CUSTOMER_ID
            elif "teams.customer_id" in stmt_str:
                result.scalars.return_value.all.return_value = []
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        override_dependencies(admin_user, mock_db)
        client = TestClient(app)
        response = client.get("/api/admin/teams")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_teams_forbidden_for_non_admin(self, non_admin_user, mock_db):
        """Non-admin should get 403."""
        override_dependencies(non_admin_user, mock_db)
        client = TestClient(app)
        response = client.get("/api/admin/teams")
        assert response.status_code == 403


class TestCreateTeam:
    """POST /api/admin/teams"""

    @pytest.fixture(autouse=True)
    def setup(self, admin_user, mock_db):
        now = datetime.now(timezone.utc)

        async def execute_side_effect(stmt, *args, **kwargs):
            result = MagicMock()
            stmt_str = str(stmt)
            if "customers.slug" in stmt_str:
                result.scalar_one_or_none.return_value = DEFAULT_CUSTOMER_ID
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        def refresh_side_effect(team):
            team.id = DEFAULT_TEAM_ID
            team.created_at = now
            team.updated_at = now

        mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)
        override_dependencies(admin_user, mock_db)
        yield
        clear_overrides()

    def test_create_team_success(self):
        """Should create a new team and return it."""
        client = TestClient(app)
        response = client.post(
            "/api/admin/teams", json={"name": "Engineering"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Engineering"
        assert data["customer_id"] == str(DEFAULT_CUSTOMER_ID)
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_team_empty_name(self):
        """Should reject empty team name."""
        client = TestClient(app)
        response = client.post(
            "/api/admin/teams", json={"name": ""}
        )
        assert response.status_code == 422

    def test_create_team_forbidden_for_non_admin(self, non_admin_user, mock_db):
        """Non-admin should get 403."""
        override_dependencies(non_admin_user, mock_db)
        client = TestClient(app)
        response = client.post(
            "/api/admin/teams", json={"name": "Engineering"}
        )
        assert response.status_code == 403


class TestDeleteTeam:
    """DELETE /api/admin/teams/{team_id}"""

    @pytest.fixture(autouse=True)
    def setup(self, admin_user, mock_db):
        self.team = make_team("Engineering", DEFAULT_TEAM_ID, DEFAULT_CUSTOMER_ID)

        async def execute_side_effect(stmt, *args, **kwargs):
            result = MagicMock()
            stmt_str = str(stmt)
            if "customers.slug" in stmt_str:
                result.scalar_one_or_none.return_value = DEFAULT_CUSTOMER_ID
            elif "teams.id" in stmt_str and "teams.customer_id" in stmt_str:
                result.scalar_one_or_none.return_value = self.team
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        override_dependencies(admin_user, mock_db)
        yield
        clear_overrides()

    def test_delete_team_success(self):
        """Should delete a team and return 204."""
        client = TestClient(app)
        response = client.delete(f"/api/admin/teams/{DEFAULT_TEAM_ID}")
        assert response.status_code == 204

    def test_delete_team_not_found(self, admin_user, mock_db):
        """Should return 404 when team doesn't belong to customer."""
        async def execute_side_effect(stmt, *args, **kwargs):
            result = MagicMock()
            stmt_str = str(stmt)
            if "customers.slug" in stmt_str:
                result.scalar_one_or_none.return_value = DEFAULT_CUSTOMER_ID
            elif "teams.id" in stmt_str:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        override_dependencies(admin_user, mock_db)
        client = TestClient(app)
        response = client.delete(f"/api/admin/teams/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_delete_team_forbidden_for_non_admin(self, non_admin_user, mock_db):
        """Non-admin should get 403."""
        override_dependencies(non_admin_user, mock_db)
        client = TestClient(app)
        response = client.delete(f"/api/admin/teams/{DEFAULT_TEAM_ID}")
        assert response.status_code == 403
