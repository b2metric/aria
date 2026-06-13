# Sprint 10: Token Quota Enforcement & Tracking - Design Doc

## Goal
Implement Token Management to control LLM costs and prevent abuse. Based on the gap analysis:
- TOK-01 & TOK-02: Record token consumption after LLM calls (`TokenTracker` service).
- TOK-03: Enforce token quotas before queries based on `LOCKED-DECISIONS.md` ("daily token cap per user/team/session").

## Architecture & Integration

- **Backend Context**: The query pipeline (`backend/app/query/pipeline.py`) calls `backend/app/query/llm_sql.py` which interacts with the LiteLLM proxy.
- **Models**: `TokenQuota` and `TokenUsageDaily` already exist in `backend/app/models/token.py`.
- **Database**: PostgreSQL handles persistence. Redis handles atomic rate limiting/quota checking.

### Component 1: `TokenTracker` Service

Create `backend/app/services/token.py` (or similar, depending on existing structure).

**Functions**:
1. `check_quota(user_id, team_id, session_id) -> bool`:
   - Checks Redis counters for the current day.
   - Compares against `TokenQuota` values from Postgres (or cached values).
   - Raises an exception (or returns False) if any limit is exceeded.
2. `record_usage(user_id, team_id, session_id, prompt_tokens, completion_tokens, model_name)`:
   - Increments Redis counters.
   - Asynchronously (or periodically via a background task/middleware) updates the `token_usage_daily` table in Postgres for persistence.

### Component 2: LiteLLM Response Parsing

Modify `backend/app/query/llm_sql.py` (or wherever the LLM API is called):
- Extract the `usage` object from the LiteLLM completion response.
- `usage.prompt_tokens` and `usage.completion_tokens`.
- Pass these metrics to `TokenTracker.record_usage()`.

### Component 3: Query Pipeline Integration

Modify `backend/app/query/pipeline.py` (specifically `process_query`):
- **Pre-execution**: Call `TokenTracker.check_quota()` before starting any heavy processing (before Vault matching or LLM calls).
- **Post-execution (implicit)**: The LLM call itself will trigger `record_usage()`.

## Missing Pieces / Dependencies
- **Redis Connection**: Ensure `backend/app/core/redis.py` (or similar) is set up and accessible for atomic increment operations (`INCRBY`).
- **Quota Defaulting**: If a user/team has no specific `TokenQuota` entry, fallback to tenant-level defaults (`customer_db_configs.daily_token_limit` or global env vars).

## Scope for Sprint 10

1. **Backend Service**: Create `TokenTracker` using Redis for fast counting and Postgres for durable records.
2. **LLM Integration**: Parse token usage from LiteLLM.
3. **Pipeline Guard**: Add pre-query quota enforcement.
4. **Tests**: Unit tests for the service and integration tests for the pipeline blocking over-quota requests.
