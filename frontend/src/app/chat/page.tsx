"use client";

import { useState, useCallback, useRef, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { streamQuery } from "@/lib/api";
import type { ChatMessage, ChartSpec } from "@/lib/types";

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
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialQuery = searchParams.get("q") || "";

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [sqlPreview, setSqlPreview] = useState<string | null>(null);
  const [currentChart, setCurrentChart] = useState<ChartSpec | null>(null);
  const [chartHtml, setChartHtml] = useState<string | null>(null);
  const [chartUrl, setChartUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

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
      setSqlPreview(null);
      setCurrentChart(null);
      setChartHtml(null);
      setChartUrl(null);

      try {
        const { reader, abort } = streamQuery(q, conversationId || undefined);
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
                  if (payload.sql) {
                    setSqlPreview(payload.sql);
                  }
                  break;
                }

                case "sql": {
                  setSqlPreview(payload.sql);
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
                  if (payload.chart_spec || payload.chart_config) {
                    const spec = payload.chart_spec || payload.chart_config;
                    setCurrentChart(spec);
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === assistantMsg.id
                          ? { ...m, chartSpec: spec }
                          : m,
                      ),
                    );
                  }
                  if (payload.chart_html) {
                    setChartHtml(payload.chart_html);
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === assistantMsg.id
                          ? { ...m, chartHtml: payload.chart_html }
                          : m,
                      ),
                    );
                  }
                  if (payload.chart_url) {
                    setChartUrl(payload.chart_url);
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === assistantMsg.id
                          ? { ...m, chartUrl: payload.chart_url }
                          : m,
                      ),
                    );
                  }
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
    setSqlPreview(null);
    setCurrentChart(null);
    setChartHtml(null);
    setChartUrl(null);
    setError(null);
    setInputValue("");
    inputRef.current?.focus();
  }, []);

  return (
    <div className="flex h-full">
      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-white">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">New Chat</h2>
            <p className="text-xs text-gray-500">
              Ask questions about your data in natural language
            </p>
          </div>
          <button
            onClick={handleNewChat}
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            + New Chat
          </button>
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

      {/* SQL Preview panel */}
      {sqlPreview && (
        <div className="w-96 border-l border-gray-200 bg-gray-50 flex flex-col">
          <div className="px-4 py-3 border-b border-gray-200 bg-white">
            <h3 className="text-sm font-semibold text-gray-900">SQL Preview</h3>
          </div>
          <div className="flex-1 overflow-auto p-4">
            <pre className="text-xs text-gray-700 bg-gray-900 text-green-400 p-4 rounded-xl overflow-auto font-mono leading-relaxed">
              {sqlPreview}
            </pre>
          </div>
          {currentChart && (
            <div className="p-4 border-t border-gray-200 bg-white">
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                Chart
              </h4>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">
                  {currentChart.type === "bar"
                    ? "📊"
                    : currentChart.type === "line"
                      ? "📈"
                      : currentChart.type === "pie"
                        ? "🥧"
                        : currentChart.type === "scatter"
                          ? "🔵"
                          : "📉"}
                </span>
                <span className="text-sm font-medium text-gray-900 capitalize">
                  {currentChart.type} chart
                </span>
              </div>
              {currentChart.title && (
                <p className="text-xs text-gray-500 mt-1">{currentChart.title}</p>
              )}

              {/* Chart iframe */}
              {chartHtml && (
                <div className="mt-3 border border-gray-200 rounded-lg overflow-hidden bg-white">
                  <iframe
                    srcDoc={chartHtml}
                    className="w-full"
                    style={{ height: "400px", border: "none" }}
                    title="Chart"
                    sandbox="allow-scripts allow-same-origin"
                  />
                </div>
              )}

              {chartUrl && !chartHtml && (
                <div className="mt-3 border border-gray-200 rounded-lg overflow-hidden bg-white">
                  <iframe
                    src={chartUrl}
                    className="w-full"
                    style={{ height: "400px", border: "none" }}
                    title="Chart"
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
