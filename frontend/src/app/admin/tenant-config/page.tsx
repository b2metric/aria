"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Settings, Save, AlertCircle, CheckCircle, Database } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DBConfig {
  db_type: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password?: string;
}

interface TenantConfig {
  daily_token_limit: number;
  max_row_limit: number;
  source: "db" | "default";
  db_config?: DBConfig;
}

export default function TenantConfigPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken;

  const [config, setConfig] = useState<TenantConfig | null>(null);
  const [tokenLimit, setTokenLimit] = useState(50000);
  const [rowLimit, setRowLimit] = useState(1000);

  const [dbType, setDbType] = useState("postgresql");
  const [dbHost, setDbHost] = useState("");
  const [dbPort, setDbPort] = useState(5432);
  const [dbDatabase, setDbDatabase] = useState("");
  const [dbUsername, setDbUsername] = useState("");
  const [dbPassword, setDbPassword] = useState("");

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
        if (data.db_config) {
          setDbType(data.db_config.db_type);
          setDbHost(data.db_config.host);
          setDbPort(data.db_config.port);
          setDbDatabase(data.db_config.database);
          setDbUsername(data.db_config.username);
        }
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
      const payload: any = {
        daily_token_limit: tokenLimit,
        max_row_limit: rowLimit,
      };

      if (dbHost && dbDatabase && dbUsername) {
        payload.db_config = {
          db_type: dbType,
          host: dbHost,
          port: dbPort,
          database: dbDatabase,
          username: dbUsername,
        };
        if (dbPassword) {
          payload.db_config.password = dbPassword;
        }
      }

      const res = await fetch(`${API_BASE}/api/admin/tenant`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data: TenantConfig = await res.json();
        setConfig(data);
        setMessage({ type: "success", text: "Configuration saved successfully" });
        setDbPassword(""); // clear password after save
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

  const hasChanges = true; // Simplified for now since we have many fields

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-2">
          <Settings className="w-6 h-6 text-blue-600" />
          Tenant Configuration
        </h1>
        <p className="text-gray-500">
          Manage system-wide limits and customer database connections.
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
        <div className="space-y-8">
          {/* Limits Section */}
          <div className="bg-white border border-gray-200 p-8 rounded-xl shadow-sm space-y-6">
            <div className="flex items-center gap-2 pb-4 border-b border-gray-100">
              <Settings className="w-5 h-5 text-gray-400" />
              <h2 className="text-lg font-semibold text-gray-800">System Limits</h2>
              {config && (
                <span
                  className={`ml-auto px-2 py-0.5 rounded text-xs font-medium ${
                    config.source === "db"
                      ? "bg-green-50 text-green-700"
                      : "bg-yellow-50 text-yellow-700"
                  }`}
                >
                  {config.source === "db" ? "DB Active" : "Defaults"}
                </span>
              )}
            </div>

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
                className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
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
                className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
              />
              <p className="text-xs text-gray-500 mt-2">
                Queries exceeding this limit will trigger a high-row artifact upload to MinIO. Range: 100 - 1,000,000
              </p>
            </div>
          </div>

          {/* Database Connection Section */}
          <div className="bg-white border border-gray-200 p-8 rounded-xl shadow-sm space-y-6">
            <div className="flex items-center gap-2 pb-4 border-b border-gray-100">
              <Database className="w-5 h-5 text-gray-400" />
              <h2 className="text-lg font-semibold text-gray-800">Customer Database Connection</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Database Type</label>
                <select
                  value={dbType}
                  onChange={(e) => setDbType(e.target.value)}
                  className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                >
                  <option value="postgresql">PostgreSQL</option>
                  <option value="oracle">Oracle</option>
                  <option value="mysql">MySQL</option>
                  <option value="mssql">SQL Server (MSSQL)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Host</label>
                <input
                  type="text"
                  value={dbHost}
                  onChange={(e) => setDbHost(e.target.value)}
                  placeholder="e.g. 192.168.1.100 or aws.rds..."
                  className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Port</label>
                <input
                  type="number"
                  value={dbPort}
                  onChange={(e) => setDbPort(Number(e.target.value))}
                  className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Database Name (or SID/Service)</label>
                <input
                  type="text"
                  value={dbDatabase}
                  onChange={(e) => setDbDatabase(e.target.value)}
                  className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Username</label>
                <input
                  type="text"
                  value={dbUsername}
                  onChange={(e) => setDbUsername(e.target.value)}
                  className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
                <input
                  type="password"
                  value={dbPassword}
                  onChange={(e) => setDbPassword(e.target.value)}
                  placeholder="Leave empty to keep existing password"
                  className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Note: Database passwords are encrypted at rest using AES-256 (Fernet) before storing in PostgreSQL.
            </p>
          </div>

          <div className="flex items-center justify-end">
            <button
              onClick={handleSave}
              disabled={saving}
              className={`px-8 py-3 rounded-lg font-medium transition-all flex items-center gap-2 ${
                saving
                  ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow-md"
              }`}
            >
              <Save className="w-5 h-5" />
              {saving ? "Saving..." : "Save Configuration"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
