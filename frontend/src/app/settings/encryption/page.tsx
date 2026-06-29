"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import {
  ShieldAlert,
  Save,
  Loader2,
  Key,
  RefreshCw,
  CheckCircle2,
  XCircle,
  History,
} from "lucide-react";

interface EncryptionStatus {
  provider: string;
  key_uri: string | null;
  is_active: boolean;
  reachable: boolean;
}

interface AuditEntry {
  id: string;
  action: string;
  created_at: string;
  details: Record<string, unknown> | null;
}

export default function EncryptionSettings() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken;
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [config, setConfig] = useState({ provider: "app", key_uri: "" });
  const [status, setStatus] = useState<EncryptionStatus | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);

  const fetchStatus = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/api/admin/encryption/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data: EncryptionStatus = await res.json();
        setStatus(data);
        setConfig({ provider: data.provider || "app", key_uri: data.key_uri || "" });
      }
    } catch (err) {
      console.error("Failed to load encryption status", err);
    }
  }, [API_BASE, token]);

  const fetchAudit = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/api/admin/audit-logs?limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        const rows: AuditEntry[] = data.data || data || [];
        setAudit(rows.filter((r) => (r.action || "").startsWith("cmek_")).slice(0, 10));
      }
    } catch (err) {
      console.error("Failed to load CMEK audit trail", err);
    }
  }, [API_BASE, token]);

  useEffect(() => {
    if (!token) return;
    void (async () => {
      setLoading(true);
      await Promise.all([fetchStatus(), fetchAudit()]);
      setLoading(false);
    })();
  }, [token, fetchStatus, fetchAudit]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/admin/encryption`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(config),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to update encryption configuration");
      }
      setMessage({ type: "success", text: "Encryption configuration updated and DEK re-wrapped." });
      await Promise.all([fetchStatus(), fetchAudit()]);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  };

  const handleRotate = async () => {
    if (!token) return;
    if (!confirm("Rotate the encryption key now? The DEK will be re-wrapped under the latest key version.")) {
      return;
    }
    setRotating(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/admin/encryption/rotate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Key rotation failed");
      }
      setMessage({ type: "success", text: "Key rotated successfully. Existing data remains decryptable." });
      await Promise.all([fetchStatus(), fetchAudit()]);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setRotating(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex justify-center">
        <Loader2 className="animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-blue-600" />
            Encryption (CMEK)
          </h1>
          <p className="text-gray-500 mt-1">Manage Customer Managed Encryption Keys for your workspace.</p>
        </div>
      </div>

      {message && (
        <div
          className={`p-4 rounded-md ${
            message.type === "success"
              ? "bg-green-50 text-green-700 border border-green-200"
              : "bg-red-50 text-red-700 border border-red-200"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Status / health */}
      {status && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-500">Active provider</div>
            <div className="text-lg font-semibold text-gray-900 uppercase">{status.provider}</div>
            {status.key_uri && (
              <div className="mt-1 text-xs text-gray-500 font-mono break-all max-w-xl">{status.key_uri}</div>
            )}
          </div>
          <div className="flex items-center gap-4">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${
                status.reachable ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
              }`}
            >
              {status.reachable ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
              {status.reachable ? "Key reachable" : "Key unreachable"}
            </span>
            <button
              onClick={handleRotate}
              disabled={rotating}
              className="flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              title="Re-wrap the DEK under the latest key version"
            >
              {rotating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              Rotate key
            </button>
          </div>
        </div>
      )}

      {/* Provider configuration */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="p-6 border-b border-gray-200 bg-gray-50/50">
          <h2 className="text-lg font-medium text-gray-900 flex items-center gap-2">
            <Key className="w-5 h-5 text-gray-500" />
            Key Management Provider
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            By default, ARIA secures your data using an application-level key (App KEK). You can
            configure a cloud provider KMS to wrap your tenant&apos;s Data Encryption Key (DEK).
          </p>
        </div>

        <div className="p-6">
          <form onSubmit={handleSave} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">KMS Provider</label>
              <select
                value={config.provider}
                onChange={(e) => setConfig({ ...config, provider: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="app">ARIA Default (App KEK)</option>
                <option value="aws">AWS KMS</option>
                <option value="gcp">Google Cloud KMS</option>
                <option value="azure">Azure Key Vault</option>
              </select>
            </div>

            {config.provider !== "app" && (
              <div className="animate-in fade-in slide-in-from-top-4 duration-300">
                <label className="block text-sm font-medium text-gray-700 mb-1">Key URI / ARN</label>
                <input
                  type="text"
                  required
                  value={config.key_uri}
                  onChange={(e) => setConfig({ ...config, key_uri: e.target.value })}
                  placeholder={
                    config.provider === "aws"
                      ? "arn:aws:kms:region:account:key/id"
                      : config.provider === "gcp"
                        ? "projects/*/locations/*/keyRings/*/cryptoKeys/*"
                        : "https://vault-name.vault.azure.net/keys/key-name/version"
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  The key is validated (a wrap/unwrap probe) before saving — an unreachable key is rejected.
                </p>
              </div>
            )}

            <div className="pt-4 flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-[#ffffff] rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save Configuration
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* CMEK config-change audit trail */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50/50">
          <h2 className="text-lg font-medium text-gray-900 flex items-center gap-2">
            <History className="w-5 h-5 text-gray-500" />
            Key Configuration History
          </h2>
        </div>
        {audit.length === 0 ? (
          <div className="p-6 text-sm text-gray-500">No key configuration changes recorded yet.</div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {audit.map((a) => {
              const d = a.details || {};
              const label =
                a.action === "cmek_key_rotation"
                  ? `Key rotated (${d.provider ?? "?"})`
                  : `Provider changed: ${d.old_provider ?? "?"} → ${d.new_provider ?? "?"}`;
              return (
                <li key={a.id} className="px-6 py-3 flex items-center justify-between text-sm">
                  <span className="text-gray-800">{label}</span>
                  <span className="text-gray-400 text-xs">
                    {a.created_at ? new Date(a.created_at).toLocaleString() : ""}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
