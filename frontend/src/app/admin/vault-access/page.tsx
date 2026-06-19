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
  
  // Real DB Teams
  const [teams, setTeams] = useState<any[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string>("default");
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Current working state for the selected team
  const [allowedTables, setAllowedTables] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (status === "unauthenticated") router.push("/api/auth/signin");
  }, [status, router]);

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
          const defaultPolicy = data.find((p: any) => p.team_id === "default");
          if (defaultPolicy) {
            setAllowedTables(new Set(defaultPolicy.allowed_tables));
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
    const policy = policies.find((p) => p.team_id === selectedTeam);
    setAllowedTables(new Set(policy?.allowed_tables || []));
  }, [selectedTeam, policies]);

  const handleToggleTable = (tableName: string) => {
    const next = new Set(allowedTables);
    const existing = Array.from(next).find(t => t.toLowerCase() === tableName.toLowerCase());
    if (existing) {
      next.delete(existing);
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
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          allowed_tables: Array.from(allowedTables),
        }),
      });

      if (res.ok) {
        // Update local policies state
        const updatedPolicy = await res.json();
        setPolicies((prev) => {
          const exists = prev.find((p) => p.team_id === selectedTeam);
          if (exists) {
            return prev.map((p) =>
              p.team_id === selectedTeam
                ? { ...p, allowed_tables: updatedPolicy.allowed_tables }
                : p
            );
          }
          return [
            ...prev,
            { id: "temp", team_id: selectedTeam, allowed_tables: updatedPolicy.allowed_tables },
          ];
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
          <p className="text-gray-500 mt-1">
            Configure which tables are visible to each team (App-Level RLS).
          </p>
        </div>
        <Button
          onClick={handleSave}
          disabled={loading || saving}
          className="bg-blue-600 hover:bg-blue-700"
        >
          <Save className={`w-4 h-4 mr-2 ${saving ? "animate-pulse" : ""}`} />
          {saving ? "Saving..." : "Save Policy"}
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
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading tables...</div>
            ) : tables.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No tables found in the vault.
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {tables.map((table) => (
                  <label
                    key={table.table_name}
                    className="flex items-start gap-4 p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <Checkbox
                      className="mt-1"
                      checked={Array.from(allowedTables).some(t => t.toLowerCase() === table.table_name.toLowerCase())}
                      onCheckedChange={() => handleToggleTable(table.table_name)}
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{table.table_name}</p>
                      <p className="text-sm text-gray-500 mt-0.5 line-clamp-1">
                        {table.description || "No description"}
                      </p>
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
