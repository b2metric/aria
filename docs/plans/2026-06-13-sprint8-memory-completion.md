# Sprint 8: Memory Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use engineering-core:subagent-driven-development (recommended) or engineering-core:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the memory system with per-memory TTL editing, team memory management, and stats dashboard.

**Architecture:** Extend existing Mem0+Qdrant memory service with custom TTL metadata, add team memory CRUD APIs, and build stats aggregation for admin dashboard.

**Tech Stack:** FastAPI, Mem0, Qdrant, Next.js, Recharts, Tailwind

---

## File Structure

```
backend/app/api/endpoints/admin/
├── memory.py          # MODIFY: Add PATCH TTL endpoint, update list response
├── team_memory.py     # MODIFY: Add CRUD for team conventions

backend/app/memory/
├── service.py         # MODIFY: Add update_ttl(), get_stats() methods

frontend/src/app/admin/memory/
├── page.tsx           # MODIFY: Add TTL edit modal, stats section
```

---

## Task 1: S8.5 — Memory Retention Backend (TTL Support)

**Files:**
- Modify: `backend/app/api/endpoints/admin/memory.py`
- Modify: `backend/app/memory/service.py`

### Step 1: Add TTL update method to MemoryService

- [ ] **1.1: Add update_memory_ttl method**

```python
# backend/app/memory/service.py - add after delete_memory method (~line 400)

def update_memory_ttl(
    self,
    memory_id: str,
    ttl_days: int | None,
) -> bool:
    """Update TTL for a specific memory entry.
    
    Args:
        memory_id: Memory identifier
        ttl_days: Days until expiration (None = never expire)
    
    Returns:
        True if updated successfully
    """
    if not self._memory:
        return False
    
    try:
        # Calculate expires_at timestamp
        if ttl_days is None:
            expires_at = None  # Never expires
        elif ttl_days == 0:
            # Immediate deletion
            return self.delete_memory(memory_id)
        else:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat()
        
        # Update metadata with expires_at
        # Mem0 doesn't have native update, so we need to use Qdrant directly
        from qdrant_client import QdrantClient
        settings = get_settings()
        
        qdrant_url = settings.qdrant_url
        if qdrant_url.startswith("http://"):
            qdrant_host = qdrant_url.replace("http://", "").split(":")[0]
            qdrant_port = int(qdrant_url.split(":")[-1])
        else:
            qdrant_host = "localhost"
            qdrant_port = 6333
        
        client = QdrantClient(host=qdrant_host, port=qdrant_port)
        
        # Update the point's payload with expires_at
        client.set_payload(
            collection_name=settings.qdrant_collection,
            payload={"expires_at": expires_at},
            points=[memory_id],
        )
        
        logger.info("Updated TTL for memory %s: expires_at=%s", memory_id, expires_at)
        return True
        
    except Exception as e:
        logger.warning("Failed to update TTL for memory %s: %s", memory_id, e)
        return False
```

- [ ] **1.2: Add get_memory_stats method**

```python
# backend/app/memory/service.py - add after update_memory_ttl

def get_memory_stats(self, workspace_id: str) -> dict:
    """Get memory statistics for a workspace.
    
    Returns:
        Dict with counts by type, recent activity, expiring soon
    """
    if not self._memory:
        return {"total": 0, "by_type": {}, "expiring_soon": 0}
    
    stats = {
        "total": 0,
        "by_type": {"user": 0, "team": 0, "cache": 0},
        "expiring_soon": 0,  # Expiring in next 7 days
        "recent_7d": 0,      # Created in last 7 days
    }
    
    try:
        now = datetime.now(timezone.utc)
        soon_cutoff = now + timedelta(days=7)
        recent_cutoff = now - timedelta(days=7)
        
        # Get all memories for each type
        for mem_type, user_pattern in [
            ("cache", f"{workspace_id}:query_cache"),
            ("user", f"{workspace_id}:"),  # Will need iteration
            ("team", f"{workspace_id}:team:"),
        ]:
            memories = self._memory.get_all(user_id=user_pattern)
            results = memories.get("results", []) if isinstance(memories, dict) else []
            
            for mem in results:
                stats["total"] += 1
                stats["by_type"][mem_type] += 1
                
                # Check created_at for recent
                created_at = mem.get("created_at")
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            mem_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        else:
                            mem_time = datetime.fromtimestamp(created_at, tz=timezone.utc)
                        
                        if mem_time > recent_cutoff:
                            stats["recent_7d"] += 1
                    except (ValueError, TypeError):
                        pass
                
                # Check expires_at for expiring soon
                expires_at = mem.get("metadata", {}).get("expires_at") if mem.get("metadata") else None
                if expires_at:
                    try:
                        exp_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                        if exp_time < soon_cutoff:
                            stats["expiring_soon"] += 1
                    except (ValueError, TypeError):
                        pass
        
    except Exception as e:
        logger.warning("Failed to get memory stats: %s", e)
    
    return stats
```

