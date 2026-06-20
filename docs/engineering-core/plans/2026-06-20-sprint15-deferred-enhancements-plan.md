# Sprint 15: Deferred Enhancements — Chart Export, Audit Filters, Memory Smarts

> **For agentic workers:** REQUIRED SUB-SKILL: Use engineering-core:subagent-driven-development or engineering-core:executing-plans to implement this plan task-by-task.

**Goal:** Pick up the genuinely-open, near-term enhancements that were previously parked in `docs/future-work-summary.md` (now retired) and turn them into concrete, gated tasks. Near-term product/engineering polish — *not* the post-MVP roadmap (see "Out of scope" below).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, LiteLLM, Plotly + Kaleido, MinIO, Next.js 16.

> **Out of scope (long-term / post-MVP — tracked in `LOCKED-DECISIONS.md` & `AGENTS.md`, NOT scheduled here):** ClickHouse (Phase 3), Teams/PowerBI integration, Go hot-path microservices, Kubernetes/Terraform IaC, vLLM local-GPU routing.

---

### Task 1: Kaleido PNG chart export
*Goal: The pipeline exports CSV to MinIO; the PNG export (`chart_url`) is wired in code but never produced. Finish it now that `kaleido==0.2.1` is pinned for linux-x86_64.*

**Files:**
- Modify: `agents/chart_renderer.py` (`render_png`)
- Modify: `agents/chart_builder.py` / `backend/app/query/pipeline.py` (upload + `chart_url`)

- [x] **Step 1: Generate the PNG**
`render_png` already builds the Plotly figure and calls `fig.to_image(engine="kaleido")` with graceful degradation. The real blocker was the dependency: bumped `kaleido` `0.2.1` (linux-x86_64-only, not Plotly-6-native) → **`>=1,<2`** (cross-platform wheels incl. macOS ARM64). Verified locally — `render_png` now emits a real 83 KB PNG. **(RESOLVED)**
- [x] **Step 2: Upload + surface `chart_url`**
Already implemented: `pipeline.py` uploads `png_bytes` to MinIO (`chart_{conversation_id}.png`) and sets `chart_url` (public/presigned) in the chart payload. Added a `render_png` contract test. **(RESOLVED)**

> **Runtime note (infra follow-up):** Kaleido 1.x needs a Chrome/Chromium at render time. Where it is absent (e.g. a backend container without a browser) `render_png` degrades to "no PNG" — no crash. To actually produce PNGs in prod, provision Chrome in the backend image (or call `kaleido.get_chrome_sync()` at build).

---

### Task 2: Audit Log UI — filter by JSON metadata
*Goal: `/admin/audit-log` lists events, but the nested `details` JSON (e.g. `success`, `sql`) can only be filtered client-side. Push filtering into the backend query.*

**Files:**
- Modify: `backend/app/api/endpoints/admin/audit.py`
- Modify: `frontend/src/app/admin/audit-log/page.tsx`

- [ ] **Step 1: Backend metadata filters**
Add query params (e.g. `success`, `resource_type`, free-text on `details`) to the audit-logs endpoint and translate them into JSONB/`details` predicates in the SQLAlchemy query (scoped by `customer_id`).
- [ ] **Step 2: Frontend filter controls**
Wire the existing status/action selects (and a new "outcome" filter) to the new query params so filtering is server-side rather than the current client-side slice.

---

### Task 3: Team Conventions approval workflow expansion
*Goal: Team memory CRUD exists, but the human approval workflow ("managed by admin/team_lead") is only partially live (`expansion 🔜`).*

**Files:**
- Modify: `backend/app/api/endpoints/admin/` (team-memory endpoints)
- Modify: `frontend/src/app/admin/team-memory/page.tsx`

- [ ] **Step 1: Approval states**
Add a `status` (e.g. `pending` / `approved` / `rejected`) to team conventions and gate which conventions feed the LLM context to `approved` only.
- [ ] **Step 2: Admin/team_lead review UI**
Surface pending conventions in the team-memory admin page with approve/reject actions (RBAC: admin + team_lead), per the invariant in `AGENTS.md`.

---

### Task 4: Memory proactivity — preferences influence SQL generation
*Goal: Stored `user_preferences` (e.g. "always group by month") are recalled but not yet proactively injected into SQL generation before the user re-asks.*

**Files:**
- Modify: `backend/app/memory/service.py`
- Modify: `backend/app/query/llm_sql.py`

- [ ] **Step 1: Surface preferences to the SQL prompt**
In the SQL-generation grounding step, pull relevant `user_preferences` from the memory service and add them to the prompt context (alongside the existing column/enum grounding).
- [ ] **Step 2: Verify non-regression**
Confirm with a couple of NL→SQL cases that preferences nudge output (e.g. monthly bucketing) without breaking the scalar-vs-trend rules from the earlier SQL-grounding fix.

---

### Task 5: Memory decay tuning
*Goal: `user_preferences` use a hard 180-day decay (delete). Move toward relevance-scoring decay instead of hard deletion.*

**Files:**
- Modify: `backend/app/memory/service.py`

- [ ] **Step 1: Relevance score over hard-delete**
Replace (or augment) the 180-day hard delete with a recency/usage-weighted relevance score; rank recall by score and only purge long-cold entries.
- [ ] **Step 2: Tuning + tests**
Add unit coverage for the scoring/decay function and document the chosen half-life / thresholds.
