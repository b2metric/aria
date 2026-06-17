"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import {
  Users,
  Trash2,
  Pencil,
  Plus,
  RefreshCw,
  Building2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ────────────────────────────────────────────────────────────

type Team = {
  id: string;
  name: string;
  customer_id: string;
  created_at: string;
  updated_at: string;
};

type User = {
  id: string;
  email: string;
  display_name: string;
  role: string;
  team_id: string | null;
  customer_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type Tab = "users" | "teams";

// ── Helpers ──────────────────────────────────────────────────────────

function roleBadge(role: string) {
  switch (role) {
    case "admin":
      return (
        <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
          Admin
        </Badge>
      );
    case "member":
      return (
        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
          Member
        </Badge>
      );
    case "viewer":
      return (
        <Badge variant="outline" className="bg-gray-50 text-gray-600 border-gray-200">
          Viewer
        </Badge>
      );
    default:
      return <Badge variant="outline">{role}</Badge>;
  }
}

function roleLabel(role: string): string {
  switch (role) {
    case "admin": return "Admin";
    case "member": return "Member";
    case "viewer": return "Viewer";
    default: return role;
  }
}

// ── Page Component ───────────────────────────────────────────────────

export default function UsersTeamsPage() {
  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<Tab>("users");

  // Teams state
  const [teams, setTeams] = useState<Team[]>([]);
  const [teamsLoading, setTeamsLoading] = useState(true);

  // Users state
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);

  // Create team dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newTeamName, setNewTeamName] = useState("");
  const [creating, setCreating] = useState(false);

  // Edit user dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editRole, setEditRole] = useState("");
  const [editTeamId, setEditTeamId] = useState("");
  const [saving, setSaving] = useState(false);

  // Create user dialog state
  const [createUserDialogOpen, setCreateUserDialogOpen] = useState(false);
  const [newUserName, setNewUserName] = useState("");
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserRole, setNewUserRole] = useState("member");
  const [newUserTeamId, setNewUserTeamId] = useState("");
  const [creatingUser, setCreatingUser] = useState(false);

  // Delete team state
  const [deletingTeamId, setDeletingTeamId] = useState<string | null>(null);

  // ── Auth guard ────────────────────────────────────────────────────

  useEffect(() => {
    if (status === "unauthenticated") router.push("/api/auth/signin");
  }, [status, router]);

  // ── Fetch teams ───────────────────────────────────────────────────

  const fetchTeams = useCallback(async () => {
    if (!token) return;
    try {
      setTeamsLoading(true);
      const res = await fetch(`${API_BASE}/api/admin/teams`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTeams(Array.isArray(data) ? data : []);
      } else {
        console.error("Failed to fetch teams", res.status);
      }
    } catch (err) {
      console.error("Failed to fetch teams", err);
    } finally {
      setTeamsLoading(false);
    }
  }, [token]);

  // ── Fetch users ───────────────────────────────────────────────────

  const fetchUsers = useCallback(async () => {
    if (!token) return;
    try {
      setUsersLoading(true);
      const res = await fetch(`${API_BASE}/api/admin/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(Array.isArray(data) ? data : []);
      } else {
        console.error("Failed to fetch users", res.status);
      }
    } catch (err) {
      console.error("Failed to fetch users", err);
    } finally {
      setUsersLoading(false);
    }
  }, [token]);

  // ── Initial load ──────────────────────────────────────────────────

  useEffect(() => {
    if (token) {
      fetchTeams();
      fetchUsers();
    }
  }, [token, fetchTeams, fetchUsers]);

  // ── Create team ───────────────────────────────────────────────────

  const handleCreateTeam = async () => {
    if (!token || !newTeamName.trim()) return;
    try {
      setCreating(true);
      const res = await fetch(`${API_BASE}/api/admin/teams`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: newTeamName.trim() }),
      });
      if (res.ok) {
        setNewTeamName("");
        setCreateDialogOpen(false);
        await fetchTeams();
      } else {
        console.error("Failed to create team", res.status);
      }
    } catch (err) {
      console.error("Failed to create team", err);
    } finally {
      setCreating(false);
    }
  };

  // ── Delete team ───────────────────────────────────────────────────

  const handleDeleteTeam = async (teamId: string) => {
    if (!token) return;
    try {
      setDeletingTeamId(teamId);
      const res = await fetch(`${API_BASE}/api/admin/teams/${teamId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        await fetchTeams();
        await fetchUsers(); // users may have had this team_id
      } else {
        console.error("Failed to delete team", res.status);
      }
    } catch (err) {
      console.error("Failed to delete team", err);
    } finally {
      setDeletingTeamId(null);
    }
  };

  // ── Open edit user dialog ─────────────────────────────────────────

  const openEditDialog = (user: User) => {
    setEditingUser(user);
    setEditRole(user.role);
    setEditTeamId(user.team_id || "");
    setEditDialogOpen(true);
  };

  // ── Create user ───────────────────────────────────────────────────

  const handleCreateUser = async () => {
    if (!token || !newUserName.trim() || !newUserEmail.trim()) return;
    try {
      setCreatingUser(true);
      const res = await fetch(`${API_BASE}/api/admin/users`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          display_name: newUserName,
          email: newUserEmail,
          role: newUserRole,
          team_id: newUserTeamId || null,
        }),
      });
      if (res.ok) {
        setNewUserName("");
        setNewUserEmail("");
        setNewUserRole("member");
        setNewUserTeamId("");
        setCreateUserDialogOpen(false);
        await fetchUsers();
      } else {
        const errorData = await res.json();
        alert(errorData.detail || "Failed to create user");
        console.error("Failed to create user", res.status, errorData);
      }
    } catch (err) {
      console.error("Failed to create user", err);
    } finally {
      setCreatingUser(false);
    }
  };

  // ── Save user edit ────────────────────────────────────────────────

  const handleSaveUser = async () => {
    if (!token || !editingUser) return;
    try {
      setSaving(true);
      const body: Record<string, any> = { role: editRole };
      if (editTeamId) {
        body.team_id = editTeamId;
      } else {
        body.team_id = null;
      }
      const res = await fetch(`${API_BASE}/api/admin/users/${editingUser.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        setEditDialogOpen(false);
        setEditingUser(null);
        await fetchUsers();
      } else {
        console.error("Failed to update user", res.status);
      }
    } catch (err) {
      console.error("Failed to update user", err);
    } finally {
      setSaving(false);
    }
  };

  // ── Derive team name for display ──────────────────────────────────

  const teamNameById = (teamId: string | null): string => {
    if (!teamId) return "—";
    const team = teams.find((t) => t.id === teamId);
    return team ? team.name : teamId;
  };

  // ── Render ────────────────────────────────────────────────────────

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="w-6 h-6 text-blue-600" />
            Users & Teams
          </h1>
          <p className="text-gray-500 mt-1">
            Manage users and teams in your workspace.
          </p>
        </div>
      </div>

      {/* Tab Toggle */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab("users")}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === "users"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <Users className="w-4 h-4 inline mr-2" />
          Users
        </button>
        <button
          onClick={() => setActiveTab("teams")}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === "teams"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <Building2 className="w-4 h-4 inline mr-2" />
          Teams
        </button>
      </div>

      {/* ── Users Tab ──────────────────────────────────────────────── */}
      {activeTab === "users" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              All Users
            </h2>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={fetchUsers} disabled={usersLoading}>
                <RefreshCw className={`w-4 h-4 mr-1 ${usersLoading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
              <Dialog open={createUserDialogOpen} onOpenChange={setCreateUserDialogOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white">
                    <Plus className="w-4 h-4 mr-1" />
                    Add User
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add New User</DialogTitle>
                    <DialogDescription>
                      Create a new user account for your workspace.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">Name</label>
                      <Input
                        placeholder="John Doe"
                        value={newUserName}
                        onChange={(e) => setNewUserName(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">Email</label>
                      <Input
                        type="email"
                        placeholder="john@example.com"
                        value={newUserEmail}
                        onChange={(e) => setNewUserEmail(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">Role</label>
                      <Select value={newUserRole} onValueChange={setNewUserRole}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a role" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="viewer">Viewer</SelectItem>
                          <SelectItem value="analyst">Analyst</SelectItem>
                          <SelectItem value="team_lead">Team Lead</SelectItem>
                          <SelectItem value="admin">Admin</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">Team Assignment</label>
                      <Select value={newUserTeamId} onValueChange={setNewUserTeamId}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a team (optional)" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">No Team</SelectItem>
                          {teams.map((team) => (
                            <SelectItem key={team.id} value={team.id}>
                              {team.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setCreateUserDialogOpen(false)} disabled={creatingUser}>
                      Cancel
                    </Button>
                    <Button onClick={handleCreateUser} disabled={creatingUser || !newUserName.trim() || !newUserEmail.trim()}>
                      {creatingUser ? "Creating..." : "Create User"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Name</th>
                    <th className="px-6 py-3 font-semibold">Email</th>
                    <th className="px-6 py-3 font-semibold">Role</th>
                    <th className="px-6 py-3 font-semibold">Team</th>
                    <th className="px-6 py-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {usersLoading && users.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                        Loading users...
                      </td>
                    </tr>
                  ) : users.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                        No users found in this workspace.
                      </td>
                    </tr>
                  ) : (
                    users.map((user) => (
                      <tr key={user.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 font-medium text-gray-900">
                          {user.display_name}
                        </td>
                        <td className="px-6 py-4 text-gray-500">{user.email}</td>
                        <td className="px-6 py-4">{roleBadge(user.role)}</td>
                        <td className="px-6 py-4 text-gray-500">
                          {teamNameById(user.team_id)}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openEditDialog(user)}
                          >
                            <Pencil className="w-4 h-4 mr-1" />
                            Edit
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── Teams Tab ──────────────────────────────────────────────── */}
      {activeTab === "teams" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              All Teams
            </h2>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={fetchTeams} disabled={teamsLoading}>
                <RefreshCw className={`w-4 h-4 mr-1 ${teamsLoading ? "animate-spin" : ""}`} />
                Refresh
              </Button>

              <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
                <DialogTrigger asChild>
                  <Button size="sm">
                    <Plus className="w-4 h-4 mr-1" />
                    Create Team
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create New Team</DialogTitle>
                    <DialogDescription>
                      Add a new team to your workspace. You can assign users to this team
                      from the Users tab.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">
                        Team Name
                      </label>
                      <Input
                        placeholder="e.g. Data Engineering"
                        value={newTeamName}
                        onChange={(e) => setNewTeamName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleCreateTeam();
                        }}
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button
                      variant="outline"
                      onClick={() => setCreateDialogOpen(false)}
                      disabled={creating}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleCreateTeam}
                      disabled={creating || !newTeamName.trim()}
                    >
                      {creating ? "Creating..." : "Create Team"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Team Name</th>
                    <th className="px-6 py-3 font-semibold">Created</th>
                    <th className="px-6 py-3 font-semibold">ID</th>
                    <th className="px-6 py-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {teamsLoading && teams.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                        Loading teams...
                      </td>
                    </tr>
                  ) : teams.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                        No teams found. Create your first team above.
                      </td>
                    </tr>
                  ) : (
                    teams.map((team) => (
                      <tr key={team.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 font-medium text-gray-900">
                          {team.name}
                        </td>
                        <td className="px-6 py-4 text-gray-500">
                          {new Date(team.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 font-mono text-xs text-gray-400">
                          {team.id}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            disabled={deletingTeamId === team.id}
                            onClick={() => {
                              if (confirm(`Delete team "${team.name}"? This cannot be undone.`)) {
                                handleDeleteTeam(team.id);
                              }
                            }}
                          >
                            <Trash2 className="w-4 h-4 mr-1" />
                            {deletingTeamId === team.id ? "Deleting..." : "Delete"}
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── Edit User Dialog ────────────────────────────────────────── */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit User</DialogTitle>
            <DialogDescription>
              {editingUser && (
                <>
                  Update role and team assignment for{" "}
                  <span className="font-medium text-gray-900">
                    {editingUser.display_name}
                  </span>
                  {" "}({editingUser.email}).
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          {editingUser && (
            <div className="space-y-4 py-4">
              {/* Role Select */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">Role</label>
                <Select value={editRole} onValueChange={setEditRole}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="member">Member</SelectItem>
                    <SelectItem value="viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Team Select */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">Team</label>
                <Select
                  value={editTeamId}
                  onValueChange={(v) => setEditTeamId(v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="No team" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">No team (unassigned)</SelectItem>
                    {teams.map((team) => (
                      <SelectItem key={team.id} value={team.id}>
                        {team.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setEditDialogOpen(false)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button onClick={handleSaveUser} disabled={saving || !editRole}>
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
