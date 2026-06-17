# Sprint 11: Team & User Management Dashboard

## 1. Overview
The ARIA product has existing database tables for `Customer` (tenant), `Team`, and `User`, but lacks a user interface and API to manage them. As an Enterprise BI tool, workspace admins must be able to group users into teams and assign roles (`admin`, `member`, `viewer`).

This sprint provides the CRUD APIs and frontend interfaces needed for User and Team administration.

## 2. Goals
1. **Backend API (`/api/admin/teams`)**: Create, list, update, and delete teams within the current workspace.
2. **Backend API (`/api/admin/users`)**: List users, update their roles (`UserRole`), and assign/reassign them to teams.
3. **Frontend Dashboard (`/admin/users`)**: A unified page to manage users and teams, utilizing Radix UI primitives and existing design patterns (light mode, B2Metric palette).
4. **Sidebar Navigation**: Integrate the new section into the admin sidebar.

## 3. Architecture & Security
- **RBAC Guard**: Both the `/api/admin/users` and `/api/admin/teams` endpoints MUST enforce the `UserContext.can_admin` check. Only Admins can manage users and teams.
- **Tenant Isolation**: All operations are strictly scoped to the `customer_id` derived from `current_user.workspace_id`.
- **Soft Delete / Cascade**:
  - Deleting a team should set `team_id = NULL` for its users (already handled by `ON DELETE SET NULL` in DB schema).
  - Keycloak handles authentication; this internal DB acts as the authorization & grouping layer.

## 4. Implementation Steps

### Phase 1: Backend APIs
- Create `backend/app/schemas/organization.py` for Pydantic models (TeamCreate, TeamResponse, UserResponse, UserUpdate).
- Create `backend/app/api/endpoints/admin/teams.py` (GET, POST, DELETE).
- Create `backend/app/api/endpoints/admin/users.py` (GET, PATCH).
- Wire them into `backend/app/api/endpoints/admin/__init__.py`.

### Phase 2: Frontend UI
- Update `frontend/src/app/admin/layout.tsx` to include the "Users & Teams" menu item.
- Create `frontend/src/app/admin/users/page.tsx`. Use a Tabs component (or separate views) for "Users" and "Teams".
- Implement `DataTable` components to list users and teams.
- Implement forms/modals to add new teams and change a user's role or team assignment.

## 5. Exclusions (Out of Scope)
- Keycloak bi-directional sync. For this sprint, users are assumed to exist in the database (or will be lazily created on first login, which is standard OIDC flow). We will focus on managing their internal ARIA roles and team associations.