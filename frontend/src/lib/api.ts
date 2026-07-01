import { getSession } from "next-auth/react";
import type { DashboardData, PickerItem, SavedQuery } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Demo / mock data for development before backend endpoints are ready. */
export function getMockDashboardData(): DashboardData {
  return {
    stats: [
      { label: "Total Queries", value: "12.4K", change: "+14%", changeType: "up" },
      { label: "Accuracy", value: "94.2%", change: "+2.1%", changeType: "up" },
      { label: "Avg Response", value: "1.8s", change: "-0.3s", changeType: "down" },
      { label: "Active Users", value: "342", change: "+8%", changeType: "up" },
    ],
    workspaceStats: [
      { label: "Workspace Queries", value: "48.1K", change: "+11%", changeType: "up" },
      { label: "Team Members", value: "18", change: "+2", changeType: "up" },
      { label: "Saved Queries", value: "126", change: "+9%", changeType: "up" },
      { label: "Data Sources", value: "7", change: "0", changeType: "neutral" },
    ],
    recentConversations: [
      {
        id: "c1",
        query: "Show me prepaid revenue by region for last quarter",
        timestamp: "2 min ago",
        status: "completed",
        rowCount: 142,
        duration: "1.2s",
      },
      {
        id: "c2",
        query: "Top 10 customers by recharge amount this month",
        timestamp: "15 min ago",
        status: "completed",
        rowCount: 10,
        duration: "0.8s",
      },
      {
        id: "c3",
        query: "Churn prediction for postpaid segment",
        timestamp: "1 hour ago",
        status: "completed",
        rowCount: 2300,
        duration: "3.1s",
      },
      {
        id: "c4",
        query: "Compare ARPU across all regions YTD",
        timestamp: "2 hours ago",
        status: "completed",
        rowCount: 24,
        duration: "1.5s",
      },
      {
        id: "c5",
        query: "Daily active subscribers trend last 30 days",
        timestamp: "3 hours ago",
        status: "failed",
        duration: "—",
      },
    ],
    savedQueries: [
      {
        id: "s1",
        name: "Monthly Revenue by Region",
        question: "Show monthly prepaid revenue by region for current year",
        sql: "SELECT region, SUM(revenue) FROM prepaid GROUP BY region",
        created_at: "2026-05-15",
      },
      {
        id: "s2",
        name: "Top Customers Recharge",
        question: "Top 10 customers by recharge amount this month",
        sql: "SELECT customer, SUM(amount) FROM recharge GROUP BY customer ORDER BY 2 DESC LIMIT 10",
        created_at: "2026-05-20",
      },
      {
        id: "s3",
        name: "Churn Risk Analysis",
        question: "Churn prediction for postpaid segment with risk scores",
        sql: "SELECT customer, risk_score FROM churn_predictions WHERE segment = 'postpaid'",
        created_at: "2026-05-28",
      },
      {
        id: "s4",
        name: "ARPU Comparison YTD",
        question: "Compare ARPU across all regions YTD vs last year",
        sql: "SELECT region, arpu_ytd, arpu_last_year FROM arpu_benchmark",
        created_at: "2026-06-01",
      },
    ],
    chartData: [
      { month: "Jan", revenue: 2400, lastYear: 2100 },
      { month: "Feb", revenue: 1398, lastYear: 1200 },
      { month: "Mar", revenue: 9800, lastYear: 8700 },
      { month: "Apr", revenue: 3908, lastYear: 3500 },
      { month: "May", revenue: 4800, lastYear: 4200 },
      { month: "Jun", revenue: 3800, lastYear: 3600 },
      { month: "Jul", revenue: 4300, lastYear: 3900 },
      { month: "Aug", revenue: 5100, lastYear: 4500 },
      { month: "Sep", revenue: 6200, lastYear: 5500 },
      { month: "Oct", revenue: 5800, lastYear: 5100 },
      { month: "Nov", revenue: 4900, lastYear: 4400 },
      { month: "Dec", revenue: 7100, lastYear: 6500 },
    ],
    chartConfig: {
      type: "bar",
      xKey: "month",
      yKeys: ["revenue", "lastYear"],
      title: "Monthly Revenue",
      colors: ["#4a9eed", "#93c5fd"],
    },
  };
}

