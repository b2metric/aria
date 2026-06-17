"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Trash2, Brain, Users, Database, Filter, Sparkles, Clock } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type MemoryType = "all" | "user" | "team" | "cache";

interface Memory {
  id: string | null;
  entity_id: string;
  content: string;
  type: "user" | "team" | "cache";
  created_at: string | null;
  metadata: Record<string, unknown> | null;
  expires_at?: string | null;
}

interface MemoryStats {
  total: number;
  by_type: { user: number; team: number; cache: number };
  expiring_soon: number;
  recent_7d: number;
}

export default function MemoryManagerPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken;
  
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<MemoryType>("all");
  const [deleting, setDeleting] = useState<string | null>(null);
  const [cleaning, setCleaning] = useState(false);
  const [cleanupResult, setCleanupResult] = useState<{ cache: number; user: number } | null>(null);
  const [editingTTL, setEditingTTL] = useState<string | null>(null);
  const [ttlValue, setTtlValue] = useState<string>("");
  const [stats, setStats] = useState<MemoryStats | null>(null);

  // Pagination state
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const limit = 50;

  useEffect(() => {
    if (token) {
      fetchMemories();
      fetchStats();
    }
  }, [token, filter, page]);

  const fetchMemories = async () => {
    try {
      setLoading(true);
      const res = await fetch(
        `${API_BASE}/api/admin/memory?memory_type=${filter}&page=${page}&limit=${limit}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setMemories(data.items || []);
        setTotalPages(data.total_pages || 1);
        setTotalItems(data.total || 0);
      }
    } catch (err) {
      console.error("Failed to fetch memories", err);
    } finally {
      setLoading(false);
    }
  };

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

  const handleDelete = async (memoryId: string) => {
    if (!confirm("Are you sure you want to delete this memory entry?")) {
      return;
    }
    
    setDeleting(memoryId);
    try {
      const res = await fetch(`${API_BASE}/api/admin/memory/${memoryId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (res.ok) {
        setMemories(memories.filter((m) => m.id !== memoryId));
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || "Failed to delete"}`);
      }
    } catch (err) {
      console.error("Failed to delete memory", err);
    } finally {
      setDeleting(null);
    }
  };

  const handleCleanup = async () => {
    if (!confirm("This will delete expired memories:\n- Query cache older than 7 days\n- User preferences older than 90 days\n\nTeam conventions are never deleted.\n\nContinue?")) {
      return;
    }
    
    setCleaning(true);
    setCleanupResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/admin/memory/cleanup`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (res.ok) {
        const data = await res.json();
        setCleanupResult(data.deleted);
        // Refresh the list
        fetchMemories();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || "Cleanup failed"}`);
      }
    } catch (err) {
      console.error("Failed to cleanup memories", err);
    } finally {
      setCleaning(false);
    }
  };

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
          setMemories(memories.map((m) =>
            m.id === memoryId ? { ...m, expires_at: data.expires_at } : m
          ));
        }
        setEditingTTL(null);
        setTtlValue("");
        fetchStats();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || "Failed to update TTL"}`);
      }
    } catch (err) {
      console.error("Failed to update TTL", err);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "user":
        return <Brain className="w-4 h-4 text-purple-500" />;
      case "team":
        return <Users className="w-4 h-4 text-blue-500" />;
      case "cache":
        return <Database className="w-4 h-4 text-green-500" />;
      default:
        return null;
    }
  };

  const getTypeBadge = (type: string) => {
    const styles: Record<string, string> = {
      user: "bg-purple-50 text-purple-700 border-purple-200",
      team: "bg-blue-50 text-blue-700 border-blue-200",
      cache: "bg-green-50 text-green-700 border-green-200",
    };
    return styles[type] || "bg-gray-50 text-gray-700 border-gray-200";
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-2">
          <Brain className="w-6 h-6 text-blue-600" />
          Agent Memory
        </h1>
        <p className="text-gray-500">
          View and manage Qdrant/Mem0 memory entries — user preferences, team conventions, and query cache.
        </p>
      </div>

      {/* Stats Cards */}
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

      {/* Filter + Cleanup */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Filter className="w-5 h-5 text-gray-400" />
          <div className="flex gap-2">
            {(["all", "user", "team", "cache"] as MemoryType[]).map((type) => (
              <button
                key={type}
                onClick={() => { setFilter(type); setPage(1); }}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-all ${
                  filter === type
                    ? "bg-blue-50 text-blue-700 border-blue-200"
                    : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                }`}
              >
                {type === "all" ? "All" : type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
        </div>
        
        <button
          onClick={handleCleanup}
          disabled={cleaning}
          className={`px-4 py-2 text-sm font-medium rounded-lg border transition-all flex items-center gap-2 ${
            cleaning
              ? "bg-gray-100 text-gray-400 cursor-not-allowed border-gray-200"
              : "bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100"
          }`}
        >
          <Sparkles className="w-4 h-4" />
          {cleaning ? "Cleaning..." : "Cleanup Expired"}
        </button>
      </div>

      {/* Cleanup Result */}
      {cleanupResult && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
          Cleanup complete: {cleanupResult.cache} cache entries deleted
          {cleanupResult.user > 0 && `, ${cleanupResult.user} user entries deleted`}
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="animate-pulse flex space-x-4">
          <div className="flex-1 space-y-4 py-1">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            </div>
          </div>
        </div>
      ) : memories.length === 0 ? (
        <div className="p-8 text-center bg-white border border-dashed border-gray-300 rounded-xl text-gray-500">
          <Brain className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p>No memory entries found.</p>
          <p className="text-sm mt-1">
            {filter !== "all" ? `No ${filter} memories. Try selecting "All".` : "Memories will appear as users interact with the system."}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="w-full text-left text-sm text-gray-700">
            <thead className="bg-gray-50 text-gray-500 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 font-medium w-24">Type</th>
                <th className="px-6 py-4 font-medium">Content</th>
                <th className="px-6 py-4 font-medium w-32">Created</th>
                <th className="px-6 py-4 font-medium w-28">Expires</th>
                <th className="px-6 py-4 font-medium text-right w-20">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {memories.map((mem, idx) => (
                <tr key={mem.id || idx} className="hover:bg-gray-50 transition-colors group">
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded-md border ${getTypeBadge(mem.type)}`}>
                      {getTypeIcon(mem.type)}
                      {mem.type}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <p className="line-clamp-2">{mem.content}</p>
                    {mem.metadata && Object.keys(mem.metadata).length > 0 && (
                      <p className="text-xs text-gray-400 mt-1 truncate">
                        {JSON.stringify(mem.metadata).slice(0, 80)}...
                      </p>
                    )}
                  </td>
                  <td className="px-6 py-4 text-gray-500 text-xs">
                    {mem.created_at
                      ? new Date(mem.created_at).toLocaleDateString()
                      : "N/A"}
                  </td>
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
                  <td className="px-6 py-4 text-right">
                    {mem.id && (
                      <button
                        onClick={() => handleDelete(mem.id!)}
                        disabled={deleting === mem.id}
                        className={`p-2 rounded-lg transition-all ${
                          deleting === mem.id
                            ? "text-gray-300 cursor-not-allowed"
                            : "text-gray-400 hover:text-red-600 hover:bg-red-50 opacity-0 group-hover:opacity-100"
                        }`}
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      {/* Stats + Retention Info */}
      {!loading && memories.length > 0 && (
        <div className="mt-4 flex flex-col gap-4 text-sm text-gray-500">
          <div className="flex justify-between items-center bg-white p-3 rounded-lg border border-gray-200">
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 bg-gray-100 rounded disabled:opacity-50 hover:bg-gray-200"
              >
                Previous
              </button>
              <span className="py-1 px-2">Page {page} of {totalPages}</span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 bg-gray-100 rounded disabled:opacity-50 hover:bg-gray-200"
              >
                Next
              </button>
            </div>
            <span>Total Items: {totalItems}</span>
          </div>
          <div className="flex justify-between">
            <div className="flex gap-4">
              <span>Displaying {memories.length} items</span>
            </div>
            <div className="text-xs text-gray-400">
              Retention: Cache=7d, User=90d, Team=∞
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
