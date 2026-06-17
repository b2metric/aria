"""Unit tests for Admin Users API endpoints.

Uses FastAPI TestClient with dependency overrides to mock auth and database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.auth.dependencies import get_current_user as _get_current_user_dep
from backend.app.api.endpoints.admin.users import get_db as _get_db_dep
from backend.app.auth.models import Role, UserContext
from backend.app.models.organization import Customer, User
from backend.app.models.enums import UserRole


# ── Test fixtures ───────────────────────────────────────────────────

DEFAULT_CUSTOMER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DEFAULT_TEAM_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DEFAULT_USER_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
SECOND_USER_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


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
        user_id=str(SECOND_USER_ID),
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


def make_user(
    email: str = "user@test.com",
    display_name: str = "Test User",
    role: UserRole = UserRole.MEMBER,
    id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    team_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> User:
    """Create a User model instance for testing."""
    now = datetime.now(timezone.utc)
    user = User(
        email=email,
        display_name=display_name,
        role=role,
        customer_id=customer_id or DEFAULT_CUSTOMER_ID,
        team_id=team_id,
    )
    user.id = id or uuid.uuid4()
    user.is_active = True
    user.created_at = created_at or now
    user.updated_at = updated_at or now
    return user


def make_customer() -> Customer:
    """Create a Customer model instance for testing."""
    customer = Customer(
        name="Test Corp",
        slug="test-workspace",
    )
    customer.id = DEFAULT_CUSTOMER_ID
    return customer


# ── Test helpers ────────────────────────────────────────────────────


def override_dependencies(auth_user: UserContext, mock_db: AsyncMock):
    """Set up FastAPI dependency overrides for a test."""

    async def get_current_user_override():
        return auth_user

    async def get_db_override():
        yield mock_db

    app.dependency_overrides[_get_current_user_dep] = get_current_user_override
    app.dependency_overrides[_get_db_dep] = get_db_override


def clear_overrides():
    """Clear all FastAPI dependency overrides."""
    app.dependency_overrides.clear()


# ── Tests ───────────────────────────────────────────────────────────


class TestListUsers:
    """GET /api/admin/users"""

    @pytest.fixture(autouse=True)
    def setup(self, admin_user, mock_db):
        now = datetime.now(timezone.utc)
        self.user1 = make_user("alice@test.com", "Alice", UserRole.ADMIN, DEFAULT_USER_ID, DEFAULT_CUSTOMER_ID, DEFAULT_TEAM_ID, now, now)
        self.user2 = make_user("bob@test.com", "Bob", UserRole.MEMBER, SECOND_USER_ID, DEFAULT_CUSTOMER_ID, None, now, now)

        async def execute_side_effect(stmt, *args, **kwargs):
            result = MagicMock()
            stmt_str = str(stmt)
            if "customers.slug" in stmt_str:
                result.scalar_one_or_none.return_value = DEFAULT_CUSTOMER_ID
            elif "users.customer_id" in stmt_str:
                result.scalars.return_value.all.return_value = [self.user1, self.user2]
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        override_dependencies(admin_user, mock_db)
        yield
        clear_overrides()

    def test_list_users_success(self):
        """Should return list of users for the workspace."""
        client = TestClient(app)
        response = client.get("/api/admin/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["email"] == "alice@test.com"
        assert data[0]["display_name"] == "Alice"
        assert data[0]["role"] == "admin"
        assert data[0]["team_id"] == str(DEFAULT_TEAM_ID)
        assert data[1]["email"] == "bob@test.com"
        assert data[1]["team_id"] is None

    def test_list_users_empty(self, admin_user, mock_db):
        """Should return empty list when no users exist."""
        async def execute_side_effect(stmt, *args, **kwargs):
            result = MagicMock()
            stmt_str = str(stmt)
            if "customers.slug" in stmt_str:
                result.scalar_one_or_none.return_value = DEFAULT_CUSTOMER_ID
            elif "users.customer_id" in stmt_str:
                result.scalars.return_value.all.return_value = []
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        override_dependencies(admin_user, mock_db)
        client = TestClient(app)
        response = client.get("/api/admin/users")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_users_forbidden_for_non_admin(self, non_admin_user, mock_db):
        """Non-admin should get 403."""
        override_dependencies(non_admin_user, mock_db)
        client = TestClient(app)
        response = client.get("/api/admin/users")
        assert response.status_code == 403


class TestUpdateUser:
    """PATCH /api/admin/users/{user_id}"""

    @pytest.fixture(autouse=True)
    def setup(self, admin_user, mock_db):
        self.admin_user = admin_user
        self.mock_db = mock_db
        self.user = make_user("alice@test.com", "Alice", UserRole.MEMBER, DEFAULT_USER_ID, DEFAULT_CUSTOMER_ID, DEFAULT_TEAM_ID)
        yield
        clear_overrides()

    def _setup_execute(self, user_to_find=None):
        """Configure mock_db.execute for a user lookup scenario."""
        target_user = user_to_find or self.user

        async def execute_side_effect(stmt, *args, **kwargs):
            result = MagicMock()
            stmt_str = str(stmt)
            if "customers.slug" in stmt_str:
                result.scalar_one_or_none.return_value = DEFAULT_CUSTOMER_ID
            elif "users.id" in stmt_str and "users.customer_id" in stmt_str:
                result.scalar_one_or_none.return_value = target_user
            return result

        self.mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    def test_update_user_role(self):
        """Should update a user's role."""
        self._setup_execute()
        override_dependencies(self.admin_user, self.mock_db)
        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{DEFAULT_USER_ID}",
            json={"role": "admin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert data["email"] == "alice@test.com"

    def test_update_user_team(self):
        """Should update a user's team_id."""
        new_team_id = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
        self._setup_execute()
        override_dependencies(self.admin_user, self.mock_db)
        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{DEFAULT_USER_ID}",
            json={"team_id": str(new_team_id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == str(new_team_id)

    def test_update_user_remove_team(self):
        """Should remove a user from their team (team_id=null)."""
        self._setup_execute()
        override_dependencies(self.admin_user, self.mock_db)
        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{DEFAULT_USER_ID}",
            json={"team_id": None},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] is None

    def test_update_user_role_and_team(self):
        """Should update both role and team_id."""
        new_team_id = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
        self._setup_execute()
        override_dependencies(self.admin_user, self.mock_db)
        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{DEFAULT_USER_ID}",
            json={"role": "viewer", "team_id": str(new_team_id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "viewer"
        assert data["team_id"] == str(new_team_id)

    def test_update_user_not_found(self):
        """Should return 404 when user doesn't belong to customer."""
        async def execute_side_effect(stmt, *args, **kwargs):
            result = MagicMock()
            stmt_str = str(stmt)
            if "customers.slug" in stmt_str:
                result.scalar_one_or_none.return_value = DEFAULT_CUSTOMER_ID
            elif "users.id" in stmt_str:
                result.scalar_one_or_none.return_value = None
            return result

        self.mock_db.execute = AsyncMock(side_effect=execute_side_effect)
        override_dependencies(self.admin_user, self.mock_db)
        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{uuid.uuid4()}",
            json={"role": "admin"},
        )
        assert response.status_code == 404

    def test_update_user_forbidden_for_non_admin(self, non_admin_user, mock_db):
        """Non-admin should get 403."""
        override_dependencies(non_admin_user, mock_db)
        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{DEFAULT_USER_ID}",
            json={"role": "admin"},
        )
        assert response.status_code == 403

    def test_update_user_invalid_role(self):
        """Should reject invalid role values."""
        self._setup_execute()
        override_dependencies(self.admin_user, self.mock_db)
        client = TestClient(app)
        response = client.patch(
            f"/api/admin/users/{DEFAULT_USER_ID}",
            json={"role": "superadmin"},
        )
        assert response.status_code == 422