### Step 2: Add PATCH endpoint for TTL update

- [ ] **2.1: Add PATCH /admin/memory/{memory_id} endpoint**

```python
# backend/app/api/endpoints/admin/memory.py - add after delete_memory endpoint

from pydantic import BaseModel

class MemoryTTLUpdate(BaseModel):
    ttl_days: int | None = None  # None = never expire, 0 = delete immediately


@router.patch("/{memory_id}")
async def update_memory_ttl(
    memory_id: str,
    update: MemoryTTLUpdate,
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Update TTL for a specific memory entry.
    
    Args:
        memory_id: Memory identifier
        update: TTL update payload (ttl_days: null=never, 0=delete, N=days)
    
    Returns:
        Updated memory info
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    try:
        svc = MemoryService.get_instance()
        
        if update.ttl_days == 0:
            # Immediate deletion
            success = svc.delete_memory(memory_id)
            if success:
                return {"deleted": True, "id": memory_id}
            raise HTTPException(status_code=404, detail="Memory not found")
        
        success = svc.update_memory_ttl(memory_id, update.ttl_days)
        
        if success:
            expires_at = None
            if update.ttl_days:
                expires_at = (datetime.now(timezone.utc) + timedelta(days=update.ttl_days)).isoformat()
            
            log.info("admin.memory: Updated TTL for %s to %s days", memory_id, update.ttl_days)
            return {
                "updated": True,
                "id": memory_id,
                "ttl_days": update.ttl_days,
                "expires_at": expires_at,
            }
        else:
            raise HTTPException(status_code=404, detail="Memory not found or update failed")
            
    except HTTPException:
        raise
    except Exception as exc:
        log.error("admin.memory: Failed to update TTL for %s: %s", memory_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to update TTL: {exc}") from exc
```

- [ ] **2.2: Add GET /admin/memory/stats endpoint**

```python
# backend/app/api/endpoints/admin/memory.py - add after update_memory_ttl

@router.get("/stats")
async def get_memory_stats(
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Get memory statistics for the workspace.
    
    Returns:
        Stats including total count, by type, expiring soon, recent activity
    """
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    
    try:
        svc = MemoryService.get_instance()
        stats = svc.get_memory_stats(workspace_id)
        return stats
        
    except Exception as exc:
        log.error("admin.memory: Failed to get stats: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {exc}") from exc
```

- [ ] **2.3: Add imports to memory.py**

```python
# backend/app/api/endpoints/admin/memory.py - add to imports at top
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
```

### Step 3: Verify backend changes

- [ ] **3.1: Restart backend and test endpoints**

```bash
docker restart aria-backend
sleep 5

# Test stats endpoint
curl -s "http://api.aria.localhost/api/admin/memory/stats" \
  -H "Authorization: Bearer <token>" | jq .

# Test TTL update (get a memory ID first from /api/admin/memory)
curl -X PATCH "http://api.aria.localhost/api/admin/memory/<memory_id>" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"ttl_days": 30}'
```

---

## Task 2: S8.4 — Admin Memory Management UI (TTL Edit)

**Files:**
- Modify: `frontend/src/app/admin/memory/page.tsx`

### Step 1: Add TTL edit modal and stats section

- [ ] **1.1: Update Memory interface to include expires_at**

```typescript
// frontend/src/app/admin/memory/page.tsx - update interface
interface Memory {
  id: string | null;
  entity_id: string;
  content: string;
  type: "user" | "team" | "cache";
  created_at: string | null;
  metadata: Record<string, unknown> | null;
  expires_at?: string | null;  // ADD THIS
}

interface MemoryStats {
  total: number;
  by_type: { user: number; team: number; cache: number };
  expiring_soon: number;
  recent_7d: number;
}
```

- [ ] **1.2: Add state for TTL editing and stats**

```typescript
// Add after existing useState declarations (~line 29)
const [editingTTL, setEditingTTL] = useState<string | null>(null);
const [ttlValue, setTtlValue] = useState<string>("");
const [stats, setStats] = useState<MemoryStats | null>(null);
```

- [ ] **1.3: Add fetchStats function**

```typescript
// Add after fetchMemories function
const fetchStats = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/admin/memory/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const data = await res.json();
      setStats(data);
    }
  } catch (err) {
    console.error("Failed to fetch stats", err);
  }
};
```

- [ ] **1.4: Add handleTTLUpdate function**

