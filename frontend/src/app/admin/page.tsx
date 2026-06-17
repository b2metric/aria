"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Users, MessagesSquare, Zap, Target } from "lucide-react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Metrics {
  total_users: number;
  active_teams: number;
  queries_today: number;
  tokens_used_today: number;
}

export default function AdminDashboardPage() {
  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const router = useRouter();

  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/api/auth/signin");
      return;
    }

    if (token) {
      fetchMetrics();
    }
  }, [status, token, router]);

  const fetchMetrics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/admin/metrics`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error("Failed to fetch metrics", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 p-8 overflow-y-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-800">Overview</h1>
        <p>Loading dashboard metrics...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-800">Admin Overview</h1>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Total Users */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col items-center text-center">
            <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-4">
              <Users className="w-6 h-6" />
            </div>
            <h3 className="text-gray-500 text-sm font-medium mb-1">Total Users</h3>
            <span className="text-3xl font-bold text-gray-900">{metrics?.total_users || 0}</span>
          </div>

          {/* Active Teams */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col items-center text-center">
            <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mb-4">
              <Target className="w-6 h-6" />
            </div>
            <h3 className="text-gray-500 text-sm font-medium mb-1">Active Teams</h3>
            <span className="text-3xl font-bold text-gray-900">{metrics?.active_teams || 0}</span>
          </div>

          {/* Queries Today */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col items-center text-center">
            <div className="w-12 h-12 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-4">
              <MessagesSquare className="w-6 h-6" />
            </div>
            <h3 className="text-gray-500 text-sm font-medium mb-1">Queries Today</h3>
            <span className="text-3xl font-bold text-gray-900">{metrics?.queries_today || 0}</span>
          </div>

          {/* Tokens Used */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col items-center text-center">
            <div className="w-12 h-12 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center mb-4">
              <Zap className="w-6 h-6" />
            </div>
            <h3 className="text-gray-500 text-sm font-medium mb-1">Tokens Used Today</h3>
            <span className="text-3xl font-bold text-gray-900">{metrics?.tokens_used_today || 0}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-bold mb-4">System Status</h3>
            <p className="text-gray-600 text-sm">
              Use the System Health tab in the sidebar to check the detailed status of database connections, Redis, Keycloak, and other infrastructure dependencies.
            </p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-bold mb-4">Quick Links</h3>
            <div className="flex flex-col gap-2">
              <a href="/admin/users" className="text-blue-600 hover:underline text-sm font-medium">Manage Users & Teams &rarr;</a>
              <a href="/admin/tenant-config" className="text-blue-600 hover:underline text-sm font-medium">Update Token Limits &rarr;</a>
              <a href="/admin/audit-log" className="text-blue-600 hover:underline text-sm font-medium">View System Audit Logs &rarr;</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
