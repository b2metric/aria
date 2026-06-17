# Admin UI: Vault RLS & Audit Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use engineering-core:subagent-driven-development (recommended) or engineering-core:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Admin API endpoints and UI for managing Team Vault Policies and viewing Audit Logs.

**Architecture:** Add two new FastAPI endpoints in the admin router. Add two new Next.js pages in the admin section using shadcn/ui.

**Tech Stack:** Python 3.12, FastAPI, Next.js 16, React, Tailwind CSS, shadcn/ui.

---

### Task 1: Audit Log Backend API

**Files:**
- Create: `backend/app/api/endpoints/admin/audit.py`
- Modify: `backend/app/api/endpoints/admin/__init__.py`

- [ ] **Step 1: Create Audit Endpoint**

Create `backend/app/api/endpoints/admin/audit.py`:
```python
import logging
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_user
from backend.app.db.dependencies import get_db
from backend.app.services.audit import AuditService

log = logging.getLogger("aria.admin.audit")
router = APIRouter()

@router.get("")
async def list_audit_logs(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_id: str | None = None,
    action: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List audit logs with filtering and pagination."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    
    try:
        user_uuid = uuid.UUID(user_id) if user_id else None
        
        svc = AuditService(db)
        logs = await svc.get_logs(
            workspace_id=workspace_id,
            user_id=user_uuid,
            action=action,
            status=status_filter,
            limit=limit,
            offset=offset
        )
        
        total_count = await svc.count_logs(
            workspace_id=workspace_id,
            user_id=user_uuid,
            action=action,
            status=status_filter
        )
        
        return {
            "data": [
                {
                    "id": str(log.id),
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "details": log.details,
                    "status": log.status,
                    "user_id": str(log.user_id) if log.user_id else None,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid UUID format: {exc}")
    except Exception as exc:
        log.error("audit.list failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to list audit logs: {exc}")
```

- [ ] **Step 2: Register Router**

Modify `backend/app/api/endpoints/admin/__init__.py` to include the new router:
```python
from fastapi import APIRouter

from backend.app.api.endpoints.admin import memory
from backend.app.api.endpoints.admin import team_memory
from backend.app.api.endpoints.admin import tenant
from backend.app.api.endpoints.admin import audit

router = APIRouter()
router.include_router(memory.router, prefix="/memory", tags=["admin", "memory"])
router.include_router(team_memory.router, prefix="/team-memory", tags=["admin", "team-memory"])
router.include_router(tenant.router, prefix="/tenant", tags=["admin", "tenant"])
router.include_router(audit.router, prefix="/audit-logs", tags=["admin", "audit"])
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/endpoints/admin/audit.py backend/app/api/endpoints/admin/__init__.py
git commit -m "feat: add admin audit logs API endpoint"
```

---

### Task 2: Vault Policy Backend API

**Files:**
- Create: `backend/app/api/endpoints/admin/vault_policies.py`
- Modify: `backend/app/api/endpoints/admin/__init__.py`

- [ ] **Step 1: Create Vault Policies Endpoint**