export async function fetchDashboardData(): Promise<DashboardData> {
  try {
    const res = await fetch(`${API_BASE}/api/dashboard`, {
      credentials: "include",
    });
    if (res.ok) return await res.json();
  } catch {
    // fall back to mock data
  }
  return getMockDashboardData();
}

/**
 * Fetch the dashboard with optional team/user activity filters.
 *
 * The backend applies `team_id`/`user_id_filter` to the workspace-scoped
 * aggregates + 7-day trend (always scoped to the caller's tenant). Filters
 * are only sent when provided so the default call stays unfiltered.
 */
export async function getDashboard(
  token: string,
  opts?: { teamId?: string; userId?: string },
): Promise<DashboardData> {
  const params = new URLSearchParams();
  if (opts?.teamId) params.set("team_id", opts.teamId);
  if (opts?.userId) params.set("user_id_filter", opts.userId);
  const qs = params.toString();
  const res = await fetch(`${API_BASE}/api/dashboard${qs ? `?${qs}` : ""}`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: "omit",
  });
  if (!res.ok) throw new Error(`Failed to fetch dashboard: ${res.status}`);
  return res.json();
}

// ── Chat / Query API ───────────────────────────────────────────────────

/**
 * Stream a query to the backend via SSE.
 * Returns an object with:
 *  - reader: ReadableStreamDefaultReader for raw SSE chunks
 *  - abort: AbortController to cancel the request
 */
export function streamQuery(
  question: string,
  conversationId?: string,
  workspaceId: string = "",
  token: string = "",
): { reader: ReadableStreamDefaultReader<Uint8Array>; abort: () => void } {
  const controller = new AbortController();

  const body = JSON.stringify({
    question,
    conversation_id: conversationId || null,
    workspace_id: workspaceId,
  });

  const responsePromise = fetch(`${API_BASE}/api/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body,
    signal: controller.signal,
    credentials: "omit",
  });

  const stream = new ReadableStream({
    async start(controller) {
      try {
        const response = await responsePromise;
        if (!response.ok || !response.body) {
          controller.error(new Error(`HTTP ${response.status}`));
          return;
        }
        const reader = response.body.getReader();
        const pump = async () => {
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              controller.close();
              break;
            }
            controller.enqueue(value);
          }
        };
        await pump();
      } catch (err) {
        controller.error(err);
      }
    },
  });

  return {
    reader: stream.getReader(),
    abort: () => controller.abort(),
  };
}

/**
 * Get the auth token from localStorage or cookie.
 */
function getAuthToken(): string {
  if (typeof window === "undefined") return "";
  // Try localStorage first
  const token = localStorage.getItem("aria_access_token");
  if (token) return token;
  // Fallback: read from cookie
  const match = document.cookie.match(/(?:^|;\s*)aria_token=([^;]*)/);
  return match ? match[1] : "";
}

/**
 * Fetch conversation list from the backend.
 */
export async function fetchConversations(tokenOverride?: string): Promise<
  { id: string; title: string; message_count: number; created_at: string; updated_at: string }[]
> {
  const token = tokenOverride || getAuthToken();
  const url = `${API_BASE}/api/conversations`;

  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    credentials: "omit", // Using token in header, no need for cookies/credentials
  });
  if (!res.ok) throw new Error(`Failed to fetch conversations: ${res.status}`);
  return res.json();
}

/**
 * Fetch a single conversation with full messages.
 */
export async function fetchConversation(conversationId: string, tokenOverride?: string) {
  const token = tokenOverride || getAuthToken();
  const res = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    credentials: "omit",
  });
  if (!res.ok) throw new Error(`Failed to fetch conversation: ${res.status}`);
  return res.json();
}

/**
 * Get the run status for a conversation: "running" | "complete" | "error" | null.
 * Used on load to decide whether to resume the live stream or render history.
 */
export async function getRunStatus(
  conversationId: string,
  tokenOverride?: string,
): Promise<{ status: string | null }> {
  const token = tokenOverride || getAuthToken();
  const res = await fetch(`${API_BASE}/api/query/${conversationId}/status`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: "omit",
  });
  if (!res.ok) return { status: null };
  return res.json();
}

/**
 * Re-attach to an in-flight run's SSE stream (GET). Mirrors streamQuery's
 * reader/abort contract so the same SSE-consume loop can drive it.
 */
export function streamResume(
  conversationId: string,
  token: string = "",
): { reader: ReadableStreamDefaultReader<Uint8Array>; abort: () => void } {
  const controller = new AbortController();
  const responsePromise = fetch(`${API_BASE}/api/query/${conversationId}/stream`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
    signal: controller.signal,
    credentials: "omit",
  });

  const stream = new ReadableStream({
    async start(controller) {
      try {
        const response = await responsePromise;
        if (!response.ok || !response.body) {
          controller.error(new Error(`HTTP ${response.status}`));
          return;
        }
        const reader = response.body.getReader();
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            controller.close();
            break;
          }
          controller.enqueue(value);
        }
      } catch (err) {
        controller.error(err);
      }
    },
  });

  return { reader: stream.getReader(), abort: () => controller.abort() };
}

/**
 * Delete a conversation.
 */
export async function deleteConversation(conversationId: string, tokenOverride?: string): Promise<void> {
  const token = tokenOverride || getAuthToken();
  const res = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    credentials: "omit",
  });
  if (!res.ok) throw new Error(`Failed to delete conversation: ${res.status}`);
}

/**
 * Fetch agent memory entries for the admin's workspace/user (admin only).
 *
 * Hits the FastAPI backend at ${API_BASE} — NOT a relative path. A relative
 * "/api/admin/memory" resolves to the Next.js dev server (which has no such
 * route) and returns its HTML 404 page, breaking JSON.parse with
 * "Unexpected token '<'". The backend mounts this router at /api/admin/memory.
 */
export async function fetchAdminMemory(token: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/admin/memory`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: "omit",
  });
  if (!res.ok) throw new Error(`Failed to fetch admin memory: ${res.status}`);
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

