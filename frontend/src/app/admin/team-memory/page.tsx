"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Plus, Trash2, BookOpen, Users } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Team {
  id: string;
  name: string;
}

interface TeamMemory {
  id: string | null;
  content: string;
  team_id: string;
  metadata: Record<string, unknown> | null;
  created_at: string | null;
}

export default function TeamMemoryPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken;
  
  const [memories, setMemories] = useState<TeamMemory[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [teamId, setTeamId] = useState("default");
  const [teams, setTeams] = useState<Team[]>([]);
  const [teamsLoading, setTeamsLoading] = useState(true);

  const fetchTeams = async () => {
    try {
      setTeamsLoading(true);
      const res = await fetch(`${API_BASE}/api/admin/teams`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTeams(data);
        if (data.length > 0 && teamId === "default") {
          setTeamId(data[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to fetch teams", err);
    } finally {
      setTeamsLoading(false);
    }
  };

  const fetchMemories = async () => {
    try {
      setLoading(true);
      const res = await fetch(
        `${API_BASE}/api/admin/team-memory?team_id=${teamId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setMemories(data);
      }
    } catch (err) {
      console.error("Failed to fetch team memories", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      void (async () => { await fetchMemories(); })();
    }
  }, [token, teamId]);

  useEffect(() => {
    if (token) {
      void (async () => { await fetchTeams(); })();
    }
  }, [token]);

  const handleCreate = async () => {
    if (!newContent.trim()) return;
    
    setCreating(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/team-memory`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          content: newContent,
          team_id: teamId,
        }),
      });
      
      if (res.ok) {
        setNewContent("");
        fetchMemories();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || "Failed to create"}`);
      }
    } catch (err) {
      console.error("Failed to create team memory", err);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (memoryId: string) => {
    if (!confirm("Are you sure you want to delete this team convention?")) {
      return;
    }
    
    try {
      const res = await fetch(
        `${API_BASE}/api/admin/team-memory/${memoryId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      
      if (res.ok) {
        fetchMemories();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || "Failed to delete"}`);
      }
    } catch (err) {
      console.error("Failed to delete team memory", err);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-2">
          <Users className="w-6 h-6 text-blue-600" />
          Team Conventions
        </h1>
        <p className="text-gray-500">
          Define business rules and conventions that apply to all team members.
          These definitions help the AI generate more accurate SQL queries.
        </p>
      </div>

      {/* Create New */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Plus className="w-5 h-5 text-blue-600" />
          Add New Convention
        </h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Team
            </label>
            <select
              value={teamId}
              onChange={(e) => setTeamId(e.target.value)}
              disabled={teamsLoading || teams.length === 0}
              className="w-full md:w-48 bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {teamsLoading ? (
                <option>Loading teams...</option>
              ) : teams.length === 0 ? (
                <option value="">No teams available</option>
              ) : (
                teams.map((team) => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))
              )}
            </select>
            {!teamsLoading && teams.length === 0 && (
              <p className="text-sm text-amber-600 mt-1">
                Please create a team in Users &amp; Teams first.
              </p>
            )}
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Business Rule / Definition
            </label>
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="e.g., 'Active subscriber means customer with transaction in last 30 days'"
              className="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
            />
            <p className="text-xs text-gray-500 mt-2">
              Examples: &quot;Revenue should always use TOPUP_AMOUNT column&quot;, &quot;Churn rate = lost subscribers / total * 100&quot;
            </p>
          </div>
          
          <button
            onClick={handleCreate}
            disabled={creating || !newContent.trim()}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
              creating || !newContent.trim()
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700 text-white shadow-sm"
            }`}
          >
            {creating ? "Creating..." : "Add Convention"}
          </button>
        </div>
      </div>

      {/* List */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-gray-500" />
            Current Conventions
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({memories.length})
            </span>
          </h2>
        </div>
        
        {loading ? (
          <div className="p-8 text-center text-gray-500">
            <div className="animate-pulse flex flex-col items-center">
              <div className="h-4 bg-gray-200 rounded w-48 mb-2"></div>
              <div className="h-4 bg-gray-200 rounded w-32"></div>
            </div>
          </div>
        ) : memories.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <BookOpen className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>No team conventions defined yet.</p>
            <p className="text-sm mt-1">Add your first business rule above.</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {memories.map((mem, idx) => (
              <li
                key={mem.id || idx}
                className="px-6 py-4 hover:bg-gray-50 transition-colors group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-900">{mem.content}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                      <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                        {mem.team_id}
                      </span>
                      {mem.created_at && (
                        <span>
                          {new Date(mem.created_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  {mem.id && (
                    <button
                      onClick={() => handleDelete(mem.id!)}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
