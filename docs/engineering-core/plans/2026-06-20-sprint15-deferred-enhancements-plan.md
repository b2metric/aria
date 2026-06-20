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

- [x] **Step 1: Backend metadata filters** — added a `success: bool | None` query param to `GET /api/admin/audit-logs`, translated into a JSONB predicate (`details->>'success'`) in `AuditService.get_logs`/`count_logs` (still scoped by `customer_id`). Verified live: all=80, `success=true`=55, `success=false`=14. **(RESOLVED)**
- [x] **Step 2: Frontend filter controls** — the audit-log page's status select now sends `&success=true/false` to the backend (re-fetches on change) instead of slicing client-side. `action` was already server-side. **(RESOLVED)**

---

### Task 3: Team Conventions approval workflow expansion
*Goal: Team memory CRUD exists, but the human approval workflow ("managed by admin/team_lead") is only partially live (`expansion 🔜`).*

**Files:**
- Modify: `backend/app/api/endpoints/admin/` (team-memory endpoints)
- Modify: `frontend/src/app/admin/team-memory/page.tsx`

- [x] **Step 1: Approval states** — new team conventions now persist with metadata `status="pending"`; `MemoryService.lookup` gates `team_conventions` to `status == "approved"` (legacy/no-status entries treated as approved for back-compat). `set_memory_status(memory_id, status, …)` flips the state. Because Mem0 2.x single-entry `update()`/`get()` by id are unreliable for these points, status changes are applied via `get_all` → `delete` → re-`add` (`infer=False`). **(RESOLVED)**
- [x] **Step 2: Admin/team_lead review UI** — `PATCH /api/admin/team-memory/{id}/status` (RBAC: `can_admin` OR `can_manage_team`; validates `approved|rejected|pending`). Team-memory admin page shows a status badge (green/amber/red) + hover Approve/Reject actions. Verified live (`stc-kuwait` workspace): create→`pending`, approve→`200`+single entry now `approved`, delete→`200`. 3 unit tests in `backend/tests/test_memory_approval.py`. **(RESOLVED)**

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

---

### Task 6: CMEK — real external KMS + key-management UI
*Goal: CMEK shipped as app-KEK envelope encryption + a provider-selection page (Sprint 12 Task 6, retroactively documented), but the external KMS providers are stubbed and the UI has no lifecycle management. Close the gap.*

**Files:**
- Modify: `backend/app/services/crypto.py` (AWS/GCP/Azure providers — currently stub)
- Modify: `backend/app/api/endpoints/admin/encryption.py`
- Modify: `frontend/src/app/settings/encryption/page.tsx`

- [ ] **Step 1: Real KMS providers (backend)**
Implement the `aws` / `gcp` / `azure` providers in `crypto.py` so that when a customer's provider != `app`, the per-customer DEK is wrapped/unwrapped via the external KMS (boto3 KMS / google-cloud-kms / azure-keyvault-keys) using the configured key URI/ARN. Validate the key URI on PATCH (fail fast if the key is unreachable). Keep `app` as the default fallback.
- [ ] **Step 2: Key lifecycle UI (frontend)**
Extend `/settings/encryption` beyond provider+URI: show **key status/health** (is the configured KMS key reachable?), a **rotate key** action (re-wrap the DEK under a new key version), and surface a **CMEK config-change audit trail** (who changed provider/key, when) via the existing audit log.
- [ ] **Step 3: Tests**
Unit-test the provider selection + DEK wrap/unwrap round-trip (mock the external KMS SDKs); assert `app` fallback still works.

> Note: the existing config page (provider dropdown + key URI + PATCH) already exists — this task is the *management layer* (real KMS wiring + rotation/status/audit), not a from-scratch build.
