# Durable, Resumable Chat Streaming — Design

**Date:** 2026-06-28
**Branch:** feat/sprint16-hygiene
**Status:** Approved (design); pending spec review → implementation plan

## Problem

When a user submits a chat question and refreshes the page (F5) while ARIA is
still generating SQL, the saved conversation shows only the user's message; the
assistant reply is empty.

Root cause (verified in code):

- The user message is persisted to Redis immediately
  ([pipeline.py:1885-1886](../../../backend/app/query/pipeline.py)).
- The assistant message is persisted **only after the whole pipeline completes**
  ([pipeline.py:2339-2350](../../../backend/app/query/pipeline.py)). The
  intermediate SSE events (`status`, `sql`, `chart`) are streamed live but never
  persisted incrementally.
- On client disconnect the SSE response generator is cancelled
  ([query.py:145-147](../../../backend/app/api/query.py)); the pipeline coroutine
  dies. The in-flight assistant turn is never written.
- On reload the frontend only does `GET /api/conversations/{id}`
  ([chat/page.tsx:208-210](../../../frontend/src/app/chat/page.tsx)), which
  returns whatever is persisted — just the user message. There is no resume.

## Goal

A page refresh, tab close + reopen, or network blip during generation must not
lose the in-flight answer. The user reconnects and sees the turn complete live.
Generation must also survive a backend deploy/restart of the producing process.

## Constraints (discovered)

- **Prod runs 4 Gunicorn workers** (`GUNICORN_WORKERS: 4`,
  [docker-compose.prod.yml](../../../docker-compose.prod.yml)) with
  `worker_class = "uvicorn.workers.UvicornWorker"`
  ([infra/gunicorn.conf.py:15](../../../infra/gunicorn.conf.py)). A detached
  `asyncio.create_task` survives past the HTTP request on that worker's event
  loop, but a **different worker** may serve the resume request — so the event
  transport must be **cross-process**.
- **Prefect 3.7.4 is the house orchestrator**: declared in `pyproject.toml`
  (`prefect>=3.2,<4`), a `prefect-server` + `prefect-db` run in
  `docker-compose.dev.yml`, and `artifact.py:62` reserves an unused
  `prefect_flow_run_id` column. But there are **zero flows/tasks/deployments** in
  app code, and Prefect is **absent from prod compose**. It is scaffolded but
  inert. Celery/arq are NOT used and will NOT be introduced.
- Project invariants (AGENTS.md): one active run per conversation; SQL-visibility,
  row limits, token quotas enforced inside generation regardless of runner.

## Chosen Approach — Hybrid (asyncio fast-path + Prefect reconcile)

Live SSE feed always flows through **Redis Streams**. Prefect is the durability
backstop, not the live transport.

### Core principle — source of truth is a Redis Stream

Each run owns a stream `aria:run:{cid}`. The producer `XADD`s every pipeline
event; every SSE connection (initial POST and resume) `XREAD`-tails it. A
connection is just a reader, decoupled from production.

### Execution model

