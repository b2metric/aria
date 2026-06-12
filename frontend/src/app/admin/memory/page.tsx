"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { fetchAdminMemory } from "@/lib/api";

export default function MemoryManagerPage() {
  const { data: session } = useSession();
  const [memories, setMemories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch memory data when the page mounts
  useEffect(() => {
    if (!session?.accessToken) return;

    fetchAdminMemory(session.accessToken)
      .then((data) => {
        setMemories(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch memories", err);
        setLoading(false);
      });
  }, [session?.accessToken]);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Memory Manager</h1>
        <p className="text-gray-500">View and manage Qdrant/Mem0 memory entries for users and teams.</p>
      </div>
      
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
          No memory entries found.
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="w-full text-left text-sm text-gray-700">
            <thead className="bg-gray-50 text-gray-500 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 font-medium">Entity ID</th>
                <th className="px-6 py-4 font-medium">Content</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {memories.map((mem, idx) => (
                <tr key={idx} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 font-mono text-xs text-blue-600 bg-blue-50/50 rounded">{mem.entity_id || "N/A"}</td>
                  <td className="px-6 py-4 truncate max-w-md">{mem.content || "N/A"}</td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-red-600 hover:text-red-700 text-sm font-medium px-3 py-1.5 border border-red-200 hover:bg-red-50 rounded-md transition-colors">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
