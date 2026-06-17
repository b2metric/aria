"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Activity, CheckCircle2, AlertCircle, AlertTriangle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface HealthStatus {
  status: "healthy" | "unhealthy" | "warning" | "unknown";
  latency_ms?: number;
  error?: string;
}

export default function HealthDashboardPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken;
  const [healthData, setHealthData] = useState<Record<string, HealthStatus> | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/admin/health`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setHealthData(data);
      } else {
        console.error("Health check failed", await res.text());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchHealth();
  }, [token]);

  const renderStatusIcon = (status: string) => {
    switch (status) {
      case "healthy": return <CheckCircle2 className="w-6 h-6 text-green-500" />;
      case "warning": return <AlertTriangle className="w-6 h-6 text-yellow-500" />;
      case "unhealthy": return <AlertCircle className="w-6 h-6 text-red-500" />;
      default: return <Activity className="w-6 h-6 text-gray-400" />;
    }
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Activity className="w-6 h-6 text-blue-600" />
            System Health Dashboard
          </h1>
          <p className="text-gray-500 mt-1">Real-time status of backend dependencies</p>
        </div>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="px-4 py-2 bg-blue-50 text-blue-600 font-medium rounded hover:bg-blue-100 disabled:opacity-50"
        >
          {loading ? "Checking..." : "Refresh"}
        </button>
      </div>

      {loading && !healthData ? (
        <div className="animate-pulse flex gap-4">
          <div className="h-32 bg-gray-200 rounded-xl w-full"></div>
        </div>
      ) : healthData ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Object.entries(healthData).map(([service, info]) => {
            const displayName = service === "customer_dbs" ? "Customer Databases" : service.replace(/_/g, " ");
            return (
              <div key={service} className="p-5 bg-white border border-gray-200 rounded-xl shadow-sm flex flex-col gap-3">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-lg text-gray-800 capitalize">{displayName}</span>
                  {renderStatusIcon(info.status)}
                </div>
                <div className="flex justify-between text-sm text-gray-600">
                  <span>Status: <span className="font-medium uppercase">{info.status}</span></span>
                  {info.latency_ms !== undefined && <span>{info.latency_ms} ms</span>}
                </div>
                {info.error && (
                  <div className="mt-2 text-xs p-2 bg-red-50 text-red-700 rounded border border-red-100 overflow-x-auto">
                    {info.error}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center text-gray-500 mt-10">Failed to load health data.</div>
      )}
    </div>
  );
}
