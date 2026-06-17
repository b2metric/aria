# Sprint 11: Team & User Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use engineering-core:subagent-driven-development (recommended) or engineering-core:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement CRUD APIs and Frontend UI for managing Users and Teams in the Admin dashboard.

**Architecture:** FastAPI endpoints with strict RBAC (`can_admin` requirement) scoped to `customer_id`. Next.js frontend using standard existing UI components.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic, Next.js, TailwindCSS, Lucide React.

---

### Task 1: Backend Schemas and Teams API

**Files:**
- Create: `backend/app/schemas/organization.py`
- Create: `backend/app/api/endpoints/admin/teams.py`
- Modify: `backend/app/api/endpoints/admin/__init__.py`

- [ ] **Step 1: Create organization schemas**
Create `backend/app/schemas/organization.py` with `TeamBase`, `TeamCreate`, `TeamResponse`, `UserUpdate`, `UserResponse`. Use `pydantic.BaseModel` and `ConfigDict(from_attributes=True)`.

- [ ] **Step 2: Implement Teams API Endpoints**
Create `backend/app/api/endpoints/admin/teams.py`:
- `GET /` - List all teams for the workspace's customer_id
- `POST /` - Create a new team for the customer_id
- `DELETE /{team_id}` - Delete a team (verify it belongs to the customer_id first)
Ensure `current_user: UserContext = Depends(get_current_user)` and `current_user.can_admin` checks are present. Translate `workspace_id` to `customer_id` like in audit/vault policies.

- [ ] **Step 3: Register Teams API Router**
Modify `backend/app/api/endpoints/admin/__init__.py` to include:
```python
from backend.app.api.endpoints.admin import teams
router.include_router(teams.router, prefix="/teams", tags=["Admin / Teams"])
```

- [ ] **Step 4: Write and run Tests for Teams API**
Create `tests/api/admin/test_teams.py` and write tests for GET, POST, DELETE. Run `pytest tests/api/admin/test_teams.py` and ensure they pass.

- [ ] **Step 5: Commit**
`git add` and `git commit -m "feat(admin): implement teams api"`

---

### Task 2: Backend Users API

**Files:**
- Create: `backend/app/api/endpoints/admin/users.py`
- Modify: `backend/app/api/endpoints/admin/__init__.py`

- [ ] **Step 1: Implement Users API Endpoints**
Create `backend/app/api/endpoints/admin/users.py`:
- `GET /` - List all users for the workspace's customer_id
- `PATCH /{user_id}` - Update a user's `role` and/or `team_id` (verify user belongs to customer_id)
Enforce `can_admin` and resolve `customer_id`.

- [ ] **Step 2: Register Users API Router**
Modify `backend/app/api/endpoints/admin/__init__.py` to include:
```python
from backend.app.api.endpoints.admin import users
router.include_router(users.router, prefix="/users", tags=["Admin / Users"])
```

- [ ] **Step 3: Write and run Tests for Users API**
Create `tests/api/admin/test_users.py` and write tests for GET, PATCH. Run tests and ensure they pass.

- [ ] **Step 4: Commit**
`git add` and `git commit -m "feat(admin): implement users api"`

---

### Task 3: Frontend Layout & Teams UI

**Files:**
- Modify: `frontend/src/app/admin/layout.tsx`
- Create: `frontend/src/app/admin/users/page.tsx`

- [ ] **Step 1: Update Sidebar Navigation**
In `frontend/src/app/admin/layout.tsx`, add a new sidebar link for "Users & Teams" pointing to `/admin/users`, using the `Users` icon from `lucide-react`.

- [ ] **Step 2: Create Users & Teams Page Shell**
Create `frontend/src/app/admin/users/page.tsx`. Add a simple layout with two toggle buttons/tabs to switch between "Users" and "Teams" views.

- [ ] **Step 3: Implement Teams View**
In the same file (or a component), fetch `/api/admin/teams`. Display them in a table. Add a "Create Team" button that opens a `Dialog` to input a team name and POST to `/api/admin/teams`. Add a "Delete" button for each team.

- [ ] **Step 4: Commit**
`git add` and `git commit -m "feat(admin): implement teams UI and sidebar nav"`

---

### Task 4: Frontend Users UI

**Files:**
- Modify: `frontend/src/app/admin/users/page.tsx`

- [ ] **Step 1: Implement Users View**
Fetch `/api/admin/users`. Display users in a table (Name, Email, Role, Team).

- [ ] **Step 2: Implement User Edit Modal**
Add an "Edit" button per user that opens a `Dialog`. The dialog should allow changing the `role` (Select: Admin, Member, Viewer) and `team_id` (Select: from the fetched teams list).

- [ ] **Step 3: Handle User Update**
On save, send a `PATCH` request to `/api/admin/users/{user_id}` with the updated fields, then refresh the users list.

- [ ] **Step 4: Commit**
`git add` and `git commit -m "feat(admin): implement user management UI"`