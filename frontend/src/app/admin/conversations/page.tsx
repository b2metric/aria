"use client";

import { MessagesSquare, RefreshCw, Eye, Cpu, Database, Brain } from "lucide-react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ConversationSummary = {
  id: string;
  user_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
};

type QueryTrace = {
  model: string | null;
  model_source: string | null;
  row_count: number;
  sql_generated: boolean;
  memory: {
    user_preferences: number;
    team_conventions: number;
    similar_queries: number;
    snippets: string[];
  } | null;
} | null;

type ConversationMessage = {
  role: string;
  content: string;
  sql: string | null;
  trace: QueryTrace;
  timestamp: string;
};

type ConversationDetail = {
  id: string;
  user_id: string;
  title: string;
  messages: ConversationMessage[];
};

export default function AdminConversationsPage() {
  const { data: session, status } = useSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  const router = useRouter();

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") router.push("/api/auth/signin");
  }, [status, router]);

  const fetchConversations = async () => {
    if (!token) return;
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/admin/conversations?limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setConversations(await res.json());
    } catch (err) {
      console.error("Failed to fetch conversations", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void (async () => {
      await fetchConversations();
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const openConversation = async (id: string) => {
    if (!token) return;
    setDetailLoading(true);
    setDetail(null);
    try {
      const res = await fetch(`${API_BASE}/api/admin/conversations/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setDetail(await res.json());
    } catch (err) {
      console.error("Failed to fetch conversation detail", err);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <MessagesSquare className="w-6 h-6 text-blue-600" />
            Conversation Debug
          </h1>
          <p className="text-gray-500 mt-1">
            Inspect every conversation in your workspace and its per-turn query trace.
          </p>
        </div>
        <Button variant="outline" onClick={fetchConversations} disabled={loading} className="w-full sm:w-auto">
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 font-semibold">Title</th>
                <th className="px-6 py-3 font-semibold">User ID</th>
                <th className="px-6 py-3 font-semibold">Messages</th>
                <th className="px-6 py-3 font-semibold">Updated</th>
                <th className="px-6 py-3 font-semibold"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading && conversations.length === 0 ? (
                <tr><td colSpan={5} className="px-6 py-8 text-center text-gray-500">Loading conversations...</td></tr>
              ) : conversations.length === 0 ? (
                <tr><td colSpan={5} className="px-6 py-8 text-center text-gray-500">No conversations in this workspace yet.</td></tr>
              ) : (
                conversations.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 font-medium text-gray-900 max-w-xs truncate" title={c.title}>{c.title}</td>
                    <td className="px-6 py-4 font-mono text-xs text-gray-600">{c.user_id}</td>
                    <td className="px-6 py-4 text-gray-600">{c.message_count}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">{new Date(c.updated_at).toLocaleString()}</td>
                    <td className="px-6 py-4">
                      <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => openConversation(c.id)}>
                        <Eye className="w-3 h-3 mr-1" /> Inspect
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Dialog open={detailLoading || detail !== null} onOpenChange={(open) => { if (!open) setDetail(null); }}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{detail ? detail.title : "Loading conversation..."}</DialogTitle>
          </DialogHeader>
          {detailLoading ? (
            <div className="py-8 text-center text-gray-500">Loading conversation detail...</div>
          ) : detail ? (
            <div className="mt-2 space-y-4">
              {detail.messages.map((m, i) => (
                <div
                  key={i}
                  className={`rounded-lg border p-3 ${m.role === "user" ? "bg-blue-50 border-blue-100" : "bg-gray-50 border-gray-200"}`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <Badge variant="outline" className={m.role === "user" ? "bg-blue-100 text-blue-700 border-blue-200" : "bg-gray-100 text-gray-700 border-gray-300"}>
                      {m.role}
                    </Badge>
                    {m.timestamp && <span className="text-xs text-gray-400">{new Date(m.timestamp).toLocaleString()}</span>}
                  </div>
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{m.content}</p>

                  {m.sql && (
                    <pre className="mt-2 bg-gray-900 text-gray-100 p-3 rounded text-xs overflow-x-auto whitespace-pre-wrap break-all">{m.sql}</pre>
                  )}

                  {m.trace && (
                    <div className="mt-3 border-t border-gray-200 pt-2">
                      <div className="text-xs font-semibold text-gray-500 uppercase mb-1.5">Query Trace</div>
                      <div className="flex flex-wrap gap-2 text-xs">
                        {m.trace.model && (
                          <span className="inline-flex items-center gap-1 bg-white border border-gray-200 rounded px-2 py-0.5">
                            <Cpu className="w-3 h-3 text-blue-600" /> {m.trace.model}
                            {m.trace.model_source && <span className="text-gray-400">· {m.trace.model_source}</span>}
                          </span>
                        )}
                        <span className="inline-flex items-center gap-1 bg-white border border-gray-200 rounded px-2 py-0.5">
                          <Database className="w-3 h-3 text-emerald-600" /> {m.trace.row_count} rows
                        </span>
                        <span className="inline-flex items-center gap-1 bg-white border border-gray-200 rounded px-2 py-0.5">
                          SQL {m.trace.sql_generated ? "✓" : "—"}
                        </span>
                        {m.trace.memory && (
                          <span className="inline-flex items-center gap-1 bg-white border border-gray-200 rounded px-2 py-0.5">
                            <Brain className="w-3 h-3 text-purple-600" />
                            mem: {m.trace.memory.user_preferences}p / {m.trace.memory.team_conventions}c / {m.trace.memory.similar_queries}q
                          </span>
                        )}
                      </div>
                      {m.trace.memory && m.trace.memory.snippets.length > 0 && (
                        <ul className="mt-2 space-y-1">
                          {m.trace.memory.snippets.map((s, j) => (
                            <li key={j} className="text-xs text-gray-500 bg-white border border-gray-100 rounded px-2 py-1 truncate" title={s}>{s}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
