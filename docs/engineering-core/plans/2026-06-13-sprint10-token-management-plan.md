# Sprint 10: Token Quota Enforcement & Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use engineering-core:subagent-driven-development (recommended) or engineering-core:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Token Management (Tracking and Quota Enforcement) across the backend.

**Architecture:** Create `TokenService` using Redis for fast atomic counting and PostgreSQL for persistence. Inject this service into the query pipeline to block over-quota requests and record usage after LLM calls.

**Tech Stack:** Python 3.12, FastAPI, Redis (via `redis-py` async), SQLAlchemy, LiteLLM.

---

### Task 1: Create Token Service

**Files:**
- Create: `backend/app/services/token.py`
- Modify: `backend/app/services/__init__.py`

- [ ] **Step 1: Implement TokenService Logic**

Create `backend/app/services/token.py`:
```python
import logging
from typing import Optional
import uuid
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from backend.app.models.token import TokenUsageDaily, TokenQuota
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class TokenService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis

    def _get_redis_key(self, level: str, target_id: str, date_str: str) -> str:
        """Generate a Redis key like: aria:tokens:user:user_uuid:2026-06-13"""
        return f"{settings.PROJECT_NAME.lower()}:tokens:{level}:{target_id}:{date_str}"

    async def get_quotas(self, workspace_id: str, user_id: str, team_id: str) -> dict:
        """Fetch quotas for user, team, and workspace. Fallback to defaults."""
        quotas = {
            "session": getattr(settings, "DEFAULT_SESSION_TOKEN_LIMIT", 100000),
            "user": getattr(settings, "DEFAULT_USER_TOKEN_LIMIT", 500000),
            "team": getattr(settings, "DEFAULT_TEAM_TOKEN_LIMIT", 2000000),
        }
        
        # Fetch actual DB quotas if they exist
        result = await self.db.execute(
            select(TokenQuota).where(
                (TokenQuota.workspace_id == workspace_id) &
                ((TokenQuota.target_id == user_id) | (TokenQuota.target_id == team_id) | (TokenQuota.level == "workspace"))
            )
        )
        db_quotas = result.scalars().all()
        for q in db_quotas:
            quotas[q.level] = q.daily_limit
            
        return quotas

    async def check_quota(self, workspace_id: str, user_id: str, team_id: str, session_id: str) -> bool:
        """Check if current usage exceeds limits. Returns True if allowed, False if blocked."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Get limits
        quotas = await self.get_quotas(workspace_id, user_id, team_id)
        
        # Get current usage from Redis
        user_key = self._get_redis_key("user", user_id, date_str)
        team_key = self._get_redis_key("team", team_id, date_str)
        session_key = self._get_redis_key("session", session_id, date_str)
        
        # Pipeline multiple GETs
        pipe = self.redis.pipeline()
        pipe.get(user_key)
        pipe.get(team_key)
        pipe.get(session_key)
        results = await pipe.execute()
        
        user_used = int(results[0]) if results[0] else 0
        team_used = int(results[1]) if results[1] else 0
        session_used = int(results[2]) if results[2] else 0
        
        # Check
        if user_used >= quotas["user"]:
            logger.warning(f"User {user_id} exceeded daily token limit ({quotas['user']})")
            return False
        if team_used >= quotas["team"]:
            logger.warning(f"Team {team_id} exceeded daily token limit ({quotas['team']})")
            return False
        if session_used >= quotas["session"]:
            logger.warning(f"Session {session_id} exceeded token limit ({quotas['session']})")
            return False
            
        return True

    async def record_usage(
        self, 
        workspace_id: str, 
        user_id: str, 
        team_id: str, 
        session_id: str, 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int
    ) -> None:
        """Increment Redis counters and queue DB persistence."""
        total_tokens = prompt_tokens + completion_tokens
        if total_tokens <= 0:
            return
            
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        date_obj = datetime.now(timezone.utc).date()
        
        user_key = self._get_redis_key("user", user_id, date_str)
        team_key = self._get_redis_key("team", team_id, date_str)
        session_key = self._get_redis_key("session", session_id, date_str)
        
        # 1. Update Redis (fast atomic increment, set 48h expiry if new)
        pipe = self.redis.pipeline()
        for key in [user_key, team_key, session_key]:
            pipe.incrby(key, total_tokens)
            pipe.expire(key, 172800, nx=True) # 48 hours
        await pipe.execute()
        
        # 2. Persist to Postgres (Upsert logic)
        try:
            # We record at the user level for simplicity here, can expand to team/workspace aggregation later.
            stmt = insert(TokenUsageDaily).values(
                workspace_id=workspace_id,
                target_id=user_id,
                level="user",
                date=date_obj,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                model_costs={model: total_tokens} # Simplified
            )
            
            # On conflict, update totals
            stmt = stmt.on_conflict_do_update(
                index_elements=['workspace_id', 'target_id', 'level', 'date'],
                set_={
                    'prompt_tokens': TokenUsageDaily.prompt_tokens + prompt_tokens,
                    'completion_tokens': TokenUsageDaily.completion_tokens + completion_tokens,
                    'total_tokens': TokenUsageDaily.total_tokens + total_tokens,
                    'updated_at': datetime.now(timezone.utc)
                }
            )
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to persist token usage to DB: {e}")
            await self.db.rollback()
```

- [ ] **Step 2: Export Service**

In `backend/app/services/__init__.py`:
```python
from backend.app.services.audit import AuditService
from backend.app.services.token import TokenService

__all__ = ["AuditService", "TokenService"]
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/token.py backend/app/services/__init__.py
git commit -m "feat: implement TokenService for quota checking and usage recording"
```

---

### Task 2: Extract LLM Token Usage

**Files:**
- Modify: `backend/app/query/llm_sql.py`
- Modify: `backend/app/query/pipeline.py`

- [ ] **Step 1: Update `LLMSqlGenerator.generate` signature and return type**

In `backend/app/query/llm_sql.py`:
Modify it to return a tuple `(sql_string, token_usage_dict)` instead of just `sql_string`. 
The dict should be `{"prompt_tokens": int, "completion_tokens": int, "model": str}`.

*Note: You need to inspect how LiteLLM is being called and extract `response.usage.prompt_tokens`.*

- [ ] **Step 2: Update `_generate_sql` in `pipeline.py`**

In `backend/app/query/pipeline.py`, update `_generate_sql` to handle the tuple returned by `LLMSqlGenerator`.
It should also return the token usage up to `process_query`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/query/llm_sql.py backend/app/query/pipeline.py
git commit -m "feat: extract token usage from LLM response"
```

---

### Task 3: Enforce Quota and Record Usage in Pipeline

**Files:**
- Modify: `backend/app/query/pipeline.py`
- Modify: `backend/app/api/endpoints/query.py`

- [ ] **Step 1: Enforce Quota Pre-Execution**

In `backend/app/query/pipeline.py`, at the very beginning of `process_query`:
1. Obtain Redis connection (via a dependency or import `redis_client` from `backend.app.core.redis`).
2. Instantiate `TokenService(db=db, redis=redis_client)`.
3. Call `check_quota()`. If False, `raise HTTPException(429, "Token quota exceeded")` or yield an SSE error event.

- [ ] **Step 2: Record Usage Post-Execution**

In `process_query`, after `_generate_sql` returns the token usage dict:
1. Call `await token_svc.record_usage(...)` with the extracted tokens.

- [ ] **Step 3: Commit**

```bash
git add backend/app/query/pipeline.py backend/app/api/endpoints/query.py
git commit -m "feat: enforce token quotas and record usage in query pipeline"
```