**Fast path (every query):**
1. `POST /api/query` generates a `run_id`, persists the user message (existing
   behavior), creates a Redis run record + acquires a lock (`SETNX
   aria:run_lock:{cid}` with a fencing token), then starts generation as a
   **detached asyncio task** (held in a module-level reference set so it is not
   GC'd; not awaited by the response).
2. The task runs the `process_query` **core generator** but writes events via
   `run_store` (`XADD`) instead of yielding to the HTTP response. It updates a
   **heartbeat** periodically. On completion it appends the terminal event,
   persists the assistant message, and releases the lock.
3. The POST response is now a **tailer**: it `XREAD`s `aria:run:{cid}` from id
   `0` and forwards events to the client until the terminal event. If the client
   disconnects, the tailer stops; the **producer keeps running**.

**Resume on reload:**
4. Frontend loads with `?cid=`, calls `GET /api/query/{cid}/status`.
   - `active` → open resume SSE `GET /api/query/{cid}/stream`: replay buffered
     events from id `0`, then live-tail until terminal. The in-flight turn
     completes on screen.
   - `done` / no run → assistant message already persisted; normal history
     render suffices.

**Prefect reconcile (deploy/restart durability):**
5. If the producing worker dies (deploy/crash), the run record stays `running`
   but its heartbeat goes stale. A scheduled Prefect flow `reconcile_stalled_runs`
   (prod Prefect worker, ~60s interval) scans `aria:run:*` for `running` runs with
   an expired heartbeat lease, **reclaims the lock via fencing token**, and
   **re-runs generation idempotently** for that cid (reusing the persisted user
   question, NOT re-appending it). The `prefect_flow_run_id` is recorded.

### Components (isolated units)

| Unit | Responsibility | Depends on |
|------|----------------|-----------|
| **`backend/app/query/run_store.py`** (new) | Durable run event log: create/lock run, `XADD` event, tail (`XREAD`), status, heartbeat, fencing-token reclaim, stream TTL/trim | Redis |
| **`backend/app/query/pipeline.py`** (modify) | Split `process_query` into reusable **core generator** + driver; add `resume`/`skip_user_message` flag so the user message is appended only on the initial POST; emit events into `run_store` | run_store |
| **`backend/app/api/query.py`** (modify) | POST spawns detached producer + returns tailer SSE; new `GET /{cid}/stream` (resume) and `GET /{cid}/status` | run_store, pipeline |
| **`backend/app/flows/reconcile.py`** (new, + `__init__.py`) | Prefect flow scanning stalled runs + idempotent re-run | run_store, pipeline, Prefect |
| **`docker-compose.prod.yml`** (modify) | Add `prefect-server` + `prefect-db` + **`prefect-worker`** service & work-pool; `PREFECT_API_URL` wiring. Add worker to dev too | — |
| **`frontend/.../chat/page.tsx` + `lib/api.ts`** (modify) | On load check run status; open resume SSE for active runs; render live | resume/status endpoints |

### Data flow

```
POST /query ──> persist user msg ──> create run + lock ──> spawn detached task
                                                              │
                  (task) process_query core ── XADD events ──> aria:run:{cid} (Redis Stream)
                                                              │            ▲
   response tailer ── XREAD from 0 ──> client (SSE) ──────────┘            │
                                                                           │
   [refresh] GET /{cid}/status=active ──> GET /{cid}/stream ── XREAD from 0 (replay+live)
                                                                           │
   [worker dies] heartbeat stale ──> Prefect reconcile_stalled_runs ── reclaim lock ──> re-run ──┘
```

## Invariants preserved

- **One active run per conversation** via `aria:run_lock:{cid}`.
- **No duplicate user message** on resume/reconcile (the `resume` flag gates
  [pipeline.py:1885](../../../backend/app/query/pipeline.py)).
- **SQL-visibility / row-limit / token-quota** enforced inside the core
  generator, independent of who runs it (POST task vs Prefect).

## Error handling

- Producer exception → terminal `error` event + run status `error`, lock
  released. Resume shows the error; no infinite "generating".
- Reconcile runs only if it can reclaim the lock (fencing token) → a live-but-slow
  producer is never duplicated.
- Run streams expire ~1h after the terminal event (replay only needed while
  active/recent); conversation history persistence (30-day TTL) is unchanged.

## Testing (TDD — tests first)

- `run_store` unit tests: `XADD`/tail ordering, lock acquire/contend, fencing
  reclaim, heartbeat staleness, TTL/trim.
- pipeline resume: user message NOT re-appended when `resume=True`.
- reconcile idempotency: stale run re-runs once; live run not duplicated.
- resume + status endpoints: integration (active replays buffered events; done
  returns terminal; unknown 404).
- frontend: load with active run opens resume SSE and renders the completing turn.

## Risks / notes

- Detached task must be kept referenced (module-level set) to avoid GC.
- `GUNICORN_TIMEOUT=120` is a worker heartbeat; await-driven async generation does
  not block the loop, so it should not trip — verify under load.
- **Adding Prefect to prod is a LOCKED-DECISIONS-level infra change** (new
  services). Flagged explicitly; confirm before the compose change ships.
- Magic numbers (heartbeat interval, staleness threshold, reconcile cadence,
  stream TTL) become named constants.

## Out of scope (YAGNI)

- Multi-turn concurrent generation within one conversation.
- Token-by-token LLM streaming (current pipeline emits stage events, not tokens).
- Cross-region / multi-Redis durability.