Create `backend/app/api/endpoints/admin/vault_policies.py`:
```python
import logging
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_user
from backend.app.db.dependencies import get_db
from backend.app.models.governance import TeamVaultPolicy

log = logging.getLogger("aria.admin.vault_policies")
router = APIRouter()

class VaultPolicyUpdate(BaseModel):
    allowed_tables: list[str]

@router.get("")
async def get_team_policies(
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get all vault policies for the workspace."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    
    try:
        result = await db.execute(
            select(TeamVaultPolicy)
            .where(TeamVaultPolicy.workspace_id == workspace_id)
        )
        policies = result.scalars().all()
        
        return [
            {
                "id": str(p.id),
                "team_id": str(p.team_id) if p.team_id else "default",
                "allowed_tables": p.allowed_tables,
                "deny_columns": p.deny_columns,
            }
            for p in policies
        ]
    except Exception as exc:
        log.error("vault_policies.get failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to get policies: {exc}")

@router.put("/{team_id}")
async def update_team_policy(
    team_id: str,
    payload: VaultPolicyUpdate,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update allowed tables for a team."""
    if not getattr(current_user, "can_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    workspace_id = getattr(current_user, "workspace_id", None) or "default"
    
    try:
        team_uuid = None if team_id == "default" else uuid.UUID(team_id)
        
        # Check if exists
        query = select(TeamVaultPolicy).where(TeamVaultPolicy.workspace_id == workspace_id)
        if team_uuid:
            query = query.where(TeamVaultPolicy.team_id == team_uuid)
        else:
            query = query.where(TeamVaultPolicy.team_id.is_(None))
            
        result = await db.execute(query)
        policy = result.scalars().first()
        
        if policy:
            policy.allowed_tables = payload.allowed_tables
        else:
            # Create new
            policy = TeamVaultPolicy(
                workspace_id=workspace_id,
                team_id=team_uuid,
                allowed_tables=payload.allowed_tables,
                deny_columns={}
            )
            db.add(policy)
            
        await db.commit()
        return {"success": True, "team_id": team_id, "allowed_tables": policy.allowed_tables}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team_id format")
    except Exception as exc:
        await db.rollback()
        log.error("vault_policies.update failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to update policy: {exc}")
```

- [ ] **Step 2: Register Router**

Modify `backend/app/api/endpoints/admin/__init__.py` to include the new router:
```python
# ... existing imports
from backend.app.api.endpoints.admin import vault_policies

# ... existing includes
router.include_router(vault_policies.router, prefix="/vault-policies", tags=["admin", "vault-policies"])
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/endpoints/admin/vault_policies.py backend/app/api/endpoints/admin/__init__.py
git commit -m "feat: add admin vault policies API endpoint"
```

---

### Task 3: Audit Logs Frontend Page

**Files:**
- Create: `frontend/src/app/admin/audit-log/page.tsx`
- Modify: `frontend/src/app/admin/layout.tsx` (Add navigation link)

- [ ] **Step 1: Create Frontend Page**

