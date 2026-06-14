"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Activity, Edit2, Plus, Save, Trash2, Coins, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type TokenQuota = {
  id: string;
  customer_id: string;
  team_id: string | null;
  user_id: string | null;
  period: string;
  token_limit: number;
  is_active: boolean;
};

type TokenUsage = {
  id: string;
  user_id: string;
  usage_date: string;
  tokens_used: number;
  model: string;
};

export default function TokenManagementPage() {
  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const router = useRouter();

  const [quotas, setQuotas] = useState<TokenQuota[]>([]);
  const [usage, setUsage] = useState<TokenUsage[]>([]);
  const [loading, setLoading] = useState(true);

  // Users and Teams for selection/mapping
  const [teams, setTeams] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);

  // Dialog / Form states
  const [editingQuota, setEditingQuota] = useState<TokenQuota | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  
  // New quota form
  const [newQuotaScope, setNewQuotaScope] = useState<"customer" | "team" | "user">("customer");
  const [newQuotaTargetId, setNewQuotaTargetId] = useState<string>("");
  const [newQuotaLimit, setNewQuotaLimit] = useState<number>(1000000);

  useEffect(() => {
    if (status === "unauthenticated") router.push("/api/auth/signin");
  }, [status, router]);

  useEffect(() => {
    if (token) {
      fetchData();
    }
  }, [token]);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch Quotas
      const qRes = await fetch(`${API_BASE}/api/admin/tokens/quotas`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (qRes.ok) setQuotas(await qRes.json());

      // Fetch Usage
      const uRes = await fetch(`${API_BASE}/api/admin/tokens/usage`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (uRes.ok) setUsage(await uRes.json());

      // Fetch Teams & Users for mapping
      const tRes = await fetch(`${API_BASE}/api/admin/teams`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (tRes.ok) setTeams(await tRes.json());

      const userRes = await fetch(`${API_BASE}/api/admin/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (userRes.ok) setUsers(await userRes.json());
      
    } catch (err) {
      console.error("Failed fetching data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateQuota = async () => {
    if (!token) return;
    try {
      const payload: any = {
        period: "daily",
        token_limit: newQuotaLimit,
        is_active: true
      };

      if (newQuotaScope === "team") payload.team_id = newQuotaTargetId;
      if (newQuotaScope === "user") payload.user_id = newQuotaTargetId;

      const res = await fetch(`${API_BASE}/api/admin/tokens/quotas`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setIsCreating(false);
        fetchData();
      } else {
        alert("Failed to create quota. It may already exist for this scope.");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpdateQuota = async (quotaId: string, limit: number, active: boolean) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/api/admin/tokens/quotas/${quotaId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ token_limit: limit, is_active: active }),
      });
      if (res.ok) {
        setEditingQuota(null);
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteQuota = async (quotaId: string) => {
    if (!confirm("Delete this quota?")) return;
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/api/admin/tokens/quotas/${quotaId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const getScopeName = (q: TokenQuota) => {
    if (q.user_id) {
      const user = users.find(u => u.id === q.user_id);
      return `User: ${user?.display_name || user?.email || q.user_id}`;
    }
    if (q.team_id) {
      const team = teams.find(t => t.id === q.team_id);
      return `Team: ${team?.name || q.team_id}`;
    }
    return "Workspace Default";
  };

  const getUserName = (userId: string) => {
    const user = users.find(u => u.id === userId);
    return user?.display_name || user?.email || userId;
  };

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Coins className="w-6 h-6 text-blue-600" />
          Token Quotas & Usage
        </h1>
        <p className="text-gray-500 mt-1">
          Manage AI token limits for the workspace, teams, and users.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Quotas Section */}
        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between border-b border-gray-100 bg-gray-50/50 pb-4">
            <div>
              <CardTitle className="text-lg">Configured Quotas</CardTitle>
              <CardDescription>Daily limits applied in order of specificity</CardDescription>
            </div>
            <Button onClick={() => setIsCreating(!isCreating)} size="sm">
              <Plus className="w-4 h-4 mr-1" /> Add Quota
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            {isCreating && (
              <div className="p-4 bg-blue-50/50 border-b border-blue-100 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium">Scope Level</label>
                    <select
                      className="w-full mt-1 border border-gray-300 rounded-md p-2 text-sm"
                      value={newQuotaScope}
                      onChange={(e) => setNewQuotaScope(e.target.value as any)}
                    >
                      <option value="customer">Workspace Default</option>
                      <option value="team">Team Specific</option>
                      <option value="user">User Specific</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Target</label>
                    {newQuotaScope === "customer" ? (
                      <div className="mt-1 p-2 text-sm bg-gray-100 rounded-md text-gray-500">All users without a specific limit</div>
                    ) : newQuotaScope === "team" ? (
                      <select
                        className="w-full mt-1 border border-gray-300 rounded-md p-2 text-sm"
                        value={newQuotaTargetId}
                        onChange={(e) => setNewQuotaTargetId(e.target.value)}
                      >
                        <option value="">-- Select Team --</option>
                        {teams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                      </select>
                    ) : (
                      <select
                        className="w-full mt-1 border border-gray-300 rounded-md p-2 text-sm"
                        value={newQuotaTargetId}
                        onChange={(e) => setNewQuotaTargetId(e.target.value)}
                      >
                        <option value="">-- Select User --</option>
                        {users.map(u => <option key={u.id} value={u.id}>{u.display_name} ({u.email})</option>)}
                      </select>
                    )}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium">Daily Token Limit</label>
                  <Input 
                    type="number" 
                    className="mt-1"
                    value={newQuotaLimit}
                    onChange={(e) => setNewQuotaLimit(parseInt(e.target.value))}
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" onClick={() => setIsCreating(false)}>Cancel</Button>
                  <Button onClick={handleCreateQuota}>Save Quota</Button>
                </div>
              </div>
            )}

            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading quotas...</div>
            ) : quotas.length === 0 ? (
              <div className="p-8 text-center text-gray-500 flex flex-col items-center">
                <AlertCircle className="w-8 h-8 text-yellow-500 mb-2" />
                <p>No quotas configured.</p>
                <p className="text-sm">Default system limits will apply.</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {quotas.map(quota => (
                  <div key={quota.id} className="p-4 flex items-center justify-between hover:bg-gray-50">
                    {editingQuota?.id === quota.id ? (
                      <div className="flex-1 flex items-center gap-4">
                        <div className="w-1/2">
                          <span className="text-sm font-medium text-gray-700">{getScopeName(quota)}</span>
                        </div>
                        <Input 
                          type="number"
                          className="w-32 h-8 text-sm"
                          value={editingQuota.token_limit}
                          onChange={(e) => setEditingQuota({...editingQuota, token_limit: parseInt(e.target.value)})}
                        />
                        <div className="flex items-center gap-1">
                          <Button size="sm" variant="ghost" onClick={() => handleUpdateQuota(quota.id, editingQuota.token_limit, quota.is_active)}>
                            <Save className="w-4 h-4 text-green-600" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setEditingQuota(null)}>Cancel</Button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div>
                          <p className="font-medium text-gray-900">{getScopeName(quota)}</p>
                          <p className="text-sm text-gray-500">{quota.token_limit.toLocaleString()} tokens / day</p>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" variant="ghost" onClick={() => setEditingQuota(quota)}>
                            <Edit2 className="w-4 h-4 text-gray-500" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => handleDeleteQuota(quota.id)}>
                            <Trash2 className="w-4 h-4 text-red-500" />
                          </Button>
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Usage Section */}
        <Card className="shadow-sm">
          <CardHeader className="border-b border-gray-100 bg-gray-50/50 pb-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="w-5 h-5 text-gray-500" />
              Recent Usage History
            </CardTitle>
            <CardDescription>Daily aggregates of token consumption</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading usage...</div>
            ) : usage.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No usage recorded yet.</div>
            ) : (
              <div className="divide-y divide-gray-100">
                {usage.map(u => (
                  <div key={u.id} className="p-4 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{getUserName(u.user_id)}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs bg-gray-100 px-2 py-0.5 rounded text-gray-600 font-mono">
                          {u.usage_date}
                        </span>
                        <span className="text-xs text-gray-500">{u.model}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-blue-600">{u.tokens_used.toLocaleString()}</p>
                      <p className="text-xs text-gray-500">tokens</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}