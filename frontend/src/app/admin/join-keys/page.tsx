"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Link2, Save, Search, AlertTriangle, CheckCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type JoinKey = {
  column: string;
  member_tables: string[];
  occurrences: number;
  is_join_key: boolean;
  grain: string | null;
  note: string | null;
};

export default function JoinKeysPage() {
  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const router = useRouter();

  const [keys, setKeys] = useState<JoinKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [inferring, setInferring] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [search, setSearch] = useState("");
  const [onlySelected, setOnlySelected] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") router.push("/api/auth/signin");
  }, [status, router]);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/workspaces/vault/join-keys?workspace_id=default`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setKeys(Array.isArray(data.keys) ? data.keys : []);
      }
    } catch (err) {
      console.error("Failed to load join keys", err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const update = (column: string, patch: Partial<JoinKey>) =>
    setKeys((prev) => prev.map((k) => (k.column === column ? { ...k, ...patch } : k)));

  const handleInferGrains = async () => {
    if (!token) return;
    try {
      setInferring(true);
      setResult(null);
      const res = await fetch(
        `${API_BASE}/api/workspaces/vault/join-keys/infer-grains?workspace_id=default`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } },
      );
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.keys)) setKeys(data.keys);
        setResult({ ok: true, msg: `LLM filled ${data.filled ?? 0} grain label(s). Review/edit, then Save.` });
      } else {
        setResult({ ok: false, msg: `Grain inference failed (HTTP ${res.status})` });
      }
    } catch (err) {
      console.error("Grain inference failed", err);
      setResult({ ok: false, msg: "Grain inference failed. Please try again." });
    } finally {
      setInferring(false);
    }
  };

  const handleSave = async () => {
    if (!token) return;
    try {
      setSaving(true);
      setResult(null);
      const res = await fetch(`${API_BASE}/api/workspaces/vault/join-keys?workspace_id=default`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          keys: keys.map((k) => ({
            column: k.column,
            is_join_key: k.is_join_key,
            grain: k.grain,
            note: k.note,
          })),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setResult({ ok: true, msg: `Saved ${data.saved ?? 0} curated columns. The LLM now uses confirmed keys for JOINs.` });
      } else {
        let detail = `Save failed (HTTP ${res.status})`;
        try {
          const e = await res.json();
          if (typeof e?.detail === "string") detail = e.detail;
        } catch {
          // no body
        }
        setResult({ ok: false, msg: detail });
      }
    } catch (err) {
      console.error("Failed to save join keys", err);
      setResult({ ok: false, msg: "Save failed. Please try again." });
    } finally {
      setSaving(false);
    }
  };

  const q = search.trim().toLowerCase();
  const visible = keys.filter((k) => {
    if (onlySelected && !k.is_join_key) return false;
    if (!q) return true;
    return (
      k.column.toLowerCase().includes(q) ||
      k.member_tables.some((t) => t.toLowerCase().includes(q))
    );
  });
  const confirmedCount = keys.filter((k) => k.is_join_key).length;

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Link2 className="w-6 h-6 text-blue-600" />
            Conformed Join Keys
          </h1>
          <p className="text-gray-500 mt-1 max-w-2xl">
            This database has no enforced foreign keys. Columns shared across tables (e.g.{" "}
            <span className="font-mono">SUBNO</span>, <span className="font-mono">CONTRNO</span>) are
            the real join keys. Mark which ones the assistant should use for JOINs and set their grain.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleInferGrains} disabled={loading || inferring} title="Use the LLM to infer a grain label for each shared column from its vault description">
            <Sparkles className={`w-4 h-4 mr-2 ${inferring ? "animate-pulse" : ""}`} />
            {inferring ? "Inferring..." : "Auto-fill grains (LLM)"}
          </Button>
          <Button onClick={handleSave} disabled={loading || saving} className="bg-blue-600 hover:bg-blue-700">
            <Save className={`w-4 h-4 mr-2 ${saving ? "animate-pulse" : ""}`} />
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      </div>

      {result && (
        <div
          role="status"
          className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${
            result.ok ? "border-green-200 bg-green-50 text-green-700" : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          {result.ok ? <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />}
          <span className="break-words">{result.msg}</span>
        </div>
      )}

      <Card className="shadow-sm">
        <CardHeader className="pb-4 border-b border-gray-100 bg-gray-50/50">
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Link2 className="w-5 h-5 text-blue-600" />
                Shared columns ({keys.length})
              </CardTitle>
              <CardDescription className="mt-1">
                Auto-detected from the vault — columns present in ≥ 2 tables.
              </CardDescription>
            </div>
            <div className="text-sm font-medium text-gray-500 bg-white px-3 py-1 rounded-full border border-gray-200">
              {confirmedCount} confirmed
            </div>
          </div>
          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative w-full sm:max-w-xs">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search column or table…"
                className="pl-9"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <Checkbox checked={onlySelected} onCheckedChange={() => setOnlySelected((v) => !v)} />
              Confirmed only
            </label>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Loading…</div>
          ) : visible.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No shared columns match.</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {visible.map((k) => (
                <div key={k.column} className="p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start gap-4">
                    <Checkbox
                      className="mt-1"
                      checked={k.is_join_key}
                      onCheckedChange={() => update(k.column, { is_join_key: !k.is_join_key })}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold font-mono text-gray-900">{k.column}</span>
                        <span className="text-xs text-gray-400">in {k.occurrences} tables</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5 break-words">
                        {k.member_tables.join(", ")}
                      </p>
                      {k.is_join_key && (
                        <div className="mt-3 flex flex-col sm:flex-row gap-2">
                          <Input
                            value={k.grain ?? ""}
                            onChange={(e) => update(k.column, { grain: e.target.value || null })}
                            placeholder="grain (LLM-filled, e.g. line (MSISDN)) — editable"
                            className="sm:w-64"
                          />
                          <Input
                            value={k.note ?? ""}
                            onChange={(e) => update(k.column, { note: e.target.value || null })}
                            placeholder="note (e.g. join facts to FCT_PREP_MASTER for demographics)"
                            className="flex-1"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
