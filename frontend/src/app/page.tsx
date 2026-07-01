"use client";

import { useSession, signIn } from "next-auth/react";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import type {
  DashboardData,
  Conversation,
  SavedQuery,
  FilterState,
  PickerItem,
} from "@/lib/types";
import {
  fetchConversations,
  listSavedQueries,
  deleteSavedQuery,
  getDashboard,
  listAdminTeams,
  listAdminUsers,
} from "@/lib/api";
import StatCard from "@/components/StatCard";
import QuerySearch from "@/components/QuerySearch";
import ChartArea from "@/components/ChartArea";
import RecentConversations from "@/components/RecentConversations";
import SavedQueries from "@/components/SavedQueries";
import DashboardFilters from "@/components/DashboardFilters";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardPage() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const [data, setData] = useState<DashboardData | null>(null);
  const [filters, setFilters] = useState<FilterState>({ dateRange: "1y" });
  const [activeTab, setActiveTab] = useState<"recent" | "saved">("recent");
  // Team/user activity filters (admin only — pickers stay hidden otherwise).
  const [activityFilters, setActivityFilters] = useState<{
    teamId?: string;
    userId?: string;
  }>({});
  const [teams, setTeams] = useState<PickerItem[]>([]);
  const [users, setUsers] = useState<PickerItem[]>([]);

  // Best-effort load of the filter pickers on auth (admin endpoints 403 →
  // empty, which keeps the filter UI hidden for non-admins).
  useEffect(() => {
    if (status !== "authenticated") return;
    const token = (session as any)?.accessToken;
    if (!token) return;

    let cancelled = false;
    (async () => {
      const [t, u] = await Promise.all([
        listAdminTeams(token),
        listAdminUsers(token),
      ]);
      if (cancelled) return;
      setTeams(t);
      setUsers(u);
    })();
    return () => {
      cancelled = true;
    };
  }, [status, session]);

  useEffect(() => {
    // Session yuklenmediyse veya giris yapilmadiysa data getirmeyi bekle
    if (status === "loading") return;
    if (status === "unauthenticated") {
      return;
    }

    async function loadData() {
      try {
        const token = (session as any)?.accessToken;
        const dashboard = await getDashboard(token, {
          teamId: activityFilters.teamId,
          userId: activityFilters.userId,
        });

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
  }, [status, activityFilters.teamId, activityFilters.userId]);

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
      <div className="p-4 md:p-6 space-y-6 max-w-[1400px] mx-auto" aria-busy="true">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-12 w-full" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="h-[360px] w-full" />
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
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <h2 className="text-sm font-semibold text-gray-700">Workspace activity</h2>
            {(teams.length > 0 || users.length > 0) && (
              <DashboardFilters
                teams={teams}
                users={users}
                teamId={activityFilters.teamId}
                userId={activityFilters.userId}
                onChange={setActivityFilters}
              />
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {data.workspaceStats.map((stat) => (
              <StatCard key={stat.label} data={stat} />
            ))}
          </div>
          {data.tokenSplit && data.tokenSplit.total > 0 && (
            <p className="mt-2 text-xs text-gray-500">
              Today&apos;s tokens:{" "}
              <span className="font-medium text-blue-600">
                {data.tokenSplit.priced.toLocaleString()}
              </span>{" "}
              priced
              <span className="text-gray-300"> · </span>
              <span className="font-medium text-amber-600">
                {data.tokenSplit.unpriced.toLocaleString()}
              </span>{" "}
              unpriced <span className="text-gray-400">(self-hosted / $0)</span>
            </p>
          )}
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
