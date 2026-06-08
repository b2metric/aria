"use client";

import { useState, useCallback, useRef, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { streamQuery, fetchConversations, fetchConversation, deleteConversation } from "@/lib/api";
import type { ChatMessage, ChartSpec, ChartConfig, ChartDataPoint } from "@/lib/types";
import ChartArea from "@/components/ChartArea";
import { useSession, signOut, signIn } from "next-auth/react";

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
  const [conversations, setConversations] = useState<any[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

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
        loadConversations();
    }
  }, [status, token, loadConversations]);

  // Auth guard: if the session is missing/expired, redirect to Keycloak login
  // instead of landing on /chat with no token ("No authentication token available").
  useEffect(() => {
    if (status === "unauthenticated") {
      signIn("keycloak");
    }
  }, [status]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

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
                ? { ...rawSpec, data: m.chart_data || rawSpec.data || [], chart_url: m.chart_url || rawSpec.chart_url }
                : null;
              return {
                role: m.role,
                content: m.content || "",
                sql: m.sql || null,
                chartUrl: m.chart_url || null,
                chartSpec,
                id: m.id || `history-${m.role}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}-${i}`,
              };
            });
            setMessages(formattedMessages);
            // Open the most recent message that has a chart artifact in the right panel.
            const lastChartMsg = [...formattedMessages].reverse().find(
              (m: any) => m.role === "assistant" && m.chartSpec,
            );
            setActiveArtifactMsgId(lastChartMsg ? lastChartMsg.id : null);
          }
        })
        .catch((err) => {
          console.error("Failed to load conversation", err);
          setError("Failed to load conversation history.");
        });
    }
  }, [conversationId, token]);

  // Submit initial query from URL
  useEffect(() => {
    if (initialQuery) {
      handleSubmit(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  const handleSubmit = useCallback(
    async (question?: string) => {
      const q = question || inputValue.trim();
      if (!q || isStreaming) return;

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
           signIn("keycloak");
           return;
        }
        
        const { reader, abort } = streamQuery(q, conversationId || undefined, "stc-kuwait", token);
        abortRef.current = abort;

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
            console.log("SSE EVENT:", event, data.substring(0, 100));
            try {
              const payload = JSON.parse(data);

              switch (event) {
                case "status": {
                  const statusMsg = payload.message || "";
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsg.id
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
                      m.id === assistantMsg.id
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
                      m.id === assistantMsg.id
                        ? { ...m, chartSpec: spec, chartUrl: payload.chart_url }
                        : m,
                    ),
                  );
                  // Auto-open the artifact panel on first render of a new chart.
                  setActiveArtifactMsgId(assistantMsg.id);
                  break;
                }

                case "error": {
                  setError(payload.error);
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsg.id
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
                      m.id === assistantMsg.id
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
        setIsStreaming(false);
      }
    },
    [inputValue, isStreaming, conversationId, router],
  );

  const handleNewChat = useCallback(() => {
    abortRef.current?.();
    setMessages([]);
    setConversationId(null);
    setActiveArtifactMsgId(null);
    setError(null);
    setInputValue("");
    inputRef.current?.focus();
  }, []);

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
    <div className="flex h-full w-full bg-white text-gray-900">
      {/* Sidebar */}
      {isSidebarOpen && (
        <div className="w-64 border-r border-gray-200 bg-gray-50 flex flex-col flex-shrink-0 transition-all">
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <h1 className="font-bold text-gray-900 text-lg">ARIA</h1>
            <button
              onClick={() => setIsSidebarOpen(false)}
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
              className="w-full flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
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
          
          <div className="p-4 border-t border-gray-200">
            {status === "authenticated" && (
              <button
                onClick={() => signOut({ callbackUrl: "/" })}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                  <polyline points="16 17 21 12 16 7"></polyline>
                  <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                Logout
              </button>
            )}
          </div>
        </div>
      )}

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-white shadow-sm z-10">
          <div className="flex items-center gap-3">
            {!isSidebarOpen && (
              <button
                onClick={() => setIsSidebarOpen(true)}
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
              <div className="text-4xl mb-4">💬</div>
              <h3 className="text-lg font-semibold text-gray-700 mb-1">
                Start a conversation
              </h3>
              <p className="text-sm text-gray-500 max-w-md">
                Ask anything about your data. For example: &ldquo;Show me
                monthly revenue by region&rdquo; or &ldquo;Top 10 customers by
                purchase amount&rdquo;
              </p>
              <div className="mt-4 flex flex-wrap gap-2 justify-center">
                {[
                  "Show monthly revenue by region",
                  "Top 10 customers by volume",
                  "Daily active users trend",
                ].map((example) => (
                  <button
                    key={example}
                    onClick={() => {
                      setInputValue(example);
                      handleSubmit(example);
                    }}
                    className="px-3 py-1.5 text-xs text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors"
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
                    ? "bg-blue-600 text-white"
                    : "bg-white border border-gray-200 text-gray-900"
                }`}
              >
                {/* Avatar + role */}
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm">
                    {msg.role === "user" ? "🧑" : "🤖"}
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
                    <pre className="mt-1 text-xs bg-gray-900 text-green-400 p-3 rounded-lg overflow-auto font-mono leading-relaxed">
                      {msg.sql}
                    </pre>
                  </details>
                )}

                {/* Artifact chip → opens the right panel */}
                {msg.chartSpec && (
                  <button
                    onClick={() => setActiveArtifactMsgId(msg.id)}
                    className={`mt-2 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                      activeArtifactMsgId === msg.id
                        ? "border-blue-300 bg-blue-50 text-blue-700"
                        : "border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100"
                    }`}
                  >
                    <span>{chartEmoji(msg.chartSpec.type)}</span>
                    <span className="capitalize">{msg.chartSpec.type} chart</span>
                    {msg.chartSpec.title ? (
                      <span className="text-gray-400 truncate max-w-[12rem]">— {msg.chartSpec.title}</span>
                    ) : null}
                  </button>
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
              className="flex-1 px-4 py-3 text-sm bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
            />
            <button
              onClick={() => handleSubmit()}
              disabled={!inputValue.trim() || isStreaming}
              className="px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
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
              {canRecharts ? (
                <ChartArea
                  data={spec.data as ChartDataPoint[]}
                  config={{
                    type: spec.type as ChartConfig["type"],
                    xKey: spec.xKey as string,
                    yKeys: spec.yKeys as string[],
                    title: spec.title,
                    colors: spec.colors,
                  }}
                  filters={{}}
                  onFilterChange={() => {}}
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
