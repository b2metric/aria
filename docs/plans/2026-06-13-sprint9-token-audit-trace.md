# Sprint 9: Token Management + Audit + Trace

**Tarih:** 2026-06-13
**Tema:** Critical gaps: Token quota enforcement, Audit logging, Query trace, Admin UX

---

## Tasks

### S9.1 — TokenTracker Service (Backend)
**Gap:** TOK-01, TOK-02
**Files:** `backend/app/services/token_tracker.py` (new)

```python
class TokenTracker:
    async def record_usage(
        self,
        user_id: str,
        workspace_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """Record token usage to token_usage_daily table."""
    
    async def get_daily_usage(self, user_id: str, date: date) -> int:
        """Get total tokens used by user on a specific date."""
    
    async def check_quota(self, user_id: str, workspace_id: str) -> tuple[bool, int, int]:
        """Check if user is within quota. Returns (allowed, used, limit)."""
```

Integration:
- Call `record_usage()` after every LiteLLM call in `llm_sql.py`
- Parse `response.usage.prompt_tokens` and `response.usage.completion_tokens`

---

### S9.2 — Quota Enforcement (Backend)
**Gap:** TOK-03
**Files:** `backend/app/query/pipeline.py`

Add at start of `process_query()`:
```python
allowed, used, limit = await token_tracker.check_quota(user_id, workspace_id)
if not allowed:
    yield {"type": "error", "message": f"Daily token limit exceeded ({used:,}/{limit:,})"}
    return
```

---

### S9.3 — Query Trace Model (Backend)
**Gap:** NEW — Admin conversation debug
**Files:** `backend/app/query/__init__.py`, `backend/app/query/pipeline.py`

Extend `ConversationMessage`:
```python
class QueryTrace(BaseModel):
    """Debug trace for a single query execution."""
    
    # Timing
    started_at: str
    completed_at: str
    duration_ms: int
    
    # Memory context
    user_memories_found: int = 0
    team_memories_found: int = 0
    cache_hit: bool = False
    memory_correction_applied: bool = False
    
    # SQL generation
    tables_considered: list[str] = []
    sql_method: str = "rule_based"  # or "llm"
    sql_fallback_used: bool = False
    
    # Token usage
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model_used: str = ""
    
    # Result
    row_count: int = 0
    chart_type: str | None = None
    error: str | None = None


class ConversationMessage(BaseModel):
    # ... existing fields ...
    trace: QueryTrace | None = None  # NEW
```

Populate trace in `process_query()` pipeline stages.

---

### S9.4 — Token Usage Dashboard API (Backend)
**Gap:** ADM-02
**Files:** `backend/app/api/endpoints/admin/token_usage.py` (new)

Endpoints:
```
GET /api/admin/token-usage
    ?user_id=...  (optional filter)
    ?team_id=...  (optional filter)
    ?start_date=2026-06-01
    ?end_date=2026-06-13
    
Response:
{
  "total_tokens": 125000,
  "by_user": [
    {"user_id": "...", "email": "...", "tokens": 50000, "queries": 120}
  ],
  "by_model": [
    {"model": "deepseek-chat", "tokens": 80000},
    {"model": "gpt-4o-mini", "tokens": 45000}
  ],
  "by_day": [
    {"date": "2026-06-13", "tokens": 15000}
  ]
}
```

---

### S9.5 — Admin Conversations API (Backend)
**Gap:** NEW — Admin needs to see all users' conversations
**Files:** `backend/app/api/endpoints/admin/conversations.py` (new)

Endpoints:
```
GET /api/admin/conversations
    ?user_id=...  (optional filter)
    ?limit=50
    
GET /api/admin/conversations/{id}
    Returns full conversation with trace data
```

Note: Requires Redis SCAN to list all conversations across users.

---

### S9.6 — Memory Content Modal (Frontend)
**Gap:** UX — truncated content not readable
**Files:** `frontend/src/app/admin/memory/page.tsx`

Changes:
1. Add `MemoryDetailModal` component
2. On row click → open modal with full content
3. Modal shows:
   - Full `content` text (scrollable, max-height)
   - Full `metadata` as formatted JSON
   - `created_at`, `expires_at`
   - Copy button
