# ARIA — AI-Driven Analytics Platform

> **Ask. Reason. Illuminate. Act.**  
> Natural-language analytics platform that combines semantic reasoning with vector search.

## Quick Start (Development)

```bash
# 1. Start infrastructure
docker compose -f docker-compose.dev.yml up -d

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e "..[dev]"
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend
npm install
npm run dev
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Backend   │────▶│  Postgres   │
│  Next.js    │     │  FastAPI    │     │  (no pgvec) │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                 ▼
   ┌──────────┐    ┌──────────┐      ┌──────────┐
   │  Qdrant  │    │   MinIO  │      │  Prefect │
   │  Vectors │    │ Objects  │      │  Flows   │
   └──────────┘    └──────────┘      └──────────┘
```

## Repository Structure

| Directory     | Purpose                              |
|---------------|--------------------------------------|
| `backend/`    | FastAPI application + tests + alembic |
| `frontend/`   | Next.js web application               |
| `infra/`      | Docker, Kubernetes, CI/CD configs      |
| `docs/`       | Architecture, API docs, runbooks       |

## Infrastructure (Dev)

| Service         | Port(s)     | Purpose                    |
|-----------------|-------------|----------------------------|
| PostgreSQL 16   | 5432        | Primary DB (Qdrant = vectors) |
| Redis 7         | 6379        | Cache / session store      |
| Keycloak 26     | 8080        | Auth / SSO                 |
| MinIO           | 9000, 9001  | S3 object storage          |
| Qdrant          | 6333, 6334  | Vector database            |
| Prefect 3       | 4200        | Workflow orchestration     |

## Environment

Copy `.env.example` to `.env` and adjust as needed. Default dev credentials are in `docker-compose.dev.yml`.

## License

Proprietary — B2Metric. All rights reserved.

## Agent & operations (Claude Code)

This repo uses **Claude Code**, run on your own LLMs via **claude-code-router → LiteLLM** (Gemini/DeepSeek, no Anthropic billing — see `CLAUDE.md`). Discipline = skills (obra/superpowers + everything-claude-code) + the mechanical gates below. Ground truth: **`CLAUDE.md`** + **`LOCKED-DECISIONS.md`** + **`AGENTS.md`** (read first). Authority docs: `docs/technical-architecture.md`, `docs/engineering-notes.md`, `docs/frontend-architecture.md`.

**Hard gates (code/CI — no "done" without them):**
- **Boot + login smoke** — `bash smoke/check.sh` (auto-reads `backend/.env`; health → Keycloak JWKS `/auth` → OIDC login → authenticated `/me`) + CI `smoke-boot` job.
- **Backend startup validation** — fails loudly on dummy/missing `LITELLM_API_KEY` or unreachable Keycloak JWKS (`backend/app/main.py` lifespan; bypass `ARIA_SKIP_STARTUP_CHECKS=1`).
- **Frontend** — `SafeIframe` rejects `srcDoc > 1 MB`; charts render from JSON via recharts (no inline Plotly HTML).
- **Repo-path guard** — `.githooks/pre-commit` (`git config core.hooksPath .githooks`).

**Dev ingress (Traefik, `*.aria.localhost`):** backend `api.aria.localhost` · Keycloak `auth.aria.localhost/auth` · LiteLLM `llm.aria.localhost` · Langfuse `langfuse.aria.localhost`. (Backend container does **not** publish host `:8000`.)

**LLM:** all calls via the LiteLLM proxy (`infra/llm/config.yaml`) — per-role aliases (`role-architect|backend-codegen|frontend-vision|…`), **reviewer ≠ author**, hybrid cloud + local **vLLM** (RTX 6000: thinking/vision/embed via `LOCAL_LLM_BASE`; see `infra/llm/RUNBOOK-local-serving.md`), per-role cost tracking.

**Stack:** Python/FastAPI (→ Go only for a measured hot path) · PostgreSQL 16 + alembic · Keycloak · Qdrant (vectors) · MinIO · **no Supabase**.
