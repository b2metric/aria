"use client";

import { useState, useCallback, useRef, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { streamQuery, streamResume, getRunStatus, fetchConversations, fetchConversation, deleteConversation, fetchWorkspaceSuggestions, saveQuery, deleteSavedQuery, getExportStatus, downloadExport } from "@/lib/api";
import type { ChatMessage, ChartSpec, ChartConfig, ChartDataPoint, FilterState } from "@/lib/types";
import ChartArea from "@/components/ChartArea";
import { useSession, signIn } from "next-auth/react";
import { Sparkles, User } from "lucide-react";

// Emoji for a chart artifact chip/header.
function chartEmoji(type?: string): string {
  switch (type) {
    case "bar": return "📊";
    case "line": return "📈";
    case "area": return "📉";
    case "pie": return "🥧";
    case "scatter": return "🔵";
    default: return "📋";
  }
}

// Tabular ("data grid") view of the result rows.
function DataGrid({ rows }: { rows: ChartDataPoint[] }) {
  if (!rows || rows.length === 0) {
    return <div className="text-sm text-gray-400 text-center py-8">No data.</div>;
  }
  const cols = Object.keys(rows[0]);
  const shown = rows.slice(0, 200);
  return (
    <div className="overflow-auto border border-gray-200 rounded-lg bg-white">
      <table className="w-full text-xs">
        <thead className="bg-gray-50 sticky top-0">
          <tr>
            {cols.map((c) => (
              <th key={c} className="text-left font-semibold text-gray-600 px-3 py-2 border-b border-gray-200 whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.map((r, i) => (
            <tr key={i} className={i % 2 ? "bg-gray-50/50" : ""}>
              {cols.map((c) => (
                <td key={c} className="px-3 py-1.5 border-b border-gray-100 text-gray-800 whitespace-nowrap">
                  {typeof r[c] === "number" ? (r[c] as number).toLocaleString() : String(r[c] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > shown.length && (
        <div className="px-3 py-2 text-xs text-gray-400">Showing {shown.length} of {rows.length} rows</div>
      )}
    </div>
  );
}

// ── SSE Parser ───────────────────────────────────────────────────────

function parseSSEChunk(chunk: string): Array<{ event: string; data: string }> {
  const events: Array<{ event: string; data: string }> = [];
  const normalized = chunk.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lines = normalized.split("\n");
  let currentEvent = "";
  let currentData = "";

  for (const line of lines) {
    if (line.startsWith("event: ")) {
      currentEvent = line.slice(7).trim();
    } else if (line.startsWith("data: ")) {
      currentData += line.slice(6);
    } else if (line === "" && currentEvent) {
      try {
        events.push({ event: currentEvent, data: currentData });
      } catch {
        events.push({ event: currentEvent, data: currentData });
      }
      currentEvent = "";
      currentData = "";
    }
  }

  // Handle incomplete chunk
  if (currentEvent && currentData) {
    try {
      events.push({ event: currentEvent, data: currentData });
    } catch {
      // partial data, skip
    }
  }

  return events;
}

// ── Loading Fallback ─────────────────────────────────────────────────

function ChatLoading() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm text-gray-500">Loading chat...</p>
      </div>
    </div>
  );
}

// ── Main Page Wrapper (Suspense boundary for useSearchParams) ────────

export default function ChatPage() {
  return (
    <Suspense fallback={<ChatLoading />}>
      <ChatPageContent />
    </Suspense>
  );
}

// ── Chat Page Content ────────────────────────────────────────────────

function ChatPageContent() {
  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const workspaceId = (session as any)?.user?.workspaceId || "";
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialQuery = searchParams.get("q") || "";
  const initialCid = searchParams.get("cid") || null;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(initialCid);
  // Claude-Desktop-style artifact panel: id of the message whose artifact is shown on the right.
  const [activeArtifactMsgId, setActiveArtifactMsgId] = useState<string | null>(null);
  const [panelFilters, setPanelFilters] = useState<FilterState>({});
  // Per-message saved-query state: message id → saved query id (for the inline
  // "Query saved" + delete affordance). `savingMsgId` marks an in-flight save.
  const [savedQueryByMsg, setSavedQueryByMsg] = useState<Record<string, string>>({});
  const [savingMsgId, setSavingMsgId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<any[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([
    "Show monthly revenue by region",
    "Top 10 customers by volume",
    "Daily active users trend"
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<(() => void) | null>(null);
  // True only when the page mounted WITHOUT a ?cid= (fresh nav back to /chat).
  // Consumed once to auto-restore the last conversation; cleared by New Chat or
  // by sending a message so an intentional reset is never overridden.
  const pendingRestoreRef = useRef<boolean>(initialCid === null);


  // Load workspace suggestions
  useEffect(() => {
    if (token && workspaceId) {
      fetchWorkspaceSuggestions(workspaceId, token)
        .then((data) => setSuggestions(data))
        .catch(() => {});
    }
  }, [token, workspaceId]);

  // Load conversations list
  const loadConversations = useCallback(async () => {
    if (!token) return;
    try {
      const data = await fetchConversations(token).catch(() => []);
      if (Array.isArray(data)) {
        setConversations(data);
      }
    } catch (err) {
      console.error(err);
    }
  }, [token]);

  useEffect(() => {
    if (status === "authenticated" && token) {
      void (async () => { await loadConversations(); })();
    }
  }, [status, token, loadConversations]);

  // Auth guard: if the session is missing/expired, redirect to Keycloak login
  // instead of landing on /chat with no token ("No authentication token available").
  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status]);

  // Reset the artifact panel's date filter when switching between artifacts.
  useEffect(() => {
    void (async () => { setPanelFilters({}); })();
  }, [activeArtifactMsgId]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Poll a background CSV export job (created by the `export` SSE event) until
  // it reaches a terminal state, updating the owning message each tick so the
  // UI can flip from "preparing" to a Download button (or an error).
  const pollExportJob = useCallback((jobId: string, msgId: string, authToken?: string) => {
    let attempts = 0;
    const tick = async () => {
      attempts += 1;
      const st = await getExportStatus(jobId, authToken);
      if (!st) {
        if (attempts < 90) setTimeout(tick, 2000);
        return;
      }
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? {
                ...m,
                exportStatus: st.status,
                exportRowCount: st.row_count,
                exportTruncated: st.truncated,
                exportDownloadReady: st.download_ready,
                error: st.status === "error" ? (st.error || "Export failed") : m.error,
              }
            : m,
        ),
      );
      if (st.status !== "success" && st.status !== "error" && attempts < 90) {
        setTimeout(tick, 2000);
      }
    };
    setTimeout(tick, 1500);
  }, []);

  // Consume an SSE reader, applying events to the assistant message `targetId`.
  // Shared by the live POST path and the resume-on-load path. Declared before the
  // load effect so that effect can list it as a dependency without a const TDZ.
  const consumeStream = useCallback(
    async (
      reader: ReadableStreamDefaultReader<Uint8Array>,
      targetId: string,
    ): Promise<void> => {
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE events
        const events = parseSSEChunk(buffer);
        // Keep the last incomplete chunk in buffer
        const lastNewline = buffer.lastIndexOf("\n\n");
        if (lastNewline >= 0) {
          buffer = buffer.slice(lastNewline + 2);
        }

        for (const { event, data } of events) {
          try {
            const payload = JSON.parse(data);

            switch (event) {
              case "status": {
                const statusMsg = payload.message || "";
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === targetId
                      ? {
                          ...m,
                          content: m.content ? `${m.content}\n${statusMsg}` : statusMsg,
                          status:
                            payload.status === "complete" ? "complete" : "streaming",
                        }
                      : m,
                  ),
                );
                if (payload.conversation_id) {
                  setConversationId(payload.conversation_id);
                }
                break;
              }

              case "sql": {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === targetId
                      ? { ...m, sql: payload.sql, content: payload.explanation || m.content }
                      : m,
                  ),
                );
                break;
              }

              case "chart": {
                const cfg = payload.chart_config || payload.chart_spec || {};
                const spec: ChartSpec = {
                  type: cfg.type || payload.chart_type || "bar",
                  title: cfg.title,
                  xKey: cfg.xKey,
                  yKeys: cfg.yKeys,
                  colors: cfg.colors,
                  data: payload.chart_data || cfg.data || [],
                  chart_url: payload.chart_url,
                  csv_url: payload.csv_url,
                  row_count: payload.row_count,
                };
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === targetId
                      ? { ...m, chartSpec: spec, chartUrl: payload.chart_url }
                      : m,
                  ),
                );
                // Auto-open the artifact panel on first render of a new chart.
                setActiveArtifactMsgId(targetId);
                break;
              }

              case "insight": {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === targetId
                      ? {
                          ...m,
                          summary: payload.summary,
                          suggestions: payload.suggestions,
                        }
                      : m,
                  ),
                );
                break;
              }

              case "export": {
                const jobId = payload.export_job_id as string;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === targetId
                      ? {
                          ...m,
                          content: payload.message || "Preparing a CSV export…",
                          status: "complete",
                          exportJobId: jobId,
                          exportStatus: "queued",
                        }
                      : m,
                  ),
                );
                setIsStreaming(false);
                pollExportJob(jobId, targetId, token);
                break;
              }

              case "error": {
                setError(payload.error);
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === targetId
                      ? {
                          ...m,
                          status: "error",
                          error: payload.error,
                        }
                      : m,
                  ),
                );
                setIsStreaming(false);
                break;
              }

              case "done": {
                if (payload.conversation_id) {
                  setConversationId(payload.conversation_id);
                  router.replace(`/chat?cid=${payload.conversation_id}`, {
                    scroll: false,
                  });
                }
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === targetId
                      ? { ...m, status: "complete" }
                      : m,
                  ),
                );
                setIsStreaming(false);
                break;
              }
            }
          } catch {
            // Malformed event data — skip
          }
        }
      }
    },
    [router, pollExportJob, token],
  );

  // Load specific conversation if cid changes
  useEffect(() => {
    if (conversationId && token) {
      fetchConversation(conversationId, token)
        .then((data) => {
          // Convert API response schema (snake_case) to UI schema (camelCase)
          if (data && Array.isArray(data.messages)) {
            const formattedMessages = data.messages.map((m: any, i: number) => {
              const rawSpec = m.chart_spec || m.chart_config || null;
              const chartSpec = rawSpec
                ? {
                    ...rawSpec,
                    data: m.chart_data || rawSpec.data || [],
                    chart_url: m.chart_url || rawSpec.chart_url,
                    csv_url: m.csv_url || rawSpec.csv_url,
                  }
                : null;
              return {
                role: m.role,
                content: m.content || "",
                sql: m.sql || null,
                chartUrl: m.chart_url || null,
                chartSpec,
                summary: m.summary || null,
                suggestions: m.suggestions || null,
                id: m.id || `history-${m.role}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}-${i}`,
              };
            });
            setMessages(formattedMessages);
            // Open the most recent message that has a chart artifact in the right panel.
            const lastChartMsg = [...formattedMessages].reverse().find(
              (m: any) => m.role === "assistant" && m.chartSpec,
            );
            setActiveArtifactMsgId(lastChartMsg ? lastChartMsg.id : null);

            // If a run is still generating server-side (e.g. user refreshed
            // mid-answer), re-attach to its live stream and finish the turn.
            const last = formattedMessages[formattedMessages.length - 1];
            const danglingUser = last && last.role === "user";
            getRunStatus(conversationId, token)
              .then(({ status }) => {
                if (status !== "running" || !danglingUser) return;
                const assistantId = `resume-${conversationId}-${Date.now()}`;
                const assistantMsg: ChatMessage = {
                  id: assistantId,
                  role: "assistant",
                  content: "",
                  status: "streaming",
                };
                setMessages((prev) => [...prev, assistantMsg]);
                setIsStreaming(true);
                const { reader, abort } = streamResume(conversationId, token);
                abortRef.current = abort;
                consumeStream(reader, assistantId)
                  .catch(() => {
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === assistantId
                          ? { ...m, status: "error", error: "Connection lost while resuming." }
                          : m,
                      ),
                    );
                  })
                  .finally(() => {
                    abortRef.current = null;
                    setIsStreaming(false);
                  });
              })
              // A failed status check (401 / network) should silently skip resume —
              // the conversation history is already rendered.
              .catch(() => {});
          }
        })
        .catch((err) => {
          console.error("Failed to load conversation", err);
          setError("Failed to load conversation history.");
        });
    }
  }, [conversationId, token, consumeStream]);

  // Auto-restore the last conversation when the user returns to /chat without a
  // ?cid= (e.g. via sidebar nav or a plain link). The conversation lives in Redis
  // server-side; only the frontend lost which one was active. Runs once, and is
  // disabled by New Chat / sending a message so an intentional reset is honored.
  useEffect(() => {
    if (!pendingRestoreRef.current) return;
    if (status !== "authenticated" || !token) return;
    if (conversationId) {
      pendingRestoreRef.current = false;
      return;
    }
    if (conversations.length === 0) return; // list not loaded yet — wait
    pendingRestoreRef.current = false;
    const lastId =
      typeof window !== "undefined" ? localStorage.getItem("last_conversation_id") : null;
    const target =
      lastId && conversations.some((c) => c.id === lastId) ? lastId : conversations[0]?.id;
    if (target) {
      // restore-on-mount: deliberately seeding state from the persisted id
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setConversationId(target);
      router.replace(`/chat?cid=${target}`, { scroll: false });
    }
  }, [status, token, conversationId, conversations, router]);

  // Remember the active conversation so a later return can restore it even if the
  // ?cid= URL param was dropped.
  useEffect(() => {
    if (conversationId && typeof window !== "undefined") {
      localStorage.setItem("last_conversation_id", conversationId);
    }
  }, [conversationId]);

  const handleSubmit = useCallback(
    async (question?: string) => {
      const q = question || inputValue.trim();
      if (!q || isStreaming) return;

      pendingRestoreRef.current = false; // user is actively chatting — no auto-restore

      // Cancel previous stream
      abortRef.current?.();

      setIsStreaming(true);
      setError(null);
      setInputValue("");

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: q,
        status: "complete",
      };

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: "",
        status: "streaming",
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);

      try {
        if (!token) {
           // Session expired/missing — send the user to login instead of erroring.
           setIsStreaming(false);
           router.push("/login");
           return;
        }

        const { reader, abort } = streamQuery(q, conversationId || undefined, workspaceId, token);
        abortRef.current = abort;
        await consumeStream(reader, assistantMsg.id);
        setIsStreaming(false);
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") {
          // User cancelled
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id ? { ...m, status: "complete" } : m,
            ),
          );
        } else {
          const errMsg = err instanceof Error ? err.message : String(err);
          setError(errMsg);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? { ...m, status: "error", error: errMsg }
                : m,
            ),
          );
        }
      } finally {
        abortRef.current = null;
        setIsStreaming(false); // <--- HER ZAMAN STREAMING'I KAPAT
      }
    },
    [inputValue, isStreaming, conversationId, router, token, consumeStream],
  );

  // Submit initial query from URL
  useEffect(() => {
    if (initialQuery) {
      void (async () => { await handleSubmit(initialQuery); })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);
  const handleNewChat = useCallback(() => {
    abortRef.current?.();
    pendingRestoreRef.current = false; // explicit reset — do not auto-restore
    setMessages([]);
    setConversationId(null);
    setActiveArtifactMsgId(null);
    setError(null);
    setInputValue("");
    router.replace("/chat", { scroll: false }); // drop stale ?cid= from the URL
    inputRef.current?.focus();
  }, [router]);

  const handleDeleteConversation = useCallback(async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      if (!token) return;
      await deleteConversation(id, token);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (conversationId === id) {
        handleNewChat();
      }
    } catch (err) {
      console.error("Failed to delete conversation", err);
    }
  }, [conversationId, handleNewChat, token]);

  return (
    <div className="flex h-full w-full bg-white text-gray-900 relative">
      {/* Mobile History Backdrop */}
      {isHistoryOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black/50 z-20"
          onClick={() => setIsHistoryOpen(false)}
        />
      )}
      
      {/* History Sidebar - Desktop & Mobile */}
      <div 
        className={`
          fixed md:relative top-0 bottom-0 left-0 z-30 w-72 md:w-64 bg-gray-50 border-r border-gray-200 flex flex-col transition-transform duration-300 ease-in-out
          ${isHistoryOpen ? "translate-x-0" : "-translate-x-full md:hidden"}
          ${isHistoryOpen ? "md:translate-x-0" : "md:hidden"}
        `}
      >
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="font-medium text-gray-700">History</h2>
            <button
              onClick={() => setIsHistoryOpen(false)}
              className="text-gray-500 hover:text-gray-900"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          
          <div className="p-4">
            <button
              onClick={handleNewChat}
              className="w-full flex items-center gap-2 px-4 py-2 bg-blue-600 text-[#ffffff] rounded-lg hover:bg-blue-700 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              New Chat
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Recent History
            </h3>
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`w-full text-left p-3 rounded-lg text-sm truncate transition-colors flex items-center justify-between group ${
                  conversationId === conv.id
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                <button
                  onClick={() => {
                    setConversationId(conv.id);
                    router.push(`/chat?cid=${conv.id}`);
                  }}
                  className="flex-1 truncate text-left"
                >
                  {conv.title || "New Conversation"}
                </button>
                <button
                  onClick={(e) => handleDeleteConversation(conv.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 rounded transition-all"
                  title="Delete conversation"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 6h18"></path>
                    <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                    <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                  </svg>
                </button>
              </div>
            ))}
            {conversations.length === 0 && (
              <p className="text-xs text-gray-400 text-center py-4">No history yet</p>
            )}
          </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-white shadow-sm z-10">
          <div className="flex items-center gap-3">
            {!isHistoryOpen && (
              <button
                onClick={() => setIsHistoryOpen(true)}
                className="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="3" y1="12" x2="21" y2="12"></line>
                  <line x1="3" y1="6" x2="21" y2="6"></line>
                  <line x1="3" y1="18" x2="21" y2="18"></line>
                </svg>
              </button>
            )}
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {conversations.find((c) => c.id === conversationId)?.title || "New Chat"}
              </h2>
              <p className="text-xs text-gray-500">Ask questions about your data in natural language</p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto px-6 py-4 space-y-4">
          {messages.length === 0 && !isStreaming && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                <Sparkles className="h-7 w-7" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-1.5">
                What do you want to know?
              </h3>
              <p className="text-sm text-gray-500 max-w-md">
                Ask anything about your data. Pick a starting point below or type your own question.
              </p>
              <div className="mt-5 flex flex-wrap gap-2 justify-center max-w-lg">
                {suggestions.map((example) => (
                  <button
                    key={example}
                    onClick={() => {
                      setInputValue(example);
                      handleSubmit(example);
                    }}
                    className="px-3.5 py-2 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-100 hover:bg-blue-100 hover:border-blue-200 rounded-full cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-blue-600 text-[#ffffff]"
                    : "bg-white border border-gray-200 text-gray-900"
                }`}
              >
                {/* Avatar + role */}
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`flex h-5 w-5 items-center justify-center rounded-full ${
                      msg.role === "user" ? "bg-white/20 text-[#ffffff]" : "bg-blue-50 text-blue-600"
                    }`}
                  >
                    {msg.role === "user" ? <User className="h-3 w-3" /> : <Sparkles className="h-3 w-3" />}
                  </span>
                  <span className="text-xs font-medium opacity-70">
                    {msg.role === "user" ? "You" : "ARIA"}
                  </span>
                  {msg.status === "streaming" && (
                    <span className="inline-block w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                  )}
                  {msg.status === "error" && (
                    <span className="text-xs text-red-400">Error</span>
                  )}
                </div>

                {/* Content */}
                <div className="text-sm whitespace-pre-wrap leading-relaxed">
                  {msg.content || (msg.status === "streaming" ? "Thinking..." : "")}
                </div>

                {/* Inline SQL (collapsible) — visible to admin / SQL-permitted roles */}
                {msg.sql && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs font-medium text-gray-500 hover:text-gray-700 select-none">
                      🔍 View SQL
                    </summary>
                    <pre className="mt-1 text-xs bg-[#0d0d14] text-green-400 p-3 rounded-lg overflow-auto font-mono leading-relaxed">
                      {msg.sql}
                    </pre>
                  </details>
                )}

                {/* Action chips → opens the artifact panel / saves the query */}
                {(msg.chartSpec || (msg.sql && msg.role === "assistant" && msg.status !== "streaming")) && (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    {msg.chartSpec && (
                      <button
                        onClick={() => setActiveArtifactMsgId(msg.id)}
                        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                          activeArtifactMsgId === msg.id
                            ? "border-blue-300 bg-blue-50 text-blue-700"
                            : "border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100"
                        }`}
                      >
                        <span>{chartEmoji(msg.chartSpec.type)}</span>
                        <span className="capitalize">
                          {msg.chartSpec.type === "table" ? "Data grid" : `${msg.chartSpec.type} chart`}
                        </span>
                        {msg.chartSpec.title ? (
                          <span className="text-gray-400 truncate max-w-[12rem]">— {msg.chartSpec.title}</span>
                        ) : null}
                      </button>
                    )}
                    {msg.sql && msg.role === "assistant" && msg.status !== "streaming" && (
                      savedQueryByMsg[msg.id] ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-green-200 bg-green-50 text-green-700 text-xs font-medium">
                          <span>✓</span>
                          <span>Query saved</span>
                          <button
                            type="button"
                            title="Delete saved query"
                            aria-label="Delete saved query"
                            onClick={async () => {
                              if (!confirm("Delete this saved query?")) return;
                              const sid = savedQueryByMsg[msg.id];
                              try {
                                await deleteSavedQuery(sid, token);
                                setSavedQueryByMsg((prev) => {
                                  const next = { ...prev };
                                  delete next[msg.id];
                                  return next;
                                });
                              } catch {
                                alert("Could not delete saved query");
                              }
                            }}
                            className="ml-0.5 -mr-1 px-1 rounded text-green-600 hover:text-red-600 hover:bg-red-50 transition-colors"
                          >
                            ✕
                          </button>
                        </span>
                      ) : (
                        <button
                          type="button"
                          disabled={savingMsgId === msg.id}
                          onClick={async () => {
                            const idx = messages.findIndex((m) => m.id === msg.id);
                            const q =
                              [...messages.slice(0, idx)].reverse().find((m) => m.role === "user")?.content ?? "";
                            setSavingMsgId(msg.id);
                            try {
                              const saved = await saveQuery(q, msg.sql!, undefined, token);
                              setSavedQueryByMsg((prev) => ({ ...prev, [msg.id]: saved.id }));
                            } catch {
                              alert("Could not save query");
                            } finally {
                              setSavingMsgId(null);
                            }
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100 hover:text-blue-700 text-xs font-medium transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                          <span>💾</span>
                          <span>{savingMsgId === msg.id ? "Saving…" : "Save query"}</span>
                        </button>
                      )
                    )}
                  </div>
                )}

                {/* Insight Summary & Suggestions */}
                {msg.summary && (
                  <div className="mt-3 p-3 bg-blue-50/50 border border-blue-100 rounded-lg text-sm text-gray-800">
                    <strong className="text-blue-800 text-xs uppercase tracking-wider mb-1 block">💡 Insight</strong>
                    {msg.summary}
                  </div>
                )}
                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div className="mt-2 flex flex-col gap-1.5">
                    {msg.suggestions.map((suggestion, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setInputValue(suggestion);
                          handleSubmit(suggestion);
                        }}
                        className="w-full px-3 py-2 bg-white border border-gray-200 hover:bg-gray-50 hover:border-blue-300 text-xs text-gray-700 rounded-lg transition-colors shadow-sm text-left flex items-start gap-2"
                        title={suggestion}
                      >
                        <span className="text-blue-500 mt-0.5">✦</span>
                        <span className="leading-snug">{suggestion}</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* CSV export (massive-export Phase 4): preparing → download button */}
                {msg.exportJobId && (
                  <div className="mt-2 flex flex-col gap-2">
                    {msg.exportStatus === "success" && msg.exportDownloadReady ? (
                      <button
                        type="button"
                        onClick={() =>
                          downloadExport(
                            msg.exportJobId!,
                            `export_${msg.exportJobId}.csv`,
                            token,
                          ).catch(() => {
                            setError("Could not download the export. Please try again.");
                          })
                        }
                        className="inline-flex items-center gap-1.5 self-start px-3 py-1.5 rounded-lg border border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100 hover:text-blue-700 text-xs font-medium transition-colors"
                      >
                        <span>⬇</span>
                        <span>
                          Download CSV
                          {typeof msg.exportRowCount === "number"
                            ? ` (${msg.exportRowCount.toLocaleString()} rows${msg.exportTruncated ? ", truncated" : ""})`
                            : ""}
                        </span>
                      </button>
                    ) : msg.exportStatus === "error" ? (
                      <span className="text-xs text-red-700">
                        Export failed. Try narrowing the query.
                      </span>
                    ) : (
                      <span className="text-xs text-gray-500 inline-flex items-center gap-1.5">
                        <span className="inline-block w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                        Preparing CSV export… (this can take a moment for very large results)
                      </span>
                    )}
                  </div>
                )}

                {/* Error */}
                {msg.error && (
                  <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                    {msg.error}
                  </div>
                )}
              </div>
            </div>
          ))}

          {error && messages.length === 0 && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
              {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-6 py-4 border-t border-gray-200 bg-white">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              placeholder="Ask a question about your data..."
              disabled={isStreaming}
              className="flex-1 px-4 py-3.5 text-sm bg-gray-50 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent hover:border-gray-300 transition-colors disabled:opacity-50"
            />
            <button
              onClick={() => handleSubmit()}
              disabled={!inputValue.trim() || isStreaming}
              className="px-4 py-3.5 bg-blue-600 text-[#ffffff] rounded-2xl cursor-pointer hover:bg-blue-700 active:scale-[0.98] disabled:bg-gray-300 disabled:cursor-not-allowed transition-all"
            >
              {isStreaming ? (
                <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              )}
            </button>
            {isStreaming && (
              <button
                onClick={() => abortRef.current?.()}
                className="px-3 py-3 text-gray-400 hover:text-red-500 transition-colors"
                title="Stop generating"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <rect x="4" y="4" width="16" height="16" rx="2" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Artifact panel (Claude-Desktop style) — opens on chip click / auto-opens on new chart */}
      {(() => {
        const activeMsg = messages.find((m) => m.id === activeArtifactMsgId);
        const spec = activeMsg?.chartSpec;
        if (!activeMsg || !spec) return null;
        const rechartsTypes = ["bar", "line", "area", "pie"];
        const canRecharts =
          !!spec.data && spec.data.length > 0 && !!spec.xKey &&
          (spec.yKeys?.length ?? 0) > 0 && rechartsTypes.includes(spec.type);
        return (
          <div className="w-[28rem] border-l border-gray-200 bg-gray-50 flex flex-col flex-shrink-0">
            <div className="px-4 py-3 border-b border-gray-200 bg-white flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-lg">{chartEmoji(spec.type)}</span>
                <h3 className="text-sm font-semibold text-gray-900 truncate">
                  {spec.title || "Artifact"}
                </h3>
              </div>
              <button
                onClick={() => setActiveArtifactMsgId(null)}
                className="text-gray-400 hover:text-gray-700 flex-shrink-0"
                title="Close"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              {spec.type === "table" ? (
                <DataGrid rows={(spec.data ?? []) as ChartDataPoint[]} />
              ) : canRecharts ? (
                <ChartArea
                  key={activeMsg.id}
                  data={spec.data as ChartDataPoint[]}
                  config={{
                    type: spec.type as ChartConfig["type"],
                    xKey: spec.xKey as string,
                    yKeys: spec.yKeys as string[],
                    title: spec.title,
                    colors: spec.colors,
                  }}
                  filters={panelFilters}
                  onFilterChange={setPanelFilters}
                />
              ) : spec.chart_url ? (
                <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
                  <iframe
                    src={spec.chart_url}
                    className="w-full"
                    style={{ height: 440, border: "none" }}
                    title="Chart"
                    sandbox="allow-scripts allow-same-origin"
                  />
                </div>
              ) : spec.data && spec.data.length > 0 ? (
                <DataGrid rows={spec.data as ChartDataPoint[]} />
              ) : (
                <div className="text-sm text-gray-400 text-center py-8">
                  No chart preview available.
                </div>
              )}
              {spec.csv_url && (
                <a
                  href={spec.csv_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-block text-xs text-blue-600 hover:underline"
                >
                  ⬇ Download CSV
                </a>
              )}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