4. Responsive: mobile-friendly bottom sheet or centered modal

---

### S9.7 — Token Usage Dashboard UI (Frontend)
**Gap:** ADM-02
**Files:** `frontend/src/app/admin/token-usage/page.tsx` (new)

Features:
- Date range picker (default: last 7 days)
- Summary cards: Total tokens, Active users, Avg per query
- Bar chart: Daily usage trend
- Table: Top users by token consumption
- Table: Usage by model
- Filter by user/team

---

### S9.8 — Conversation History Admin UI (Frontend)
**Gap:** NEW
**Files:** `frontend/src/app/admin/conversations/page.tsx` (new)

Features:
- List all conversations (all users)
- Columns: User, Title, Messages, Created, Last Activity
- Search by user email or conversation title
- Click → Conversation Detail page

---

### S9.9 — Conversation Detail with Trace (Frontend)
**Gap:** NEW
**Files:** `frontend/src/app/admin/conversations/[id]/page.tsx` (new)

Features:
- Full chat history (user + assistant messages)
- For each assistant message, expandable "Trace" panel:
  - Memory context: X user memories, Y team memories, correction applied?
  - SQL: method (rule/LLM), tables considered, fallback?
  - Tokens: prompt/completion/total, model
  - Timing: duration_ms
  - Result: row_count, chart_type
- Responsive: trace as collapsible accordion on mobile

---

### S9.10 — Audit Logging (Backend)
**Gap:** SEC-03
**Files:** 
- `backend/app/models/audit.py` (new)
- `backend/app/services/audit_logger.py` (new)
- `backend/app/api/endpoints/admin/audit.py` (new)

Model:
```python
class AuditLog(Base):
    id: UUID
    timestamp: datetime
    user_id: UUID | None
    action: str  # "login", "query", "admin.memory.delete", etc.
    resource_type: str  # "conversation", "memory", "tenant_config"
    resource_id: str | None
    details: dict  # JSON payload
    ip_address: str | None
    user_agent: str | None
```

Actions to log:
- User login/logout
- Query execution (question, success/fail)
- Admin: memory delete, tenant config change, vault edit

API:
```
GET /api/admin/audit-log
    ?action=query
    ?user_id=...
    ?start_date=...
    ?limit=100
```

---

### S9.11 — Audit Log Viewer UI (Frontend)
**Gap:** ADM-03
**Files:** `frontend/src/app/admin/audit-log/page.tsx` (new)

Features:
- Filterable table: action, user, date range
- Expandable row for `details` JSON
- Export to CSV

### S9.12 — Team Management Admin UI
**Gap:** ADM-06
**Files:** `frontend/src/app/admin/teams/page.tsx`, `backend/app/api/endpoints/admin/teams.py`

Features:
- List all teams in the workspace
- Create new team (name, description)
- Edit/Delete team
- Assign users to teams (modal)

---

## Verification

1. Token tracking: Run 3 queries, check `token_usage_daily` has rows
2. Quota enforcement: Set low limit (1000), verify 4th query returns 429
3. Trace: Query → check conversation message has `trace` field
4. Admin UI: Login as admin, navigate to /admin/conversations, /admin/token-usage, /admin/audit-log
5. Memory modal: Click any memory row, verify full content displays

---

## Dependencies

- S9.1 before S9.2 (tracker before enforcement)
- S9.3 before S9.8/S9.9 (trace model before trace UI)
- S9.4 before S9.7 (API before UI)
- S9.5 before S9.8 (API before UI)
- S9.10 before S9.11 (backend before UI)
- S9.6 is independent

---

## Estimate

| Task | Complexity | Est. Time |
|------|------------|-----------|
| S9.1 | Medium | 30m |
| S9.2 | Low | 15m |
| S9.3 | Medium | 45m |
| S9.4 | Medium | 30m |
| S9.5 | Medium | 30m |
| S9.6 | Low | 20m |
| S9.7 | Medium | 45m |
| S9.8 | Medium | 30m |
| S9.9 | High | 60m |
| S9.10 | High | 60m |
| S9.11 | Medium | 30m |

**Total:** ~6.5 hours
