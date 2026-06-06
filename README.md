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
│  Next.js    │     │  FastAPI    │     │  + pgvector │
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
| PostgreSQL 16   | 5432        | Primary database + vectors |
| Redis 7         | 6379        | Cache / session store      |
| Keycloak 26     | 8080        | Auth / SSO                 |
| MinIO           | 9000, 9001  | S3 object storage          |
| Qdrant          | 6333, 6334  | Vector database            |
| Prefect 3       | 4200        | Workflow orchestration     |

## Environment

Copy `.env.example` to `.env` and adjust as needed. Default dev credentials are in `docker-compose.dev.yml`.

## License

Proprietary — B2Metric. All rights reserved.