/**
 * List teams in the admin's workspace for the dashboard filter picker.
 *
 * Admin-only on the backend (`GET /api/admin/teams`); a non-OK response
 * (e.g. 403 for non-admins) resolves to [] so the filter UI simply stays
 * hidden rather than throwing.
 */
export async function listAdminTeams(token: string): Promise<PickerItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/admin/teams`, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: "omit",
    });
    if (!res.ok) return [];
    const data = await res.json();
    if (!Array.isArray(data)) return [];
    return data.map((t: any) => ({ id: t.id, name: t.name }));
  } catch {
    return [];
  }
}

/**
 * List users in the admin's workspace for the dashboard filter picker.
 *
 * Admin-only on the backend (`GET /api/admin/users`); a non-OK response
 * resolves to [] (see {@link listAdminTeams}).
 */
export async function listAdminUsers(token: string): Promise<PickerItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/admin/users`, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: "omit",
    });
    if (!res.ok) return [];
    const data = await res.json();
    if (!Array.isArray(data)) return [];
    return data.map((u: any) => ({
      id: u.id,
      name: u.display_name || u.email,
      teamId: u.team_id ?? null,
    }));
  } catch {
    return [];
  }
}

export interface VaultTable {
  name: string;
  description?: string;
  columns?: any[];
  relationships?: any[];
  metadata?: Record<string, any>;
}

