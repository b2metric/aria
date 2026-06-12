"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Trash2, Brain, Users, Database, Filter } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type MemoryType = "all" | "user" | "team" | "cache";

interface Memory {
  id: string | null;
  entity_id: string;
  content: string;
  type: "user" | "team" | "cache";
  created_at: string | null;
  metadata: Record<string, unknown> | null;
}

export default function MemoryManagerPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken;
  
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<MemoryType>("all");
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      fetchMemories();
    }
  }, [token, filter]);

  const fetchMemories = async () => {
    try {
      setLoading(true);
      const res = await fetch(
        `${API_BASE}/api/admin/memory?memory_type=${filter}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setMemories(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error("Failed to fetch memories", err);
    } finally {
      setLoading(false);
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

      {/* Filter */}
      <div className="mb-6 flex items-center gap-3">
        <Filter className="w-5 h-5 text-gray-400" />
        <div className="flex gap-2">
          {(["all", "user", "team", "cache"] as MemoryType[]).map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg border transition-all ${
                filter === type
                  ? "bg-blue-50 text-blue-700 border-blue-200"
                  : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
              }`}
            >
              {type === "all" ? "All" : type.charAt(0).toUpperCase() + type.slice(1)}
              {type !== "all" && (
                <span className="ml-1.5 text-xs text-gray-400">
                  ({memories.filter((m) => filter === "all" || m.type === type).length})
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

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
      
      {/* Stats */}
      {!loading && memories.length > 0 && (
        <div className="mt-4 flex gap-4 text-sm text-gray-500">
          <span>Total: {memories.length}</span>
          <span>User: {memories.filter((m) => m.type === "user").length}</span>
          <span>Team: {memories.filter((m) => m.type === "team").length}</span>
          <span>Cache: {memories.filter((m) => m.type === "cache").length}</span>
        </div>
      )}
    </div>
  );
}
