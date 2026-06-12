"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Settings, Save, AlertCircle, CheckCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TenantConfig {
  daily_token_limit: number;
  max_row_limit: number;
  source: "db" | "default";
}

export default function TenantConfigPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken;
  
  const [config, setConfig] = useState<TenantConfig | null>(null);
  const [tokenLimit, setTokenLimit] = useState(50000);
  const [rowLimit, setRowLimit] = useState(1000);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (token) {
      fetchConfig();
    }
  }, [token]);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/admin/tenant`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data: TenantConfig = await res.json();
        setConfig(data);
        setTokenLimit(data.daily_token_limit);
        setRowLimit(data.max_row_limit);
      }
    } catch (err) {
      console.error("Failed to fetch tenant config", err);
      setMessage({ type: "error", text: "Failed to load configuration" });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/admin/tenant`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          daily_token_limit: tokenLimit,
          max_row_limit: rowLimit,
        }),
      });
      
      if (res.ok) {
        const data: TenantConfig = await res.json();
        setConfig(data);
        setMessage({ type: "success", text: "Configuration saved successfully" });
      } else {
        const err = await res.json();
        setMessage({ type: "error", text: err.detail || "Failed to save configuration" });
      }
    } catch (err) {
      console.error("Failed to save tenant config", err);
      setMessage({ type: "error", text: "Failed to save configuration" });
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = config && (
    tokenLimit !== config.daily_token_limit || rowLimit !== config.max_row_limit
  );

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-2">
          <Settings className="w-6 h-6 text-blue-600" />
          Tenant Configuration
        </h1>
        <p className="text-gray-500">
          Manage system-wide limits and behavior for the current tenant.
        </p>
      </div>

      {/* Message */}
      {message && (
        <div
          className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${
            message.type === "success"
              ? "bg-green-50 text-green-700 border border-green-200"
              : "bg-red-50 text-red-700 border border-red-200"
          }`}
        >
          {message.type === "success" ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          {message.text}
        </div>
      )}

      {loading ? (
        <div className="bg-white border border-gray-200 p-8 rounded-xl shadow-sm">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-10 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-10 bg-gray-200 rounded"></div>
          </div>
        </div>
      ) : (
        <div className="space-y-6 bg-white border border-gray-200 p-8 rounded-xl shadow-sm">
          {/* Source indicator */}
          {config && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-500">Configuration source:</span>
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${
                  config.source === "db"
                    ? "bg-green-50 text-green-700"
                    : "bg-yellow-50 text-yellow-700"
                }`}
              >
                {config.source === "db" ? "Database" : "Default"}
              </span>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Daily Token Limit (Per User/Team)
            </label>
            <input
              type="number"
              value={tokenLimit}
              onChange={(e) => setTokenLimit(Number(e.target.value))}
              min={1000}
              max={10000000}
              className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
            <p className="text-xs text-gray-500 mt-2">
              Applies to all LLM requests including local/Ollama models. Range: 1,000 - 10,000,000
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Row Limit per Query
            </label>
            <input
              type="number"
              value={rowLimit}
              onChange={(e) => setRowLimit(Number(e.target.value))}
              min={100}
              max={1000000}
              className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
            <p className="text-xs text-gray-500 mt-2">
              Queries exceeding this limit will trigger a high-row artifact upload to MinIO. Range: 100 - 1,000,000
            </p>
          </div>

          <div className="pt-6 border-t border-gray-100 flex items-center justify-between">
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className={`px-6 py-2.5 rounded-lg font-medium transition-all flex items-center gap-2 ${
                saving || !hasChanges
                  ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow-md"
              }`}
            >
              <Save className="w-4 h-4" />
              {saving ? "Saving..." : "Save Configuration"}
            </button>
            
            {hasChanges && (
              <span className="text-sm text-yellow-600">
                You have unsaved changes
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