```typescript
// Add after handleCleanup function
const handleTTLUpdate = async (memoryId: string) => {
  const days = ttlValue === "" ? null : parseInt(ttlValue, 10);
  
  if (ttlValue !== "" && (isNaN(days!) || days! < 0)) {
    alert("Please enter a valid number of days (or leave empty for never)");
    return;
  }
  
  try {
    const res = await fetch(`${API_BASE}/api/admin/memory/${memoryId}`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ttl_days: days }),
    });
    
    if (res.ok) {
      const data = await res.json();
      if (data.deleted) {
        setMemories(memories.filter((m) => m.id !== memoryId));
      } else {
        // Update the memory in the list with new expires_at
        setMemories(memories.map((m) =>
          m.id === memoryId ? { ...m, expires_at: data.expires_at } : m
        ));
      }
      setEditingTTL(null);
      setTtlValue("");
      fetchStats(); // Refresh stats
    } else {
      const err = await res.json();
      alert(`Error: ${err.detail || "Failed to update TTL"}`);
    }
  } catch (err) {
    console.error("Failed to update TTL", err);
  }
};
```

- [ ] **1.5: Update useEffect to also fetch stats**

```typescript
// Update existing useEffect
useEffect(() => {
  if (token) {
    fetchMemories();
    fetchStats();
  }
}, [token, filter]);
```

- [ ] **1.6: Add Stats Section to JSX (before filter buttons)**

```tsx
{/* Stats Cards - add after description paragraph */}
{stats && (
  <div className="mb-6 grid grid-cols-4 gap-4">
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
      <div className="text-sm text-gray-500">Total Memories</div>
    </div>
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="text-2xl font-bold text-green-600">{stats.recent_7d}</div>
      <div className="text-sm text-gray-500">Added (7d)</div>
    </div>
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="text-2xl font-bold text-amber-600">{stats.expiring_soon}</div>
      <div className="text-sm text-gray-500">Expiring Soon</div>
    </div>
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex gap-2 text-sm">
        <span className="text-purple-600">{stats.by_type.user} user</span>
        <span className="text-blue-600">{stats.by_type.team} team</span>
        <span className="text-green-600">{stats.by_type.cache} cache</span>
      </div>
      <div className="text-sm text-gray-500">By Type</div>
    </div>
  </div>
)}
```

- [ ] **1.7: Add TTL column to table header**

```tsx
// Update table header - add before Actions column
<th className="px-6 py-4 font-medium w-28">Expires</th>
```

- [ ] **1.8: Add TTL cell to table rows**

```tsx
// Add before Actions cell in the table row
<td className="px-6 py-4 text-gray-500 text-xs">
  {editingTTL === mem.id ? (
    <div className="flex items-center gap-1">
      <input
        type="number"
        min="0"
        placeholder="∞"
        value={ttlValue}
        onChange={(e) => setTtlValue(e.target.value)}
        className="w-16 px-2 py-1 text-xs border border-gray-300 rounded"
      />
      <span className="text-gray-400">d</span>
      <button
        onClick={() => handleTTLUpdate(mem.id!)}
        className="p-1 text-green-600 hover:bg-green-50 rounded"
      >
        ✓
      </button>
      <button
        onClick={() => { setEditingTTL(null); setTtlValue(""); }}
        className="p-1 text-gray-400 hover:bg-gray-100 rounded"
      >
        ✕
      </button>
    </div>
  ) : (
    <button
      onClick={() => {
        setEditingTTL(mem.id);
        setTtlValue("");
      }}
      className="hover:text-blue-600 hover:underline"
    >
      {mem.expires_at
        ? new Date(mem.expires_at).toLocaleDateString()
        : "Never"}
    </button>
  )}
</td>
```

- [ ] **1.9: Add Clock icon import**

```tsx
// Update imports at top
import { Trash2, Brain, Users, Database, Filter, Sparkles, Clock } from "lucide-react";
```

### Step 2: Test UI changes

- [ ] **2.1: Build and verify**

```bash
cd /Users/tunasonmez/projects/b2metric-aria/frontend
npm run build
```

- [ ] **2.2: Visual verification**

Navigate to `http://aria.localhost/admin/memory` and verify:
- Stats cards show at top
- TTL column shows "Never" or date
- Clicking TTL opens inline editor
- Can set TTL to a number or leave empty for infinite

---

## Task 3: S8.3 — Team Memory Store

**Files:**
- Modify: `backend/app/api/endpoints/admin/team_memory.py`

### Step 1: Add team memory CRUD endpoints

- [ ] **1.1: Update team_memory.py with full CRUD**

