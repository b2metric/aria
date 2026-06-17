# Admin UI: Vault RLS & Audit Logging - Design Doc

## Goal
Build the administrative interfaces for the Data Governance features implemented in the backend:
1. **Vault Access UI (`/admin/vault-access`)**: Interface to manage `TeamVaultPolicy` (app-level RLS). Allow admins to define which tables each team can access.
2. **Audit Logs UI (`/admin/audit-log`)**: Interface to view `DataAuditLog` records, allowing admins to track query executions, row counts, and data exfiltration attempts.

## Architecture & Integration

- **Frontend Framework**: Next.js (App Router), React, Tailwind CSS, shadcn/ui.
- **Backend Endpoints**: We need to create new FastAPI endpoints in `backend/app/api/endpoints/admin/`:
  - `GET /api/admin/audit-logs`: Fetch paginated audit logs.
  - `GET /api/admin/vault-policies`: Fetch team vault policies.
  - `POST/PUT /api/admin/vault-policies`: Update a team's allowed tables.
  - *Note: We need a way to list teams and tables to populate the UI.*
- **UI Location**: Add new links to the Admin Sidebar (which we will assume exists or we will add them to the main admin navigation).

## Component 1: Vault Access UI (`/admin/vault-access`)

**Purpose**: Manage `TeamVaultPolicy`.

**Data Flow**:
1. Fetch list of all teams in the workspace.
2. Fetch list of all available vault tables (reusing existing `/api/workspaces/vault/tables`).
3. Fetch existing `TeamVaultPolicy` records.
4. User selects a team -> Shows checkboxes for all tables. Checkboxes are checked if the table is in `allowed_tables`.
5. User clicks "Save" -> `PUT` request to update the policy.

**UI Layout**:
- **Left Panel**: List of Teams.
- **Right Panel**: "Allowed Tables for [Team Name]". A grid/list of checkboxes with table names and descriptions.
- **Save Button**: To persist changes.

## Component 2: Audit Logs UI (`/admin/audit-log`)

**Purpose**: View `DataAuditLog`.

**Data Flow**:
1. Fetch paginated logs from `GET /api/admin/audit-logs`.
2. Support filtering by: `user_id`, `action` (e.g., 'query_executed'), `status` ('success', 'failure', 'denied').
3. Display in a data table.

**UI Layout**:
- **Filters Toolbar**: Date range (optional), Status dropdown, Search by user/SQL.
- **Data Table**:
  - Timestamp
  - User ID / Team ID
  - Action / Status (Color-coded badges: Green=Success, Red=Failure/Denied)
  - Resource (SQL snippet or Table name)
  - Row Count (Highlight high row counts)
- **Detail Modal (Optional)**: Click a row to see the full SQL query and error message.

## Missing Backend Dependencies (To be implemented first)

Before building the frontend, we must implement the admin API endpoints:
1. `backend/app/api/endpoints/admin/audit.py`
   - `GET /` -> calls `AuditService.get_logs()`
2. `backend/app/api/endpoints/admin/vault_policies.py`
   - `GET /` -> fetch `TeamVaultPolicy`
   - `PUT /{team_id}` -> update `allowed_tables`
3. We need a basic `/api/admin/teams` endpoint (or similar) to list teams, unless we hardcode/mock it for now (since user/team management UI is also missing according to gap analysis ADM-01).

## Scope for Sprint 9 Continuation

1. **Backend Admin APIs**: Create the necessary FastAPI endpoints for Audit and Policies.
2. **Frontend Admin Pages**: Create `app/admin/audit-log/page.tsx` and `app/admin/vault-access/page.tsx`.
3. **Navigation**: Add them to the admin layout sidebar.

## Trade-offs & Simplifications
- **Team Management**: Since there is no full Team Management UI yet, the Vault Access UI will need to either fetch teams from the DB or we create a minimal endpoint to list them. If no teams exist, we might need to seed one or allow creating a policy for "default" team.
- **Pagination**: Audit logs can grow huge. The UI must support server-side pagination. `AuditService.get_logs` already supports `limit` and `offset`.