Create `frontend/src/app/admin/audit-log/page.tsx`:
```tsx
"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { ShieldAlert, Search, RefreshCw, AlertCircle, CheckCircle2, XCircle, Database } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type AuditLog = {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: any;
  status: string;
  user_id: string | null;
  ip_address: string | null;
  created_at: string;
};

export default function AuditLogPage() {
  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const router = useRouter();

  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [actionFilter, setActionFilter] = useState<string>("all");

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/api/auth/signin');
  }, [status, router]);

  const fetchLogs = async () => {
    if (!token) return;
    try {
      setLoading(true);
      let url = `${API_BASE}/api/admin/audit-logs?limit=100`;
      if (statusFilter !== "all") url += `&status=${statusFilter}`;
      if (actionFilter !== "all") url += `&action=${actionFilter}`;
      
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setLogs(data.data || []);
      }
    } catch (err) {
      console.error("Failed to fetch audit logs", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [token, statusFilter, actionFilter]);

  const getStatusBadge = (logStatus: string) => {
    switch (logStatus) {
      case 'success': return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200"><CheckCircle2 className="w-3 h-3 mr-1"/> Success</Badge>;
      case 'failed': return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200"><XCircle className="w-3 h-3 mr-1"/> Failed</Badge>;
      case 'denied': return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200"><AlertCircle className="w-3 h-3 mr-1"/> Denied</Badge>;
      default: return <Badge variant="outline">{logStatus}</Badge>;
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-blue-600" />
            Audit Logs
          </h1>
          <p className="text-gray-500 mt-1">Monitor data access, queries, and system events.</p>
        </div>
        <Button variant="outline" onClick={fetchLogs} disabled={loading} className="w-full sm:w-auto">
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="flex flex-wrap gap-4 bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
        <div className="w-full sm:w-48">
          <label className="text-xs font-medium text-gray-500 mb-1.5 block">Status</label>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger><SelectValue placeholder="All Statuses" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="success">Success</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="denied">Denied</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="w-full sm:w-48">
          <label className="text-xs font-medium text-gray-500 mb-1.5 block">Action</label>
          <Select value={actionFilter} onValueChange={setActionFilter}>
            <SelectTrigger><SelectValue placeholder="All Actions" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Actions</SelectItem>
              <SelectItem value="query">Query Executed</SelectItem>
              <SelectItem value="export">Data Exported</SelectItem>
              <SelectItem value="policy_evaluation">Policy Evaluation</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 font-semibold">Timestamp</th>
                <th className="px-6 py-3 font-semibold">User ID</th>
                <th className="px-6 py-3 font-semibold">Action & Status</th>
                <th className="px-6 py-3 font-semibold">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading && logs.length === 0 ? (
                <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500">Loading audit logs...</td></tr>
              ) : logs.length === 0 ? (
                <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500">No audit logs found matching criteria.</td></tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-gray-600">
                      {log.user_id || 'System'}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1.5 items-start">
                        <span className="font-medium text-gray-900">{log.action}</span>
                        {getStatusBadge(log.status)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="max-w-md">
                        {log.action === 'query' && log.details?.sql ? (
                          <div className="bg-gray-50 p-2 rounded border border-gray-200 font-mono text-xs text-gray-800 line-clamp-2" title={log.details.sql}>
                            {log.details.sql}
                          </div>
                        ) : log.resource_id ? (
                          <span className="font-medium">{log.resource_type}: {log.resource_id}</span>
                        ) : (
                          <span className="text-gray-400 italic">No details</span>
                        )}
                        {log.details?.row_count !== undefined && (
                          <div className="mt-1 text-xs text-blue-600 font-medium">
                            Returned {log.details.row_count} rows
                          </div>
                        )}
                        {log.status === 'failed' && log.details?.error && (
                          <div className="mt-1 text-xs text-red-600 line-clamp-1" title={log.details.error}>
                            Error: {log.details.error}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add Navigation Link**

*Instructions for the implementer: Inspect `frontend/src/app/admin/layout.tsx` (or wherever the admin sidebar is defined) and add a link to `/admin/audit-log` with the `ShieldAlert` icon.*

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/admin/audit-log/page.tsx
git commit -m "feat: add admin UI for audit logs"
```

---

### Task 4: Vault Access UI (RLS Configuration)

**Files:**
- Create: `frontend/src/app/admin/vault-access/page.tsx`
- Modify: `frontend/src/app/admin/layout.tsx` (Add navigation link)

- [ ] **Step 1: Create Frontend Page**

