"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import {
  Lock,
  Save,
  Database,
  Users,
  AlertTriangle,
  Filter,
  EyeOff,
  Search,
  RefreshCw,
  CheckCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type VaultTable = {
  table_name: string;
  description: string;
};

type RowFilters = Record<string, string>;
// Per-table denied (masked) column names (App-Level CLS). Keyed by table name.
type DenyColumns = Record<string, string[]>;

type VaultPolicy = {
  id: string;
  team_id: string;
  allowed_tables: string[];
  row_filters?: RowFilters | null;
  deny_columns?: DenyColumns | null;
};

export default function VaultAccessPage() {
  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const router = useRouter();

  const [tables, setTables] = useState<VaultTable[]>([]);
  const [policies, setPolicies] = useState<VaultPolicy[]>([]);
  
  // Real DB Teams
  const [teams, setTeams] = useState<any[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string>("default");
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Current working state for the selected team
  const [allowedTables, setAllowedTables] = useState<Set<string>>(new Set());
  // Per-table row-filter SQL predicates (App-Level RLS). Keyed by table name.
  const [rowFilters, setRowFilters] = useState<RowFilters>({});
  // Per-table denied (masked) columns (App-Level CLS). Keyed by table name.
  const [denyColumns, setDenyColumns] = useState<DenyColumns>({});

  // Search / filter for the (potentially 500-row) table list.
  const [search, setSearch] = useState("");
  const [filterMode, setFilterMode] = useState<"all" | "selected" | "unselected">("all");

  // Scoped re-sync of the currently-selected tables.
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<{ ok: boolean; msg: string } | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") router.push("/api/auth/signin");
  }, [status, router]);

  const fetchTables = useCallback(async () => {
    if (!token) return;
    const res = await fetch(`${API_BASE}/api/workspaces/vault/tables?workspace_id=default`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setTables(await res.json());
  }, [token]);

  useEffect(() => {
    const fetchData = async () => {
      if (!token) return;
      try {
        setLoading(true);
        // 1. Fetch tables
        const tablesRes = await fetch(`${API_BASE}/api/workspaces/vault/tables?workspace_id=default`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (tablesRes.ok) {
          setTables(await tablesRes.json());
        }

        // 2. Fetch policies
        const policiesRes = await fetch(`${API_BASE}/api/admin/vault-policies`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (policiesRes.ok) {
          const data = await policiesRes.json();
          setPolicies(data);

          // Initialize state for selected team
          const defaultPolicy = data.find((p: VaultPolicy) => p.team_id === "default");
          if (defaultPolicy) {
            setAllowedTables(new Set(defaultPolicy.allowed_tables));
            setRowFilters({ ...(defaultPolicy.row_filters ?? {}) });
            setDenyColumns({ ...(defaultPolicy.deny_columns ?? {}) });
          }
        }

        // 3. Fetch real teams from the DB
        const teamsRes = await fetch(`${API_BASE}/api/admin/teams`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (teamsRes.ok) {
          const teamsData = await teamsRes.json();
          setTeams(Array.isArray(teamsData) ? teamsData : []);
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
    void (async () => {
      const policy = policies.find((p) => p.team_id === selectedTeam);
      setAllowedTables(new Set(policy?.allowed_tables || []));
      setRowFilters({ ...(policy?.row_filters ?? {}) });
      setDenyColumns({ ...(policy?.deny_columns ?? {}) });
      setSaveError(null);
    })();
  }, [selectedTeam, policies]);

  const handleToggleTable = (tableName: string) => {
    const next = new Set(allowedTables);
    const existing = Array.from(next).find(t => t.toLowerCase() === tableName.toLowerCase());
    if (existing) {
      next.delete(existing);
      // Drop any row filter for a table that is no longer allowed.
      setRowFilters((prev) => {
        if (!(existing in prev)) return prev;
        const { [existing]: _removed, ...rest } = prev;
        return rest;
      });
      // Drop any denied-columns entry for a table that is no longer allowed.
      setDenyColumns((prev) => {
        if (!(existing in prev)) return prev;
        const { [existing]: _removed, ...rest } = prev;
        return rest;
      });
    } else {
      next.add(tableName);
    }
    setAllowedTables(next);
  };

  const handleRowFilterChange = (tableName: string, predicate: string) => {
    setRowFilters((prev) => ({ ...prev, [tableName]: predicate }));
  };

  const handleDenyColumnsChange = (tableName: string, raw: string) => {
    // Parse the comma-separated input into a trimmed, non-empty column list.
    const columns = raw
      .split(",")
      .map((c) => c.trim())
      .filter((c) => c.length > 0);
    setDenyColumns((prev) => ({ ...prev, [tableName]: columns }));
  };

  const handleSave = async () => {
    if (!token) return;
    try {
      setSaving(true);
      setSaveError(null);

      const allowed = Array.from(allowedTables);
      // Only persist row filters for allowed tables with a non-empty predicate.
      // Omitting a table (empty/whitespace predicate) means "no restriction".
      const filtersPayload: RowFilters = {};
      for (const table of allowed) {
        const predicate = rowFilters[table]?.trim();
        if (predicate) filtersPayload[table] = predicate;
      }

      // Only persist denied columns for allowed tables with a non-empty list.
      // Omitting a table means "no columns masked".
      const denyPayload: DenyColumns = {};
      for (const table of allowed) {
        const columns = denyColumns[table];
        if (columns && columns.length > 0) denyPayload[table] = columns;
      }

      const res = await fetch(`${API_BASE}/api/admin/vault-policies/${selectedTeam}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          allowed_tables: allowed,
          row_filters: filtersPayload,
          deny_columns: denyPayload,
        }),
      });

      if (res.ok) {
        // Update local policies state
        const updatedPolicy = await res.json();
        const nextRowFilters: RowFilters = updatedPolicy.row_filters ?? {};
        const nextDenyColumns: DenyColumns = updatedPolicy.deny_columns ?? {};
        setRowFilters({ ...nextRowFilters });
        setDenyColumns({ ...nextDenyColumns });
        setPolicies((prev) => {
          const exists = prev.find((p) => p.team_id === selectedTeam);
          if (exists) {
            return prev.map((p) =>
              p.team_id === selectedTeam
                ? {
                    ...p,
                    allowed_tables: updatedPolicy.allowed_tables,
                    row_filters: nextRowFilters,
                    deny_columns: nextDenyColumns,
                  }
                : p
            );
          }
          return [
            ...prev,
            {
              id: "temp",
              team_id: selectedTeam,
              allowed_tables: updatedPolicy.allowed_tables,
              row_filters: nextRowFilters,
              deny_columns: nextDenyColumns,
            },
          ];
        });
      } else {
        // Surface backend validation errors (e.g. malformed row-filter predicate → 400).
        let detail = `Failed to save policy (HTTP ${res.status})`;
        try {
          const errBody = await res.json();
          if (typeof errBody?.detail === "string") detail = errBody.detail;
        } catch {
          // Response had no JSON body; keep the generic message.
        }
        setSaveError(detail);
      }
    } catch (err) {
      console.error("Failed to save policy", err);
      setSaveError("Failed to save policy. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const isSelected = (name: string) =>
    Array.from(allowedTables).some((t) => t.toLowerCase() === name.toLowerCase());

  const q = search.trim().toLowerCase();
  const visibleTables = tables.filter((t) => {
    const matchesSearch =
      !q ||
      t.table_name.toLowerCase().includes(q) ||
      (t.description ?? "").toLowerCase().includes(q);
    if (!matchesSearch) return false;
    if (filterMode === "all") return true;
    const sel = isSelected(t.table_name);
    return filterMode === "selected" ? sel : !sel;
  });
  const RENDER_CAP = 200;
  const shown = visibleTables.slice(0, RENDER_CAP);

  const handleSelectAllFiltered = () => {
    const next = new Set(allowedTables);
    for (const t of visibleTables) {
      if (!isSelected(t.table_name)) next.add(t.table_name);
    }
    setAllowedTables(next);
  };

  const handleClearFiltered = () => {
    const visibleNames = new Set(visibleTables.map((t) => t.table_name.toLowerCase()));
    setAllowedTables(
      new Set(Array.from(allowedTables).filter((t) => !visibleNames.has(t.toLowerCase()))),
    );
  };

  const handleResyncSelected = async () => {
    if (!token || allowedTables.size === 0) return;
    try {
      setSyncing(true);
      setSyncResult(null);
      const res = await fetch(`${API_BASE}/api/workspaces/vault/sync?workspace_id=default`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ tables: Array.from(allowedTables) }),
      });
      if (res.ok) {
        const data = await res.json();
        const s = data.stats || {};
        setSyncResult({
          ok: true,
          msg: `Synced ${s.scoped_table_count ?? allowedTables.size} table(s) — added ${
            s.added ?? 0
          }, updated ${s.updated ?? 0}, enum updated ${s.enum_updated ?? 0}.`,
        });
        await fetchTables();
      } else {
        let detail = `Re-sync failed (HTTP ${res.status})`;
        try {
          const e = await res.json();
          if (typeof e?.detail === "string") detail = e.detail;
        } catch {
          // no JSON body
        }
        setSyncResult({ ok: false, msg: detail });
      }
    } catch (err) {
      console.error("Re-sync failed", err);
      setSyncResult({ ok: false, msg: "Re-sync failed. Please try again." });
    } finally {
      setSyncing(false);
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
          <p className="text-gray-500 mt-1">
            Control table access, per-table row-level filters, and column masking for each team (App-Level RLS/CLS).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleResyncSelected}
            disabled={syncing || allowedTables.size === 0}
            title="Re-sync only the selected tables (enum sampling scoped to these)"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Syncing..." : `Re-sync selected (${allowedTables.size})`}
          </Button>
          <Button
            onClick={handleSave}
            disabled={loading || saving}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Save className={`w-4 h-4 mr-2 ${saving ? "animate-pulse" : ""}`} />
            {saving ? "Saving..." : "Save Policy"}
          </Button>
        </div>
      </div>

      {syncResult && (
        <div
          role="status"
          className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${
            syncResult.ok
              ? "border-green-200 bg-green-50 text-green-700"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          {syncResult.ok ? (
            <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          )}
          <span className="break-words">{syncResult.msg}</span>
        </div>
      )}

      {saveError && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span className="break-words">{saveError}</span>
        </div>
      )}

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
              className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium ${
                selectedTeam === "default"
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
              onClick={() => setSelectedTeam("default")}
            >
              Default Team
            </button>
            {teams.map((team) => (
              <button
                key={team.id}
                className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium mt-1 ${
                  selectedTeam === team.id
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
                onClick={() => setSelectedTeam(team.id)}
              >
                {team.name}
              </button>
            ))}
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
                  Select the vault tables the{" "}
                  <span className="font-semibold text-gray-900">
                    {selectedTeam === "default" ? "Default" : teams.find(t => t.id === selectedTeam)?.name || selectedTeam}
                  </span>{" "}
                  team can query.
                </CardDescription>
              </div>
              <div className="text-sm font-medium text-gray-500 bg-white px-3 py-1 rounded-full border border-gray-200">
                {allowedTables.size} / {tables.length} Selected
              </div>
            </div>

            {/* Search + filter + bulk-select toolbar (handles 500+ tables) */}
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative w-full sm:max-w-xs">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search tables by name or description…"
                  className="pl-9"
                />
              </div>
              <div className="flex items-center gap-2">
                <div className="flex rounded-md border border-gray-200 bg-white p-0.5 text-xs font-medium">
                  {(["all", "selected", "unselected"] as const).map((m) => (
                    <button
                      key={m}
                      onClick={() => setFilterMode(m)}
                      className={`px-2.5 py-1 rounded ${
                        filterMode === m
                          ? "bg-blue-50 text-blue-700"
                          : "text-gray-600 hover:bg-gray-100"
                      }`}
                    >
                      {m === "all" ? "All" : m === "selected" ? "Selected" : "Unselected"}
                    </button>
                  ))}
                </div>
                <Button variant="outline" size="sm" onClick={handleSelectAllFiltered}>
                  Select all (filtered)
                </Button>
                <Button variant="outline" size="sm" onClick={handleClearFiltered}>
                  Clear filtered
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading tables...</div>
            ) : tables.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No tables found in the vault.
              </div>
            ) : visibleTables.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No tables match your search/filter.
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {shown.map((table) => {
                  const isAllowed = Array.from(allowedTables).some(
                    (t) => t.toLowerCase() === table.table_name.toLowerCase()
                  );
                  return (
                    <div
                      key={table.table_name}
                      className="p-4 hover:bg-gray-50 transition-colors"
                    >
                      <label className="flex items-start gap-4 cursor-pointer">
                        <Checkbox
                          className="mt-1"
                          checked={isAllowed}
                          onCheckedChange={() => handleToggleTable(table.table_name)}
                        />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-900">{table.table_name}</p>
                          <p className="text-sm text-gray-500 mt-0.5 line-clamp-1">
                            {table.description || "No description"}
                          </p>
                        </div>
                      </label>

                      {isAllowed && (
                        <div className="mt-3 ml-8 space-y-2">
                          <div className="flex items-center gap-2">
                            <Filter className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                            <input
                              type="text"
                              value={rowFilters[table.table_name] ?? ""}
                              onChange={(e) =>
                                handleRowFilterChange(table.table_name, e.target.value)
                              }
                              placeholder="e.g. REGION = 'KW'  (optional row filter)"
                              spellCheck={false}
                              className="w-full max-w-md rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm font-mono text-gray-800 placeholder:font-sans placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            />
                          </div>
                          <div className="flex items-center gap-2">
                            <EyeOff className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                            <input
                              type="text"
                              value={(denyColumns[table.table_name] ?? []).join(", ")}
                              onChange={(e) =>
                                handleDenyColumnsChange(table.table_name, e.target.value)
                              }
                              placeholder="e.g. REVENUE, MARGIN  (columns to hide, comma-separated)"
                              spellCheck={false}
                              className="w-full max-w-md rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm font-mono text-gray-800 placeholder:font-sans placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
                {visibleTables.length > RENDER_CAP && (
                  <div className="p-3 text-center text-xs text-gray-500 bg-gray-50/50">
                    Showing {RENDER_CAP} of {visibleTables.length} matches — refine your search to
                    see more.
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
