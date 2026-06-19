"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { ShieldAlert, Save, Loader2, Key } from "lucide-react";

export default function EncryptionSettings() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken;
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{type: "success" | "error", text: string} | null>(null);
  
  const [config, setConfig] = useState({
    provider: "app",
    key_uri: "",
  });

  useEffect(() => {
    if (!token) return;
    const fetchConfig = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/admin/encryption`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setConfig({
            provider: data.provider || "app",
            key_uri: data.key_uri || "",
          });
        }
      } catch (err) {
        console.error("Failed to load encryption config", err);
      } finally {
        setLoading(false);
      }
    };
    fetchConfig();
  }, [token]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/api/admin/encryption`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(config)
      });
      
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to update encryption configuration");
      }
      
      setMessage({ type: "success", text: "Encryption configuration updated successfully." });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-blue-600" /></div>;
  }

  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-blue-600" />
            Encryption (CMEK)
          </h1>
          <p className="text-gray-500 mt-1">Manage Customer Managed Encryption Keys for your workspace.</p>
        </div>
      </div>
      
      {message && (
        <div className={`p-4 rounded-md mb-6 ${message.type === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"}`}>
          {message.text}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="p-6 border-b border-gray-200 bg-gray-50/50">
          <h2 className="text-lg font-medium text-gray-900 flex items-center gap-2">
            <Key className="w-5 h-5 text-gray-500" />
            Key Management Provider
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            By default, ARIA secures your data using an application-level key (App KEK).
            You can configure a cloud provider KMS to wrap your tenant&apos;s Data Encryption Key (DEK).
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
                    config.provider === "aws" ? "arn:aws:kms:region:account:key/id" :
                    config.provider === "gcp" ? "projects/*/locations/*/keyRings/*/cryptoKeys/*" :
                    "https://vault-name.vault.azure.net/keys/key-name/version"
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Enter the fully qualified resource name or URI for your customer-managed key.
                </p>
              </div>
            )}

            <div className="pt-4 flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save Configuration
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
