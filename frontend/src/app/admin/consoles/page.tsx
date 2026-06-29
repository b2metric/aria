"use client";

import { useEffect, useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import { Boxes, ExternalLink } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ConsoleLink {
  key: string;
  name: string;
  url: string;
  embeddable: boolean;
}

export default function ServiceConsolesPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken;

  const [consoles, setConsoles] = useState<ConsoleLink[]>([]);
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchConsoles = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/admin/consoles`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data: ConsoleLink[] = await res.json();
        const list = Array.isArray(data) ? data : [];
        setConsoles(list);
        // Default to the first embeddable console (so the iframe shows on load).
        setActiveKey(
          (prev) => prev ?? list.find((c) => c.embeddable)?.key ?? list[0]?.key ?? null,
        );
      } else {
        console.error("Failed to fetch consoles", res.status);
      }
    } catch (err) {
      console.error("Failed to fetch consoles", err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) void (async () => { await fetchConsoles(); })();
  }, [token, fetchConsoles]);

  const active = consoles.find((c) => c.key === activeKey) ?? null;

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Boxes className="w-6 h-6 text-blue-600" />
          Service Consoles
        </h1>
        <p className="text-gray-500 mt-1">
          Infrastructure web consoles, embedded for admins. Consoles that block
          framing open in a new tab.
        </p>
      </div>

      {loading && consoles.length === 0 ? (
        <div className="animate-pulse h-96 bg-gray-200 rounded-xl" />
      ) : (
        <div className="flex gap-4">
          {/* Console switcher */}
          <nav className="w-56 shrink-0 space-y-1">
            {consoles.map((c) => (
              <button
                key={c.key}
                onClick={() => setActiveKey(c.key)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                  c.key === activeKey
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                <span>{c.name}</span>
                {!c.embeddable && (
                  <ExternalLink className="w-3.5 h-3.5 text-gray-400" aria-label="Opens in new tab" />
                )}
              </button>
            ))}
          </nav>

          {/* Active console */}
          <div className="flex-1 min-w-0">
            {active ? (
              <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100">
                  <span className="font-semibold text-gray-800">{active.name}</span>
                  <a
                    href={active.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
                  >
                    Open in new tab
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
                {active.embeddable ? (
                  <iframe
                    key={active.key}
                    src={active.url}
                    title={active.name}
                    className="w-full bg-white"
                    style={{ height: "calc(100vh - 230px)", minHeight: 480, border: "none" }}
                    sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"
                  />
                ) : (
                  <div className="p-10 text-center text-gray-500">
                    <p className="font-medium text-gray-700">
                      {active.name} blocks embedding (its CSP forbids framing).
                    </p>
                    <p className="mt-1 text-sm">Use “Open in new tab” above to launch it.</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-gray-500 mt-10">No consoles available.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
