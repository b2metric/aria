# Architecture

ARIA turns a natural-language question into governed SQL against the customer's own data
warehouse, then returns answer + chart + insight.

**Stack:** Next.js (frontend) · FastAPI (backend) · PostgreSQL (app DB) · Qdrant (vectors/memory) ·
Keycloak (OIDC/RBAC) · LiteLLM (model routing) · MinIO (artifacts) · Prefect (flows).

**Request pipeline (high level):** memory lookup → semantic-vault table match → SQL generation
(rule-based first, LLM fallback) → SQL guard + dry-run (EXPLAIN) + self-correction → execute on the
customer warehouse → chart → insight.

> Source-of-truth: `docs/technical-architecture.md`, `docs/frontend-architecture.md`,
> `docs/pipeline-flow.md`. Keep this page in sync via the `update-docs` / `update-codemaps` skills.
