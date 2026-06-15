"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Activity, Database, Server, RefreshCw, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ServiceHealth {
  status: "healthy" | "unhealthy" | "unknown";
  latency_ms?: number;
  error?: string;
}

interface SystemHealth {
  postgres: ServiceHealth;
  redis: ServiceHealth;
  keycloak: ServiceHealth;
  qdrant: ServiceHealth;
  litellm: ServiceHealth;
}

export default function SystemHealthPage() {
  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const router = useRouter();

  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/api/auth/signin");
      return;
    }

    if (token) {
      fetchHealth();
    }
  }, [status, token, router]);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/health`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (err) {
      console.error("Failed to fetch system health", err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "healthy":
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case "unhealthy":
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
    }
  };

  const services = [
    { key: "postgres", name: "PostgreSQL", icon: <Database className="w-5 h-5" />, desc: "Primary metadata and config database" },
    { key: "redis", name: "Redis", icon: <Server className="w-5 h-5" />, desc: "Caching, rate limiting, and pub/sub" },
    { key: "keycloak", name: "Keycloak", icon: <Server className="w-5 h-5" />, desc: "Identity, SSO, and RBAC" },
    { key: "qdrant", name: "Qdrant", icon: <Database className="w-5 h-5" />, desc: "Vector database for Mem0 semantic search" },
    { key: "litellm", name: "LiteLLM Proxy", icon: <Activity className="w-5 h-5" />, desc: "LLM routing, failover, and cost tracking" },
  ];

  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-800">System Health</h1>
          <Button onClick={fetchHealth} disabled={loading} variant="outline" size="sm">
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
            <h2 className="font-semibold text-gray-700">Infrastructure Services</h2>
            {health && (
              <span className="text-xs text-gray-500">
                All Systems: {Object.values(health).every(s => s.status === 'healthy') ? 'Operational' : 'Degraded'}
              </span>
            )}
          </div>
          
          <div className="divide-y divide-gray-100">
            {services.map((service) => {
              const data = health?.[service.key as keyof SystemHealth];
              
              return (
                <div key={service.key} className="p-6 flex items-start sm:items-center justify-between flex-col sm:flex-row gap-4">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 flex-shrink-0">
                      {service.icon}
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{service.name}</h3>
                      <p className="text-sm text-gray-500">{service.desc}</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-6 min-w-[200px] justify-end w-full sm:w-auto">
                    {loading ? (
                      <span className="text-sm text-gray-400">Checking...</span>
                    ) : data ? (
                      <>
                        <div className="text-right">
                          <div className="flex items-center gap-2 justify-end">
                            {getStatusIcon(data.status)}
                            <span className={`font-medium capitalize ${
                              data.status === 'healthy' ? 'text-green-700' : 
                              data.status === 'unhealthy' ? 'text-red-700' : 'text-yellow-700'
                            }`}>
                              {data.status}
                            </span>
                          </div>
                          {data.latency_ms !== undefined && (
                            <div className="text-xs text-gray-500 mt-1">
                              {data.latency_ms}ms latency
                            </div>
                          )}
                        </div>
                        {data.error && (
                          <div className="text-xs text-red-600 max-w-[200px] truncate" title={data.error}>
                            {data.error}
                          </div>
                        )}
                      </>
                    ) : (
                      <span className="text-sm text-gray-400">No data</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
