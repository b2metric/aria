# Sprint 12: Reliability, Security, and Admin Dashboards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use engineering-core:subagent-driven-development or engineering-core:executing-plans to implement this plan task-by-task.

**Goal:** Address key gaps identified in the June 13th Gap Analysis (SEC-04, PIP-04, PIP-05, ADM-04, ADM-05, SEC-05). Improve system reliability with retries, enforce query rate limiting, encrypt database passwords, and provide a holistic Admin Dashboard.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Tenacity, Next.js, TailwindCSS.

---

### Task 1: Reliability - LLM and DB Retry Logic (PIP-04, PIP-05)
*Goal: Prevent transient failures from crashing the query pipeline.*

**Files:**
- Modify: `backend/app/query/pipeline.py`
- Modify: `backend/app/query/llm_sql.py`

- [ ] **Step 1: Add DB execution retries**
In `backend/app/query/pipeline.py`, import `tenacity` (`retry`, `stop_after_attempt`, `wait_exponential`). Wrap the body of `_execute_sql` with a retry decorator to retry on `sqlalchemy.exc.OperationalError` (e.g., connection drops, deadlocks) up to 3 times.
- [ ] **Step 2: Add LLM retries**
In `backend/app/query/llm_sql.py`, wrap the API call inside `_generate_sql` with a tenacity retry decorator, retrying on `httpx.HTTPStatusError` (only 5xx errors) and `httpx.RequestError` up to 3 times.

---

### Task 2: Security - Query Rate Limiting (SEC-04)
*Goal: Prevent abuse by rate-limiting the `/api/query` endpoint.*

**Files:**
- Modify: `backend/app/api/endpoints/query.py`
- Create: `backend/app/services/rate_limit.py`

- [ ] **Step 1: Create Rate Limiter Service**
Create `backend/app/services/rate_limit.py` that implements a Redis-based token bucket or fixed-window rate limiter. (e.g., limit to 20 queries per minute per user).
- [ ] **Step 2: Apply to Query Endpoint**
Inject the rate limit check into the `POST /api/query` endpoint in `backend/app/api/endpoints/query.py`. Return HTTP 429 Too Many Requests if the limit is exceeded.

---

### Task 3: Security - DB Password Encryption (SEC-05)
*Goal: Remove plaintext passwords from `customer_db_configs`.*

**Files:**
- Modify: `backend/app/services/crypto.py` (Create if missing)
- Modify: `backend/app/api/endpoints/admin/tenant.py` (or where DB config is saved)
- Modify: `backend/app/query/pipeline.py`

- [ ] **Step 1: Implement Crypto Utils**
Create or update `crypto.py` with Fernet symmetric encryption using a `SECRET_KEY` from environment variables.
- [ ] **Step 2: Encrypt on Save**
When saving `customer_db_configs`, encrypt the password before storing it in `encrypted_password`.
- [ ] **Step 3: Decrypt on Use**
In `backend/app/query/pipeline.py` (`_get_db_config`), decrypt the `encrypted_password` before using it to create the database engine. Remove the `# TODO: decrypt encrypted_password` comment.

---

### Task 4: Admin - Overview Dashboard UI (ADM-04)
*Goal: Replace the generic redirect with a real dashboard.*

**Files:**
- Create: `backend/app/api/endpoints/admin/metrics.py`
- Modify: `backend/app/api/endpoints/admin/__init__.py`
- Create/Modify: `frontend/src/app/admin/page.tsx`
- Modify: `frontend/src/app/admin/layout.tsx` (Remove the redirect)

- [ ] **Step 1: Backend Metrics API**
Create an endpoint `GET /api/admin/metrics` that returns summary statistics: total users, total queries today, total tokens used today, active teams.
- [ ] **Step 2: Frontend Dashboard**
Create `frontend/src/app/admin/page.tsx` to fetch and display these metrics in a grid of cards (e.g., Lucide React icons + numbers), and maybe a recent queries list. Update `layout.tsx` or `middleware.ts` to stop redirecting `/admin` to `/admin/memory`.

---

### Task 5: Admin - System Health Dashboard (ADM-05)
*Goal: View backend dependencies health from the UI.*

**Files:**
- Modify: `backend/app/api/endpoints/health.py`
- Create: `frontend/src/app/admin/health/page.tsx`
- Modify: `frontend/src/app/admin/layout.tsx`

- [ ] **Step 1: Detailed Health API**
Enhance `GET /health` or add `GET /api/admin/health` to check connections to: PostgreSQL, Redis, Qdrant, MinIO, LiteLLM, Keycloak, and return their individual status.
- [ ] **Step 2: Health Dashboard UI**
Create a new admin page at `/admin/health` that displays the status of all these components with green/red status indicators. Add a link to it in the admin sidebar.

---

### Task 6: CMEK — Customer-Managed Encryption Keys *(retroactively documented)*
*Goal: Per-customer envelope encryption for secrets at rest, extending Task 3's Fernet password encryption. Shipped 2026-06-19 (commit `371d85d` "feat(cmek)") but not tracked in a sprint at the time — recorded here under Sprint 12's Security theme.*

**Files:**
- `backend/app/services/crypto.py` (AppKEKProvider, per-customer DEK, envelope encrypt/decrypt, 5-min DEK cache)
- `backend/app/api/endpoints/admin/encryption.py` (GET/PATCH `/api/admin/encryption`)
- `backend/app/models/database.py` (CustomerKeyConfig)
- `frontend/src/app/settings/encryption/page.tsx` (provider + key-URI config UI)

- [x] **Shipped:** Per-customer Data Encryption Keys (DEK) wrapped by an app-level KEK (Fernet via `ARIA_SECRET_KEY`); provider framework (`app`/`aws`/`gcp`/`azure`) + a settings page to choose provider and key URI. **(RESOLVED — retroactive)** — *external AWS/GCP/Azure KMS providers are stub-only and the UI lacks rotation/status/audit; carried forward in Sprint 15.*

---

### Task 7: BYOK — Customer LLM provider configuration *(retroactively documented)*
*Goal: Let each customer bring their own LLM endpoint/key instead of the shared LiteLLM proxy. Shipped 2026-06-17 (commit `e43c878` "BYOK phase 1") but not tracked in a sprint — recorded here under the Security/Admin-config theme (credentials are encrypted at rest).*

**Files:**
- `backend/app/api/endpoints/admin/llm_config.py`, `backend/app/services/llm_resolver.py`
- `backend/app/models/database.py` (CustomerLLMConfig)
- `frontend/src/app/admin/llm-config/page.tsx`

- [x] **Shipped:** Per-customer LLM provider config (OpenAI/Azure/Anthropic/Gemini/LiteLLM) with encrypted credentials; `resolve_llm()` uses the customer config and falls back to the platform LiteLLM proxy. **(RESOLVED — retroactive)**
