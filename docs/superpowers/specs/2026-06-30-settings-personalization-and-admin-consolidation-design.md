# Settings Personalization & Admin Consolidation — Design

**Date:** 2026-06-30
**Status:** Approved (brainstorming) — pending spec review
**Scope:** Frontend reorganization only. No backend changes.

## Problem

The `/settings` area currently exposes workspace-administration surfaces — **Team Members**,
**Database Connection**, **Encryption** — plus an empty **General** placeholder. Two problems:

1. **Security/RBAC gap.** The settings shell (`frontend/src/app/settings/layout.tsx`) has **no
   `AdminGuard`**, so any authenticated user (even `viewer`) can open the DB connection and
   encryption screens. The corresponding `/admin/*` pages *are* guarded.
2. **Duplication.** These settings pages duplicate functionality that already lives in the
   guarded admin panel: `/admin/users` (Users & Teams), `/admin/tenant-config` (DB credentials).
   The duplication is at the **frontend** layer — both pages call the same single backend route.

Meanwhile `/settings` has **no personal surface**: no user profile view and no in-page theme
preference (dark mode is only a sidebar toggle persisted to `localStorage`).

## Goal

Make `/settings` a **personal** area (profile + appearance) and consolidate all
workspace-administration into the guarded `/admin` panel, without leaving orphaned or duplicate
backend endpoints.

## Decisions (from brainstorming)

- **Placement:** Team/DB/Encryption move into the existing `/admin` panel (single `admin` role,
  existing `AdminGuard`). No new customer-admin role.
- **Profile:** read-only for now. Password/email editing is **out of scope** this phase.
- **Theme persistence:** cookie + `localStorage`, per-browser (no server/DB persistence).
- **Overlap handling:** deduplicate — drop the redundant settings pages; only **Encryption**
  genuinely relocates (it has no admin equivalent yet).
- **Backend:** no duplicate/orphan endpoints exist; backend stays untouched (see below).

## Design

### A. `/settings` → personal area

`/settings` redirect target changes `general` → `profile`. The settings sidebar
(`settings/layout.tsx`) is reduced to **Profile**, **Appearance** (+ "Back to App"). It remains
ungated (personal, all authenticated users) — acceptable because it no longer holds sensitive
surfaces.

- **`/settings/profile`** (new): read-only card. Displays display name, email, role(s), team —
  sourced from the NextAuth session (Keycloak JWT claims). No edit actions. A muted note may
  indicate that credential changes are managed elsewhere / coming later.
- **`/settings/appearance`** (new): theme control (Light / Dark / System) using the shared theme
  mechanism (below). This is the in-settings home for the dark-mode preference.
- **Removed:** `/settings/general` (placeholder), `/settings/team`, `/settings/database`,
  `/settings/encryption`.

### B. Encryption → `/admin/encryption` (new)

The content of `settings/encryption/page.tsx` (CMEK provider status + reachability badge,
provider switch form, "Rotate key", and the `cmek_*` audit-log panel) relocates verbatim to
**`/admin/encryption/page.tsx`**. It inherits the admin layout's `AdminGuard`. An **Encryption**
nav item is added to the admin sidebar (`admin/layout.tsx`), placed near Tenant Config.

It continues to call the unchanged endpoints: `GET /api/admin/encryption/status`,
`GET/PATCH /api/admin/encryption`, `POST /api/admin/encryption/rotate`,
`GET /api/admin/audit-logs`.

### C. Deduplication

- **Team Members** — delete `/settings/team`. `/admin/users` (Users & Teams) already covers it
  with a richer feature set (role, team, SQL-visibility tri-state, Keycloak-propagating delete).
- **Database Connection** — delete `/settings/database`. `/admin/tenant-config` already covers DB
  credentials (plus token/row limits, language).
- **Encryption** — relocated per (B), not duplicated.

### D. Theme persistence (cookie + localStorage)

- `ThemeToggle` and the Appearance control share one apply function: set
  `document.documentElement.setAttribute('data-theme', value)`, then persist to **both**
  `localStorage.theme` and a cookie (`theme=<value>; path=/; max-age=31536000; samesite=lax`),
  each in try/catch.
- The no-flicker inline `<head>` script in `app/layout.tsx` resolves the initial theme in order:
  `localStorage.theme` → cookie `theme` → `prefers-color-scheme`. Adding the cookie read keeps
  the existing fast path and makes the value SSR-readable for the future.
- "System" maps to following `prefers-color-scheme` (no stored explicit value, or a stored
  `"system"` sentinel that defers to the media query).

### E. Navigation / RBAC outcome

- Sidebar (`components/Sidebar.tsx`): "Settings" stays visible to everyone but now personal.
  "Admin Panel" (admin-only) is unchanged except its sub-nav gains **Encryption**.
- Net security win: DB/encryption/team surfaces are no longer reachable by non-admins.

### F. Backend — no changes

Endpoint analysis confirmed **no duplicate or orphaned backend routes**. Every endpoint the
deleted pages called is still used by a kept admin page:

| Endpoint | Kept caller | Verdict |
|---|---|---|
| `GET/POST/PATCH/DELETE /api/admin/users` | `/admin/users`, `/admin/tokens`, `lib/api.ts` | KEEP |
| `GET/POST/DELETE /api/admin/teams` (+ `/sync-groups`) | `/admin/users`, `/admin/vault-access`, `/admin/team-memory`, `/admin/tokens` | KEEP |
| `GET/PATCH /api/admin/tenant` | `/admin/tenant-config`, `/onboarding/database` | KEEP |
| `POST /api/workspaces/vault/sync` | `/admin/schema`, `/admin/vault-access`, `/onboarding/sync` | KEEP |
| `/api/admin/encryption/*` | **new** `/admin/encryption` (same PR) | KEEP |
| `GET /api/admin/audit-logs` | `/admin/audit-log` | KEEP |

**Hard constraint:** `/admin/encryption` must ship in the **same PR** that deletes
`/settings/encryption`, so the four encryption endpoints are never frontend-dark and are not
mistaken for dead code.

## Testing (TDD)

- New `/settings/profile`: renders session-derived fields read-only; no edit controls.
- New `/settings/appearance`: theme control writes both `localStorage` and cookie; updates
  `data-theme`.
- `ThemeToggle`: extend existing test to assert cookie is written alongside `localStorage`.
- `settings/layout`: sidebar lists only Profile + Appearance (asserts Team/Database/Encryption
  are gone).
- `admin/layout`: sidebar includes Encryption.
- `/admin/encryption`: renders moved CMEK UI and calls the encryption endpoints.
- Removed routes: `/settings/team|database|encryption|general` no longer resolve (or redirect to
  `/settings/profile`).

## Out of scope

- Password/email editing (no Keycloak Account Console link, no Admin-API form) — later phase.
- Per-user/cross-device server-side theme persistence — later phase if needed.
- Any backend route changes.

## Risk / rollback

Frontend-only; revert is a clean file restore. Main risk is deleting `/settings/encryption`
without `/admin/encryption` — mitigated by the same-PR constraint above.
