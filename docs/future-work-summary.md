# ARIA — Future Work & Backlog Summary

**Date:** 2026-06-16

This document compiles all planned features, upcoming phases, "TODO"s, and deferred technical decisions found across the ARIA documentation (`.md` files).

---

## 1. Pipeline & Execution (Next / Future Sprints)
Features marked as `🔜` (Planned) in `docs/business/chat-flow-scenarios.md` and related plans:
- **EXPLAIN Dry-Run & Row Estimation:** Before executing a query on the customer DB, run an `EXPLAIN` or equivalent to estimate row count and cost. Prevent queries from locking the database.
- **Large Result Handling (Background Jobs):** If a query exceeds the `max_row_limit` (e.g., 10,000+ rows):
  - Do not truncate or block silently.
  - Route the execution to a **Prefect background job**.
  - Provide a time-limited **MinIO download link** (e.g., valid for 3 days) to the user instead of rendering inline.
- **Kaleido Integration (PNG Exports):** The pipeline currently exports CSVs to MinIO. The PNG export (`chart_url`) is prepared in the code but awaits the `kaleido` package dependency resolution for ARM64/Linux environments to actually generate images from Plotly/Recharts.

## 2. Infrastructure & Scalability (Phase 3 & Post-MVP)
Decisions deferred to later phases as per `LOCKED-DECISIONS.md`, `AGENTS.md`, and `technical-architecture.md`:
- **ClickHouse Integration:** Slated for **Phase 3** only. Will act as a high-performance analytical datastore layer once volume demands it.
- **Teams & PowerBI Integration:** Enterprise integrations for Microsoft ecosystem are deferred to **Post-MVP**.
- **Go Microservices:** The hot-path rewrite using Golang was removed during MVP to maintain velocity. Will only be revisited for measured hot-paths post-MVP.
- **Kubernetes, Terraform, CI/CD:** Formalized infrastructure-as-code and K8s deployments are marked as `(future)` in `infra/README.md`.
- **vLLM (Local GPU):** Optional routing for local open-source models via vLLM on RTX 6000 is wired conceptually but not the default.

## 3. UI & Administrative Enhancements
- **User Management UI (`/admin/users`):** The backend endpoints exist, but the frontend requires a fully-fledged user management page to view/manage platform users, their roles, teams, and workspace assignments.
- **Token Usage Dashboard (`/admin/token-usage`):** An interface to visualize the newly implemented `token_usage_daily` table, showing consumption analytics by user, team, model, and time period.
- **Audit Log UI (Enhancements):** While the `/admin/audit-log` viewer was built, deeper integration or filtering by specific JSON metadata may be expanded.
- **Team Conventions Workflow:** Currently, team memory is updated programmatically or via backend. The documentation notes: *"Team memory definitions are managed by admin/team_lead (human approval; admin CRUD panel). Approval workflow is partially live, expansion 🔜."*

## 4. LLM Memory & Smarts
- **Memory Proactivity:** `gap-analysis-2026-06-13.md` notes that user preference extraction (e.g., "I always want data grouped by month") is currently basic. Future updates aim to make stored preferences proactively influence the heuristic and LLM SQL generators before explicit prompting is required.
- **Memory Decay (Implemented but needs tuning):** A 180-day decay was added to `user_preferences`. Future iterations may introduce relevance scoring decay rather than hard deletion.

---
*Note: This list is generated from existing Markdown files. For the active sprint board or immediate bug fixes, consult the engineering plans folder.*