export async function fetchVaultTables(workspaceId: string, tokenOverride?: string): Promise<VaultTable[]> {
  const token = tokenOverride || getAuthToken();
  const res = await fetch(`${API_BASE}/api/workspaces/vault/tables?workspace_id=${workspaceId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    if (res.status === 404) return []; // No vault tables
    throw new Error(`Failed to fetch vault tables: ${res.status}`);
  }
  return res.json();
}

export async function fetchVaultTableDetails(tableName: string, workspaceId: string, tokenOverride?: string): Promise<VaultTable> {
  const token = tokenOverride || getAuthToken();
  const res = await fetch(`${API_BASE}/api/workspaces/vault/tables/${tableName}?workspace_id=${workspaceId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch table details: ${res.status}`);
  }
  return res.json();
}

export async function fetchWorkspaceSuggestions(workspaceId: string, tokenOverride?: string): Promise<string[]> {
  const token = tokenOverride || (typeof window !== "undefined" ? localStorage.getItem("token") : null);
  const res = await fetch(`${API_BASE}/api/workspaces/${workspaceId}/suggestions`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) {
    return [
      "Show monthly revenue by region",
      "Top 10 customers by volume",
      "Daily active users trend"
    ];
  }
  return res.json();
}

// ── Saved queries (TIER 2 item 14) ──────────────────────────────────────────

export async function saveQuery(
  question: string,
  sql: string,
  name?: string,
  tokenOverride?: string,
): Promise<SavedQuery> {
  const token = tokenOverride || getAuthToken();
  const res = await fetch(`${API_BASE}/api/saved-queries`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    credentials: "omit",
    body: JSON.stringify({ question, sql, name }),
  });
  if (!res.ok) throw new Error(`Failed to save query: ${res.status}`);
  return res.json();
}

export async function listSavedQueries(tokenOverride?: string): Promise<SavedQuery[]> {
  const token = tokenOverride || getAuthToken();
  const res = await fetch(`${API_BASE}/api/saved-queries`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: "omit",
  });
  if (!res.ok) throw new Error(`Failed to list saved queries: ${res.status}`);
  const data = await res.json();
  return data.saved_queries ?? [];
}

export async function deleteSavedQuery(id: string, tokenOverride?: string): Promise<void> {
  const token = tokenOverride || getAuthToken();
  const res = await fetch(`${API_BASE}/api/saved-queries/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
    credentials: "omit",
  });
  if (!res.ok && res.status !== 404) {
    throw new Error(`Failed to delete saved query: ${res.status}`);
  }
}

// ── Massive-export (Phase 4: inline chat delivery) ──────────────────────────

export interface ExportStatus {
  id: string;
  status: "queued" | "running" | "success" | "error";
  row_count: number | null;
  truncated: boolean;
  total_estimate: number | null;
  error: string | null;
  download_ready: boolean;
}

/**
 * Poll the status of a background CSV export job created by the backend's
 * `export` SSE event. Mirrors {@link getRunStatus}'s auth/credentials shape.
 */
export async function getExportStatus(
  jobId: string,
  tokenOverride?: string,
): Promise<ExportStatus | null> {
  const token = tokenOverride || getAuthToken();
  const res = await fetch(`${API_BASE}/api/exports/${jobId}`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: "omit",
  });
  if (!res.ok) return null;
  return res.json();
}

export interface ExportListItem {
  id: string;
  status: "queued" | "running" | "success" | "error";
  question: string | null;
  row_count: number | null;
  truncated: boolean;
  total_estimate: number | null;
  error: string | null;
  created_at: string | null;
  completed_at: string | null;
  download_ready: boolean;
}

/**
 * List the caller's recent export jobs (workspace-scoped, newest first).
 * Mirrors {@link getExportStatus}'s auth/credentials shape.
 */
export async function listExports(tokenOverride?: string): Promise<ExportListItem[]> {
  const token = tokenOverride || getAuthToken();
  const res = await fetch(`${API_BASE}/api/exports`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: "omit",
  });
  if (!res.ok) return [];
  return res.json();
}

/**
 * Fetch the CSV with auth and trigger a browser download. A plain `<a href>`
 * can't be used here because the download endpoint requires Bearer auth.
 */
export async function downloadExport(
  jobId: string,
  filename: string,
  tokenOverride?: string,
): Promise<void> {
  const token = tokenOverride || getAuthToken();
  const res = await fetch(`${API_BASE}/api/exports/${jobId}/download`, {
    headers: { Authorization: `Bearer ${token}` },
    credentials: "omit",
  });
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
