# Sprint 13: UX Insights, Vault Automation, and Advanced Pipeline Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use engineering-core:subagent-driven-development or engineering-core:executing-plans to implement this plan task-by-task.

**Goal:** Implement the missing "Insight Generation" (Summary + Suggestions) stage in the query pipeline, automate Vault schema synchronization, and introduce advanced query safeguards (EXPLAIN dry-runs and row limit enforcement).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, LiteLLM, Prefect (Optional for background jobs).

---

### Task 1: Insight Generation (Summary & Suggestions)
*Goal: Fulfill the architectural requirement (Stage 6) to provide an executive summary and follow-up questions after a successful query.*

**Files:**
- Modify: `backend/app/query/pipeline.py`
- Modify: `backend/app/query/llm_sql.py` (or create `llm_insight.py`)
- Modify: `frontend/src/app/chat/page.tsx`

- [ ] **Step 1: Backend Insight Generator**
Create an LLM call (`generate_insight_and_suggestions`) that takes the original question, the generated SQL, and the JSON result data (truncated to max 10 rows for context). It should prompt the LLM to return a JSON containing a brief `summary` (e.g., "Revenue increased 15%...") and an array of 3 `suggestions` (follow-up questions).
- [ ] **Step 2: Inject into Pipeline**
In `pipeline.py`, after `RENDERING_CHART` but before `COMPLETE`, invoke the insight generator. Yield an SSE event `event: insight` with `data: {"summary": "...", "suggestions": [...]}`.
- [ ] **Step 3: Frontend Rendering**
Update the SSE parser in the frontend to catch `insight` events and display the summary box and clickable suggestion chips below the chart.

---

### Task 2: Dry-Run (EXPLAIN) & Per-Tenant Row Limits
*Goal: Prevent massive queries from locking up the system or the browser.*

**Files:**
- Modify: `backend/app/models/organization.py` (Add `max_row_limit` to Customer or a new model)
- Modify: `backend/app/api/endpoints/admin/tenant.py` (Save row limit to DB)
- Modify: `backend/app/query/pipeline.py`

- [ ] **Step 1: Save Row Limit**
Add a DB column for `max_row_limit` (either on `Customer` or `CustomerDBConfig`). Update the Tenant Config admin API to persist and read this value instead of `DEFAULT_MAX_ROW_LIMIT`.
- [ ] **Step 2: EXPLAIN Validation**
In `pipeline.py`, before executing the main SQL, run an `EXPLAIN` (or database-specific equivalent) if possible, or append a hard `LIMIT` matching the `max_row_limit` + 1. If the result set hits the limit, either truncate it and warn the user, or (future) route it to a background Prefect job.

---

### Task 3: Vault Auto-Sync & Manual Trigger
*Goal: Keep ARIA's markdown vault schemas in sync with the live customer database.*

**Files:**
- Create: `backend/app/services/vault_sync.py`
- Modify: `backend/app/api/endpoints/admin/schema.py`

- [x] **Step 1: DB Introspection Engine**
Write a service that connects to the customer's DB via `CustomerDBConfig`, reads the `information_schema` (tables, columns, types), and compares it against the existing `.md` files in `docs/vaults/{workspace}/tables/`. **(RESOLVED)**
- [x] **Step 2: Markdown Generator**
If a table is new or columns have changed, update/generate the `.md` file, preserving existing descriptions and insights where possible. **(RESOLVED)**
- [x] **Step 3: Database Connection UI Binding**
Ensure the Admin panel has a proper place to input and validate the Customer DB Credentials (already added via Tenant Config, but make sure the sync service correctly pulls the encrypted password and tests the connection before sync). **(RESOLVED)**
- [x] **Step 4: API & UI Trigger**
Add a `POST /api/workspaces/vault/sync` endpoint. Update the frontend `/admin/schema` page with a "Re-Sync Now" button that calls this API. **(RESOLVED)**

---

### Task 4: Advanced Pipeline Fallbacks & Memory Decay
*Goal: Improve robustness and clean up stale memory.*

**Files:**
- Modify: `backend/app/query/pipeline.py`
- Modify: `backend/app/memory/service.py`

- [x] **Step 1: Secondary LLM Fallback**
If the LLM generates invalid SQL and `execute_query` throws a Syntax Error, catch the error, pass the error message back to the LLM ("You made a syntax error: X. Fix the SQL"), and retry execution once. **(RESOLVED)**
- [x] **Step 2: Memory Decay**
Implement a cleanup job or filtering logic that ignores or degrades the relevance of User Preferences older than 6 months. **(RESOLVED)**

---

### Task 6: Real Dashboard Integration
*Goal: Replace the hardcoded `getMockDashboardData()` on the landing dashboard with real metrics.*

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Modify: `backend/app/api/endpoints/admin/metrics.py` (or create a user-specific `/api/dashboard`)

- [x] **Step 1: Backend User Dashboard API**
Create an endpoint (e.g. `GET /api/dashboard`) that returns statistics for the specific user/team (e.g., their total queries, charts generated, recently queried tables) rather than admin-wide metrics. **(RESOLVED)**
- [x] **Step 2: Frontend Data Binding**
Update `frontend/src/app/page.tsx` to call this new endpoint. Remove `getMockDashboardData()`. Bind the returned analytics (Stats and ChartData) to the existing UI components. **(RESOLVED)**
*Goal: Fix the issue where deleting a conversation via UI returns 204 but reappears upon refresh.*

**Files:**
- Modify: `backend/app/query/conversation.py`

- [ ] **Step 1: Check Redis ZREM Logic**
Analyze `delete_conversation`. It deletes the individual key but calls `zrem(list_key, conversation_id)`. Check if `list_conversations` reads from this exact sorted set. Ensure `ZADD` and `ZREM` member strings match exactly. **(RESOLVED)**
- [ ] **Step 2: Ensure Complete Cleanup**
When testing, if `redis.zrem(list_key, conversation_id)` returns 0, it means the ID wasn't in the sorted set. Updated `delete_conversation` to return `deleted > 0 or zrem_res > 0` and properly sweep the conversation mapping without falsely blocking 204. **(RESOLVED)**