Create `frontend/src/app/admin/vault-access/page.tsx`:
```tsx
"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Lock, Save, Database, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type VaultTable = {
  table_name: string;
  description: string;
};

type VaultPolicy = {
  id: string;
  team_id: string;
  allowed_tables: string[];
};

export default function VaultAccessPage() {
  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const router = useRouter();

  const [tables, setTables] = useState<VaultTable[]>([]);
  const [policies, setPolicies] = useState<VaultPolicy[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string>("default");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Current working state for the selected team
  const [allowedTables, setAllowedTables] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/api/auth/signin');
  }, [status, router]);

  useEffect(() => {
    const fetchData = async () => {
      if (!token) return;
      try {
        setLoading(true);
        // 1. Fetch tables
        const tablesRes = await fetch(`${API_BASE}/api/workspaces/vault/tables?workspace_id=default`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (tablesRes.ok) {
          setTables(await tablesRes.json());
        }

        // 2. Fetch policies
        const policiesRes = await fetch(`${API_BASE}/api/admin/vault-policies`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (policiesRes.ok) {
          const data = await policiesRes.json();
          setPolicies(data);
          
          // Initialize state for selected team
          const defaultPolicy = data.find((p: any) => p.team_id === "default");
          if (defaultPolicy) {
            setAllowedTables(new Set(defaultPolicy.allowed_tables));
          }
        }
      } catch (err) {
        console.error("Failed to fetch data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  // When team selection changes (future proofing for multi-team UI)
  useEffect(() => {
    const policy = policies.find(p => p.team_id === selectedTeam);
    setAllowedTables(new Set(policy?.allowed_tables || []));
  }, [selectedTeam, policies]);

  const handleToggleTable = (tableName: string) => {
    const next = new Set(allowedTables);
    if (next.has(tableName)) {
      next.delete(tableName);
    } else {
      next.add(tableName);
    }
    setAllowedTables(next);
  };

  const handleSave = async () => {
    if (!token) return;
    try {
      setSaving(true);
      const res = await fetch(`${API_BASE}/api/admin/vault-policies/${selectedTeam}`, {
        method: 'PUT',
        headers: { 
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}` 
        },
        body: JSON.stringify({
          allowed_tables: Array.from(allowedTables)
        })
      });
      
      if (res.ok) {
        // Update local policies state
        const updatedPolicy = await res.json();
        setPolicies(prev => {
          const exists = prev.find(p => p.team_id === selectedTeam);
          if (exists) {
            return prev.map(p => p.team_id === selectedTeam ? { ...p, allowed_tables: updatedPolicy.allowed_tables } : p);
          }
          return [...prev, { id: 'temp', team_id: selectedTeam, allowed_tables: updatedPolicy.allowed_tables }];
        });
      }
    } catch (err) {
      console.error("Failed to save policy", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Lock className="w-6 h-6 text-blue-600" />
            Vault Access Policies
          </h1>
          <p className="text-gray-500 mt-1">Configure which tables are visible to each team (App-Level RLS).</p>
        </div>
        <Button onClick={handleSave} disabled={loading || saving} className="bg-blue-600 hover:bg-blue-700">
          <Save className={`w-4 h-4 mr-2 ${saving ? 'animate-pulse' : ''}`} />
          {saving ? 'Saving...' : 'Save Policy'}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Teams List (Simplified for now) */}
        <Card className="col-span-1 shadow-sm h-fit">
          <CardHeader className="pb-3 border-b border-gray-100 bg-gray-50/50">
            <CardTitle className="text-base flex items-center gap-2">
              <Users className="w-4 h-4 text-gray-500" />
              Teams
            </CardTitle>
          </CardHeader>
          <CardContent className="p-2">
            <button 
              className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium ${selectedTeam === 'default' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}`}
              onClick={() => setSelectedTeam('default')}
            >
              Default Team
            </button>
            {/* Future: Map over actual teams here */}
          </CardContent>
        </Card>

        {/* Tables Checkboxes */}
        <Card className="col-span-1 md:col-span-3 shadow-sm">
          <CardHeader className="pb-4 border-b border-gray-100 bg-gray-50/50">
            <div className="flex justify-between items-center">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Database className="w-5 h-5 text-blue-600" />
                  Allowed Tables
                </CardTitle>
                <CardDescription className="mt-1">
                  Select the vault tables the <span className="font-semibold text-gray-900">{selectedTeam}</span> team can query.
                </CardDescription>
              </div>
              <div className="text-sm font-medium text-gray-500 bg-white px-3 py-1 rounded-full border border-gray-200">
                {allowedTables.size} / {tables.length} Selected
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading tables...</div>
            ) : tables.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No tables found in the vault.</div>
            ) : (
              <div className="divide-y divide-gray-100">
                {tables.map(table => (
                  <label 
                    key={table.table_name} 
                    className="flex items-start gap-4 p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <Checkbox 
                      className="mt-1"
                      checked={allowedTables.has(table.table_name)}
                      onCheckedChange={() => handleToggleTable(table.table_name)}
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{table.table_name}</p>
                      <p className="text-sm text-gray-500 mt-0.5 line-clamp-1">{table.description || "No description"}</p>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add Navigation Link**

*Instructions for the implementer: Inspect `frontend/src/app/admin/layout.tsx` (or wherever the admin sidebar is defined) and add a link to `/admin/vault-access` with the `Lock` icon.*

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/admin/vault-access/page.tsx
git commit -m "feat: add admin UI for vault access policies"
```

---

### Execution

**Plan complete and saved to `docs/engineering-core/plans/2026-06-13-vault-rls-audit-ui-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**