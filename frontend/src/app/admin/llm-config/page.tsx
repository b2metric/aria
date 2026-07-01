"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { Cpu, Save, SlidersHorizontal } from "lucide-react";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface OperationModel {
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

type OperationModels = Record<string, OperationModel>;

interface LLMConfig {
  provider: string;
  upstream_api_base: string | null;
  api_key_set: boolean;
  model_name: string;
  deployment_or_version: string | null;
  enabled: boolean;
  operation_models: OperationModels | null;
}

interface ModelCatalogEntry {
  id: string;
  provider: string;
}

// Per-operation LLM routing. Absent/empty → inherit the top-level Model Name.
const OPERATIONS: ReadonlyArray<{ key: string; label: string; hint: string }> = [
  { key: "sql_generation", label: "SQL Generation", hint: "Natural-language → SQL" },
  { key: "insight", label: "Insight", hint: "Narrative summary of results" },
  { key: "suggestion", label: "Suggestions", hint: "Follow-up question prompts" },
  { key: "chart", label: "Chart", hint: "Chart-type + encoding selection" },
];

export default function LLMConfigPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken;

  const [config, setConfig] = useState<LLMConfig | null>(null);
  const [provider, setProvider] = useState("openai");
  const [apiBase, setApiBase] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [modelName, setModelName] = useState("gpt-4");
  const [deployment, setDeployment] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [operationModels, setOperationModels] = useState<OperationModels>({});
  const [catalog, setCatalog] = useState<ModelCatalogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (!token) return;

    async function fetchConfig() {
      try {
        setLoading(true);
        const res = await fetch(`${API_BASE}/api/admin/llm-config`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data: LLMConfig = await res.json();
          setConfig(data);
          setProvider(data.provider);
          setApiBase(data.upstream_api_base || "");
          setModelName(data.model_name);
          setDeployment(data.deployment_or_version || "");
          setEnabled(data.enabled);
          setOperationModels(data.operation_models || {});
        }
      } catch (err) {
        console.error("Failed to fetch LLM config", err);
      } finally {
        setLoading(false);
      }
    }

    async function fetchCatalog() {
      try {
        const res = await fetch(`${API_BASE}/api/admin/llm-config/models`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data: ModelCatalogEntry[] = await res.json();
          setCatalog(data);
        }
      } catch (err) {
        console.error("Failed to fetch model catalog", err);
      }
    }

    fetchConfig();
    fetchCatalog();
  }, [token]);

  // Immutable update of a single operation's routing. Empty model → drop the entry
  // (so the operation inherits the top-level Model Name), keeping the payload clean.
  const setOperationModel = (op: string, patch: OperationModel) => {
    setOperationModels((prev) => {
      const next: OperationModels = { ...prev, [op]: { ...prev[op], ...patch } };
      const entry = next[op];
      if (!entry.model && entry.temperature === undefined && entry.max_tokens === undefined) {
        const { [op]: _dropped, ...rest } = next;
        return rest;
      }
      return next;
    });
  };

  const handleSave = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setMessage(null);

      const payload = {
        provider,
        upstream_api_base: apiBase || null,
        upstream_api_key: apiKey || null,
        model_name: modelName,
        deployment_or_version: deployment || null,
        enabled,
        operation_models: Object.keys(operationModels).length > 0 ? operationModels : null,
      };

      const res = await fetch(`${API_BASE}/api/admin/llm-config`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data: LLMConfig = await res.json();
        setConfig(data);
        setOperationModels(data.operation_models || {});
        setApiKey(""); // Clear the input field for security
        setMessage({ type: "success", text: "LLM configuration saved successfully" });
      } else {
        setMessage({ type: "error", text: "Failed to save configuration" });
      }
    } catch (err) {
      console.error("Failed to save LLM config", err);
      setMessage({ type: "error", text: "An unexpected error occurred" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-2">
          <Cpu className="w-6 h-6 text-indigo-600" />
          LLM Provider Configuration (BYOK)
        </h1>
        <p className="text-gray-500">
          Bring your own LLM key. This will override the global ARIA platform key for your workspace.
        </p>
      </div>

      {message && (
        <div className={`p-4 rounded-md mb-6 ${message.type === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
          {message.text}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-medium text-gray-900">Enable Custom LLM</h2>
            <p className="text-sm text-gray-500">Route queries through your dedicated provider</p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              className="sr-only peer"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
          </label>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-gray-100">
          <div className="col-span-1 md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              disabled={!enabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100"
            >
              <option value="openai">OpenAI</option>
              <option value="azure">Azure OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="gemini">Google Gemini</option>
              <option value="litellm">Custom Proxy (LiteLLM)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Model Name</label>
            <input
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              disabled={!enabled}
              placeholder="e.g. gpt-4, claude-3-opus"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              disabled={!enabled}
              placeholder={config?.api_key_set ? "•••••••••••••••• (Leave blank to keep)" : "sk-..."}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100"
            />
            {config?.api_key_set && (
              <p className="mt-1 text-xs text-green-600">Securely stored. Enter new key to update.</p>
            )}
          </div>

          <div className="col-span-1 md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">API Base URL (Optional)</label>
            <input
              type="text"
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              disabled={!enabled}
              placeholder="e.g. https://api.openai.com/v1"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100"
            />
          </div>

          {provider === "azure" && (
            <div className="col-span-1 md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Azure Deployment Name</label>
              <input
                type="text"
                value={deployment}
                onChange={(e) => setDeployment(e.target.value)}
                disabled={!enabled}
                placeholder="e.g. my-gpt4-deployment"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100"
              />
            </div>
          )}
        </div>

        <div className="pt-6 border-t border-gray-100">
          <div className="mb-4">
            <h2 className="text-lg font-medium text-gray-900 flex items-center gap-2">
              <SlidersHorizontal className="w-5 h-5 text-indigo-600" />
              Per-Operation Models
            </h2>
            <p className="text-sm text-gray-500">
              Route individual pipeline steps to specific models. Leave a step on{" "}
              <span className="font-medium">Default</span> to inherit the Model Name above.
            </p>
          </div>

          <div className="space-y-3">
            {OPERATIONS.map((op) => {
              const current = operationModels[op.key] || {};
              const modelValue = current.model || "";
              // Show the stored model even if the live catalog doesn't list it (proxy down / custom alias).
              const inCatalog = catalog.some((c) => c.id === modelValue);
              return (
                <div
                  key={op.key}
                  className="grid grid-cols-1 md:grid-cols-3 gap-3 items-center rounded-md border border-gray-100 bg-gray-50/60 p-3"
                >
                  <div className="md:col-span-1">
                    <div className="text-sm font-medium text-gray-800">{op.label}</div>
                    <div className="text-xs text-gray-500">{op.hint}</div>
                  </div>

                  <div className="md:col-span-1">
                    <select
                      aria-label={`${op.label} model`}
                      value={modelValue}
                      onChange={(e) => setOperationModel(op.key, { model: e.target.value || undefined })}
                      disabled={!enabled}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100 text-sm"
                    >
                      <option value="">Default (inherit)</option>
                      {modelValue && !inCatalog && <option value={modelValue}>{modelValue}</option>}
                      {catalog.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.provider} · {c.id}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="md:col-span-1 grid grid-cols-2 gap-2">
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="2"
                      aria-label={`${op.label} temperature`}
                      value={current.temperature ?? ""}
                      onChange={(e) =>
                        setOperationModel(op.key, {
                          temperature: e.target.value === "" ? undefined : Number(e.target.value),
                        })
                      }
                      disabled={!enabled}
                      placeholder="temp"
                      className="w-full px-2 py-2 border border-gray-300 rounded-md bg-white focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100 text-sm"
                    />
                    <input
                      type="number"
                      step="1"
                      min="1"
                      aria-label={`${op.label} max tokens`}
                      value={current.max_tokens ?? ""}
                      onChange={(e) =>
                        setOperationModel(op.key, {
                          max_tokens: e.target.value === "" ? undefined : Number(e.target.value),
                        })
                      }
                      disabled={!enabled}
                      placeholder="max tok"
                      className="w-full px-2 py-2 border border-gray-300 rounded-md bg-white focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100 text-sm"
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="pt-6 border-t border-gray-100 flex justify-end">
          <button
            onClick={handleSave}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-[#ffffff] rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {loading ? "Saving..." : "Save Configuration"}
          </button>
        </div>
      </div>
    </div>
  );
}
