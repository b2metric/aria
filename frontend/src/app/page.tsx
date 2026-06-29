"use client";

import { useSession, signIn } from "next-auth/react";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import type {
  DashboardData,
  Conversation,
  SavedQuery,
  FilterState,
} from "@/lib/types";
import { fetchConversations, listSavedQueries, deleteSavedQuery } from "@/lib/api";
import StatCard from "@/components/StatCard";
import QuerySearch from "@/components/QuerySearch";
import ChartArea from "@/components/ChartArea";
import RecentConversations from "@/components/RecentConversations";
import SavedQueries from "@/components/SavedQueries";

export default function DashboardPage() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [data, setData] = useState<DashboardData | null>(null);
  const [filters, setFilters] = useState<FilterState>({ dateRange: "1y" });
  const [activeTab, setActiveTab] = useState<"recent" | "saved">("recent");

  useEffect(() => {
    // Session yuklenmediyse veya giris yapilmadiysa data getirmeyi bekle
    if (status === "loading") return;
    if (status === "unauthenticated") {
      return;
    }

    async function loadData() {
      try {
        const token = (session as any)?.accessToken;
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/dashboard`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Failed to fetch dashboard data");
        const dashboard: DashboardData = await res.json();

        const realConversations = await fetchConversations(token);
        if (Array.isArray(realConversations)) {
            dashboard.recentConversations = realConversations.map((c: any) => ({
                id: c.id || c.conversation_id || Math.random().toString(),
                query: c.title || "New Chat",
                timestamp: c.created_at || new Date().toISOString(),
                tables: [],
                status: c.status || "completed",
            }));
        }
        try {
          dashboard.savedQueries = await listSavedQueries(token);
        } catch {
          dashboard.savedQueries = [];
        }
        setData(dashboard);
      } catch(e) {
        console.warn("Could not fetch dashboard data", e);
      }
    }
    
    loadData();
  }, [status]);

  const handleSearch = useCallback(
    (query: string) => {
      router.push(`/chat?q=${encodeURIComponent(query)}`);
    },
    [router],
  );

  const handleConversationSelect = useCallback(
    (conv: Conversation) => {
      handleSearch(conv.query);
    },
    [handleSearch],
  );

  const handleSavedQuerySelect = useCallback(
    (sq: SavedQuery) => {
      handleSearch(sq.question);
    },
    [handleSearch],
  );

  const handleSavedQueryDelete = useCallback(
    async (id: string) => {
      const token = (session as any)?.accessToken;
      try {
        await deleteSavedQuery(id, token);
        setData((prev) =>
          prev ? { ...prev, savedQueries: prev.savedQueries.filter((q) => q.id !== id) } : prev,
        );
      } catch {
        /* keep list as-is on failure */
      }
    },
    [session],
  );

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  if (status === "unauthenticated") {
    // We render a fallback until the useEffect redirects
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-pulse text-gray-400">Redirecting to login...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-pulse text-gray-400">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Overview of your analytics activity
          </p>
        </div>
      </div>

      {/* Search Bar */}
      <QuerySearch onSearch={handleSearch} />

      {/* Quick Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {data.stats.map((stat) => (
          <StatCard key={stat.label} data={stat} />
        ))}
      </div>

      {/* Workspace activity stats */}
      {data.workspaceStats && data.workspaceStats.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Workspace activity</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {data.workspaceStats.map((stat) => (
              <StatCard key={stat.label} data={stat} />
            ))}
          </div>
        </div>
      )}

      {/* Chart Area */}
      <ChartArea
        data={data.chartData}
        config={data.chartConfig}
        filters={filters}
        onFilterChange={setFilters}
      />

      {/* Bottom panels: Recent + Saved Queries */}
      <div>
        {/* Tab switcher */}
        <div className="flex items-center gap-1 mb-4 bg-gray-100 rounded-lg p-0.5 w-fit">
          <button
            onClick={() => setActiveTab("recent")}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === "recent"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Recent Queries
          </button>
          <button
            onClick={() => setActiveTab("saved")}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === "saved"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Saved Queries
          </button>
        </div>

        {activeTab === "recent" ? (
          <RecentConversations
            conversations={data.recentConversations}
            onSelect={handleConversationSelect}
          />
        ) : (
          <SavedQueries
            queries={data.savedQueries}
            onSelect={handleSavedQuerySelect}
            onDelete={handleSavedQueryDelete}
          />
        )}
      </div>
    </div>
  );
}