```python
# backend/app/api/endpoints/admin/team_memory.py
"""Admin: manage team conventions/business rules (TEAM memory type)."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.auth.dependencies import get_current_user
from backend.app.memory.service import MemoryService, MemoryType

log = logging.getLogger("aria.admin")
router = APIRouter()


class TeamMemoryCreate(BaseModel):
    content: str
    team_id: str = "default"


class TeamMemoryUpdate(BaseModel):
    content: str | None = None
    ttl_days: int | None = None


@router.get("")
async def list_team_memories(
    team_id: str = "default",
    current_user: Any = Depends(get_current_user),
) -> list[dict]:
    """List all team conventions for a team."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    
    try:
        svc = MemoryService.get_instance()
        memories = svc.get_all_memories(
            user_id=team_id,
            workspace_id=workspace_id,
            memory_type=MemoryType.TEAM,
        )
        
        return [
            {
                "id": m.get("id"),
                "content": m.get("memory") or m.get("data") or "",
                "team_id": team_id,
                "created_at": m.get("created_at"),
                "metadata": m.get("metadata"),
            }
            for m in memories
        ]
        
    except Exception as exc:
        log.error("team_memory.list failed: %s", exc)
        return []


@router.post("")
async def create_team_memory(
    payload: TeamMemoryCreate,
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Create a new team convention/business rule."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    
    try:
        svc = MemoryService.get_instance()
        memory_id = svc.store(
            content=payload.content,
            memory_type=MemoryType.TEAM,
            user_id="admin",  # Creator
            workspace_id=workspace_id,
            team_id=payload.team_id,
            metadata={"created_by": getattr(current_user, "user_id", "admin")},
        )
        
        if memory_id:
            log.info("team_memory.create: Created %s for team %s", memory_id, payload.team_id)
            return {
                "created": True,
                "id": memory_id,
                "content": payload.content,
                "team_id": payload.team_id,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create team memory")
            
    except HTTPException:
        raise
    except Exception as exc:
        log.error("team_memory.create failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to create: {exc}") from exc


@router.delete("/{memory_id}")
async def delete_team_memory(
    memory_id: str,
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Delete a team convention."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    try:
        svc = MemoryService.get_instance()
        success = svc.delete_memory(memory_id)
        
        if success:
            log.info("team_memory.delete: Deleted %s", memory_id)
            return {"deleted": True, "id": memory_id}
        else:
            raise HTTPException(status_code=404, detail="Team memory not found")
            
    except HTTPException:
        raise
    except Exception as exc:
        log.error("team_memory.delete failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to delete: {exc}") from exc
```

### Step 2: Verify team memory router is registered

- [ ] **2.1: Check main.py for router registration**

```bash
grep -n "team_memory" /Users/tunasonmez/projects/b2metric-aria/backend/app/main.py
```

If not registered, add:
```python
from backend.app.api.endpoints.admin import team_memory
app.include_router(team_memory.router, prefix="/api/admin/team-memory", tags=["admin"])
```

---

## Task 4: S8.1 — Verify Memory → LLM Prompt Injection

**Files:**
- Verify: `backend/app/query/llm_sql.py`
- Verify: `backend/app/query/pipeline.py`

### Step 1: Verify memory injection is working

- [ ] **1.1: Check llm_sql.py uses memory context**

Memory context is already injected via `_build_memory_context()` in `llm_sql.py:66-70`. Verify with:

```bash
grep -A5 "_build_memory_context" /Users/tunasonmez/projects/b2metric-aria/backend/app/query/llm_sql.py
```

- [ ] **1.2: Add logging to verify injection at runtime**

```python
# backend/app/query/llm_sql.py - in generate_sql_with_llm function, after building contexts
if memory_ctx:
    logger.info("Memory context injected: %d chars", len(memory_ctx))
```

---

## Task 5: S8.2 — Verify User Preference Extraction

**Files:**
- Verify: `backend/app/query/pipeline.py`

### Step 1: Verify user preference extraction

- [ ] **1.1: Check extraction functions exist**

```bash
grep -n "_extract_preference\|_detect_chart" /Users/tunasonmez/projects/b2metric-aria/backend/app/query/pipeline.py
```

Already implemented at lines 84-146. No changes needed.

---

## Task 6: S8.6 — Memory Stats Dashboard (Already done in Task 2)

Stats section was added in Task 2 (S8.4). Mark as complete.

---

## Final Verification

- [ ] **Smoke gate**

```bash
cd /Users/tunasonmez/projects/b2metric-aria
bash smoke/check.sh
```

- [ ] **Visual verification of admin/memory page**

1. Navigate to `http://aria.localhost/admin/memory`
2. Verify stats cards at top
3. Verify TTL column and inline edit
4. Test TTL update on a cache entry
5. Navigate to Team Conventions page
6. Add a team convention
7. Verify it appears in memory list

- [ ] **Test query with memory context**

1. Go to Chat
2. Ask a question that should hit query cache
3. Check backend logs for "Memory context injected"
