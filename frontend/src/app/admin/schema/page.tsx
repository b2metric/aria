"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Search, Database, Table as TableIcon, Edit2, Check, X, FileText, Link as LinkIcon, Key, ChevronRight, RefreshCw, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type TableSummary = {
  table_name: string;
  description: string;
  business_name: string;
  keywords: string[];
  column_count: number;
  data_domain: string;
};

type TableColumn = {
  name: string;
  type: string;
  nullable: boolean;
  is_pk: boolean;
  description: string;
};

type TableRelationship = {
  raw: string;
};

type TableDetail = {
  table_name: string;
  description: string;
  business_name: string;
  keywords: string[];
  data_domain: string;
  column_count: number;
  columns: TableColumn[];
  relationships: TableRelationship[];
  example_queries: { question: string; answer: string; sql: string }[];
  sampled_values: Record<string, string[]>;
  enriched_at: string;
  generated_at: string;
};

type LlmColumnDraft = {
  name: string;
  current_description: string | null;
  suggested_description: string | null;
  is_empty: boolean;
};

type LlmDraft = {
  table_name: string;
  current_description: string | null;
  suggested_description: string | null;
  current_keywords: string[];
  suggested_keywords: string[];
  columns: LlmColumnDraft[];
  relationships: {
    source_column: string;
    target_table: string;
    target_column: string;
    relationship_type: string;
    description: string | null;
    confidence: number;
  }[];
  language: string;
  status: string;
  error: string | null;
};

export default function SchemaPage() {
  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const isAdmin = (session as any)?.user?.roles?.includes("admin") || (session as any)?.user?.role === "admin";
  const workspaceId = (session as any)?.user?.workspaceId || "default";
  const router = useRouter();

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/api/auth/signin');
    }
  }, [status, router]);

  const [tables, setTables] = useState<TableSummary[]>([]);
  const [selectedTable, setSelectedTable] = useState<TableDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  
  // Editing state
  const [editingField, setEditingField] = useState<{ type: 'table' | 'column' | 'keywords', name: string } | null>(null);
  const [editValue, setEditValue] = useState("");

  const [addingRel, setAddingRel] = useState(false);
  const [relSourceCol, setRelSourceCol] = useState("");
  const [relTargetTable, setRelTargetTable] = useState("");
  const [relTargetCol, setRelTargetCol] = useState("");

  const fetchTables = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/workspaces/vault/tables?workspace_id=${workspaceId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setTables(data);
      }
    } catch (err) {
      console.error("Failed to fetch tables", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void (async () => {
      await fetchTables();
    })();
  }, [token]);

  const fetchTableDetail = async (tableName: string) => {
    try {
      setLoadingDetail(true);
      const res = await fetch(`${API_BASE}/api/workspaces/vault/tables/${tableName}?workspace_id=${workspaceId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedTable(data);
      }
    } catch (err) {
      console.error(`Failed to fetch table ${tableName}`, err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleUpdateKeywords = async (tableName: string, newKeywordsStr: string) => {
    if (!isAdmin) return;
    try {
      const keywordsArray = newKeywordsStr.split(",").map(k => k.trim()).filter(k => k);
      const res = await fetch(`${API_BASE}/api/workspaces/vault/tables/${tableName}?workspace_id=${workspaceId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          table_name: tableName,
          keywords: keywordsArray,
        }),
      });

      if (res.ok) {
        if (selectedTable) {
          setSelectedTable({ ...selectedTable, keywords: keywordsArray });
        }
        setTables(tables.map(t => t.table_name === tableName ? { ...t, keywords: keywordsArray } : t));
        setEditingField(null);
      }
    } catch (err) {
      console.error("Failed to update keywords", err);
    }
  };

  const handleAddRelationship = async (
    sourceTable: string,
    sourceColArg?: string,
    targetTableArg?: string,
    targetColArg?: string,
  ) => {
    if (!isAdmin) return;
    // Accept explicit args (e.g. from an LLM-draft Accept click). Falling back
    // to state would read STALE values because setState is async — that was the
    // bug that wrote empty `` -> `.` relationships.
    const sourceCol = (sourceColArg ?? relSourceCol).trim();
    const targetTable = (targetTableArg ?? relTargetTable).trim();
    const targetCol = (targetColArg ?? relTargetCol).trim();
    if (!sourceTable || !sourceCol || !targetTable || !targetCol) {
      alert("Relationship needs source column, target table and target column.");
      return;
    }
    try {
      const qs = new URLSearchParams({
        source_table: sourceTable,
        source_column: sourceCol,
        target_table: targetTable,
        target_column: targetCol,
        workspace_id: workspaceId,
      });
      const res = await fetch(`${API_BASE}/api/workspaces/vault/enrich/relationship?${qs.toString()}`, {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        }
      });

      if (res.ok) {
        // Optimistic UI update or re-fetch
        fetchTableDetail(sourceTable);
        setAddingRel(false);
        setRelSourceCol("");
        setRelTargetTable("");
        setRelTargetCol("");
      } else {
        alert("Failed to add relationship");
      }
    } catch (err) {
      console.error("Failed to add relationship", err);
    }
  };

  const handleDeleteRelationship = async (sourceTable: string, raw: string) => {
    if (!isAdmin) return;
    if (!confirm(`Remove this relationship?\n\n${raw}`)) return;
    try {
      const qs = new URLSearchParams({
        source_table: sourceTable,
        raw,
        workspace_id: workspaceId,
      });
      const res = await fetch(`${API_BASE}/api/workspaces/vault/relationship?${qs.toString()}`, {
        method: "DELETE",
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      if (res.ok) {
        fetchTableDetail(sourceTable);
      } else {
        alert("Failed to remove relationship");
      }
    } catch (err) {
      console.error("Failed to remove relationship", err);
    }
  };

  // ── Example queries (add / remove) ──────────────────────────────────────
  const [addingEq, setAddingEq] = useState(false);
  const [eqQuestion, setEqQuestion] = useState("");
  const [eqAnswer, setEqAnswer] = useState("");
  const [eqSql, setEqSql] = useState("");

  const handleAddExampleQuery = async () => {
    if (!isAdmin || !selectedTable) return;
    if (!eqQuestion.trim() || !eqSql.trim()) {
      alert("Question and SQL are both required.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/workspaces/vault/example-query?workspace_id=${workspaceId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ source_table: selectedTable.table_name, question: eqQuestion, answer: eqAnswer, sql: eqSql }),
      });
      if (res.ok) {
        setAddingEq(false);
        setEqQuestion("");
        setEqAnswer("");
        setEqSql("");
        fetchTableDetail(selectedTable.table_name);
      } else {
        alert("Failed to add example query");
      }
    } catch (err) {
      console.error("Failed to add example query", err);
    }
  };

  const handleDeleteExampleQuery = async (question: string) => {
    if (!isAdmin || !selectedTable) return;
    if (!confirm(`Remove this example query?\n\n${question}`)) return;
    try {
      const qs = new URLSearchParams({
        source_table: selectedTable.table_name,
        question,
        workspace_id: workspaceId,
      });
      const res = await fetch(`${API_BASE}/api/workspaces/vault/example-query?${qs.toString()}`, {
        method: "DELETE",
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      if (res.ok) fetchTableDetail(selectedTable.table_name);
      else alert("Failed to remove example query");
    } catch (err) {
      console.error("Failed to remove example query", err);
    }
  };

  const handleUpdateTableDescription = async (tableName: string, newDescription: string) => {
    if (!isAdmin) return;
    try {
      const res = await fetch(`${API_BASE}/api/workspaces/vault/tables/${tableName}?workspace_id=${workspaceId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          table_name: tableName,
          description: newDescription,
        }),
      });

      if (res.ok) {
        // Update local state
        if (selectedTable) {
          setSelectedTable({ ...selectedTable, description: newDescription });
        }
        setTables(tables.map(t => t.table_name === tableName ? { ...t, description: newDescription } : t));
        setEditingField(null);
      }
    } catch (err) {
      console.error("Failed to update table description", err);
    }
  };

  const handleUpdateColumnDescription = async (tableName: string, columnName: string, newDescription: string) => {
    if (!isAdmin) return;
    try {
      const res = await fetch(`${API_BASE}/api/workspaces/vault/tables/${tableName}/columns/${columnName}?workspace_id=${workspaceId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          column_name: columnName,
          description: newDescription,
        }),
      });
      
      if (res.ok) {
        // Update local state
        if (selectedTable) {
          const updatedColumns = selectedTable.columns.map(col => 
            col.name === columnName ? { ...col, description: newDescription } : col
          );
          setSelectedTable({ ...selectedTable, columns: updatedColumns });
        }
        setEditingField(null);
      }
    } catch (err) {
      console.error("Failed to update column description", err);
    }
  };

  // ── LLM auto-fill (draft → review → accept) ──────────────────────────────
  const [llmDraft, setLlmDraft] = useState<LlmDraft | null>(null);
  const [llmLoading, setLlmLoading] = useState(false);

  const handleAutoFillLlm = async () => {
    if (!isAdmin || !selectedTable) return;
    try {
      setLlmLoading(true);
      setLlmDraft(null);
      const res = await fetch(`${API_BASE}/api/workspaces/vault/enrich/llm?workspace_id=${workspaceId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ tables: [selectedTable.table_name], mode: "fill_empty" }),
      });
      if (res.ok) {
        const data = await res.json();
        setLlmDraft((data.drafts && data.drafts[0]) || null);
      } else {
        alert("LLM auto-fill failed");
      }
    } catch (err) {
      console.error("LLM auto-fill failed", err);
      alert("LLM auto-fill failed");
    } finally {
      setLlmLoading(false);
    }
  };

  const acceptDraftDescription = async () => {
    if (!selectedTable || !llmDraft?.suggested_description) return;
    await handleUpdateTableDescription(selectedTable.table_name, llmDraft.suggested_description);
    setLlmDraft((d) => (d ? { ...d, suggested_description: null } : d));
  };

  const acceptDraftKeywords = async () => {
    if (!selectedTable || !llmDraft?.suggested_keywords?.length) return;
    const merged = Array.from(
      new Set([...(selectedTable.keywords || []), ...llmDraft.suggested_keywords]),
    );
    await handleUpdateKeywords(selectedTable.table_name, merged.join(", "));
    setLlmDraft((d) => (d ? { ...d, suggested_keywords: [] } : d));
  };

  const acceptDraftColumn = async (col: LlmColumnDraft) => {
    if (!selectedTable || !col.suggested_description) return;
    await handleUpdateColumnDescription(selectedTable.table_name, col.name, col.suggested_description);
    setLlmDraft((d) =>
      d ? { ...d, columns: d.columns.filter((c) => c.name !== col.name) } : d,
    );
  };

  const filteredTables = tables.filter(t =>
    t.table_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (t.description && t.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="flex h-full w-full bg-gray-50 dark:bg-gray-950">
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Table List */}
        <div className={`w-full md:w-80 border-r border-gray-200 bg-white flex flex-col h-full z-10 flex-shrink-0 shadow-sm ${selectedTable ? 'hidden md:flex' : 'flex'}`}>
          <div className="p-4 border-b border-gray-200 bg-white sticky top-0 z-20">
            <div className="flex items-center justify-between mb-4">
              <h1 className="text-xl font-semibold flex items-center gap-2 text-gray-900">
                <Database className="w-5 h-5 text-blue-600" />
                Data Dictionary
              </h1>
              <Button size="sm" variant="outline" onClick={async () => {
                if(!confirm("This will connect to the customer DB and re-synchronize the schema. Continue?")) return;
                try {
                  const res = await fetch(`${API_BASE}/api/workspaces/vault/sync?workspace_id=${workspaceId}`, {
                    method: 'POST',
                    headers: { Authorization: `Bearer ${token}` }
                  });
                  if(res.ok) {
                    const data = await res.json();
                    alert(`Sync complete! Added: ${data.stats.added}, Updated: ${data.stats.updated}, Unchanged: ${data.stats.unchanged}`);
                    fetchTables();
                  } else {
                    const err = await res.json();
                    alert(`Sync failed: ${err.detail || "Unknown error"}`);
                  }
                } catch(e) {
                  alert("Failed to reach sync API");
                }
              }} className="h-8 text-xs px-2">
                <RefreshCw className="w-3 h-3 mr-1" /> Re-Sync
              </Button>
            </div>
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <Input 
                placeholder="Search tables..." 
                className="pl-9 bg-gray-50 border-gray-200 focus:bg-white"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent">
            {loading ? (
              <div className="p-4 text-center text-sm text-gray-500">Loading tables...</div>
            ) : filteredTables.length === 0 ? (
              <div className="p-4 text-center text-sm text-gray-500">No tables found.</div>
            ) : (
              <ul className="space-y-1">
                {filteredTables.map(table => (
                  <li key={table.table_name}>
                    <button
                      onClick={() => fetchTableDetail(table.table_name)}
                      className={`w-full text-left px-3 py-2.5 rounded-md text-sm transition-all duration-200 group flex items-center justify-between ${
                        selectedTable?.table_name === table.table_name 
                          ? 'bg-blue-50 text-blue-700 font-medium' 
                          : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                      }`}
                    >
                      <div className="flex items-center gap-2 overflow-hidden flex-1">
                        <TableIcon className={`w-4 h-4 flex-shrink-0 ${selectedTable?.table_name === table.table_name ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-600'}`} />
                        <span className="truncate">{table.table_name}</span>
                      </div>
                      <ChevronRight className={`w-4 h-4 flex-shrink-0 opacity-0 transition-opacity ${selectedTable?.table_name === table.table_name ? 'opacity-100 text-blue-400' : 'group-hover:opacity-100 text-gray-300'}`} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Right Content - Table Details */}
        <div className={`flex-1 bg-gray-50 flex flex-col h-full overflow-y-auto relative p-6 md:p-8 ${!selectedTable ? 'hidden md:flex' : 'flex'}`}>
          {loadingDetail ? (
            <div className="flex h-full items-center justify-center text-gray-500">
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4" />
                <p>Loading table details...</p>
              </div>
            </div>
          ) : selectedTable ? (
            <div className="max-w-5xl mx-auto space-y-6">
              {/* Header Card */}
              <Card className="border-gray-200 shadow-sm overflow-hidden">
                <div className="h-2 bg-blue-600 w-full" />
                <CardHeader className="pb-4">
                  <div className="flex justify-between items-start gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <button className="md:hidden p-1 text-gray-500 hover:text-gray-900" onClick={() => setSelectedTable(null)}>
                          <ChevronRight className="w-5 h-5 rotate-180" />
                        </button>
                        <TableIcon className="w-6 h-6 text-blue-600" />
                        <CardTitle className="text-2xl font-bold text-gray-900">{selectedTable.table_name}</CardTitle>
                      </div>
                      {selectedTable.business_name && (
                        <p className="text-sm font-medium text-gray-500">{selectedTable.business_name}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {selectedTable.data_domain && (
                        <span className="px-2.5 py-1 text-xs font-medium bg-blue-50 text-blue-700 rounded-full border border-blue-100">
                          {selectedTable.data_domain}
                        </span>
                      )}
                      {isAdmin && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleAutoFillLlm}
                          disabled={llmLoading}
                          title="Use the LLM to draft descriptions/keywords/relationships for empty fields (review before applying)"
                        >
                          <RefreshCw className={`w-4 h-4 mr-1.5 ${llmLoading ? "animate-spin" : ""}`} />
                          {llmLoading ? "Drafting..." : "Auto-fill empty (LLM)"}
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="group relative rounded-lg border border-gray-100 bg-gray-50/50 p-4 transition-colors hover:bg-gray-50">
                    {editingField?.type === 'table' && editingField.name === selectedTable.table_name ? (
                      <div className="flex items-start gap-2">
                        <textarea
                          className="w-full text-sm border-gray-200 rounded-md focus:ring-blue-500 focus:border-blue-500 p-2 min-h-[80px]"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          autoFocus
                        />
                        <div className="flex flex-col gap-1">
                          <Button size="icon" variant="default" className="h-8 w-8 bg-blue-600 hover:bg-blue-700" onClick={() => handleUpdateTableDescription(selectedTable.table_name, editValue)}>
                            <Check className="w-4 h-4" />
                          </Button>
                          <Button size="icon" variant="outline" className="h-8 w-8" onClick={() => setEditingField(null)}>
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-start justify-between min-h-[40px]">
                        <div>
                          <div className="flex items-center gap-1.5 mb-1.5">
                            <FileText className="w-4 h-4 text-gray-400" />
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Description</span>
                          </div>
                          <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                            {selectedTable.description || <span className="text-gray-400 italic">No description provided</span>}
                          </p>
                        </div>
                        {isAdmin && (
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 text-gray-400 hover:text-blue-600 hover:bg-blue-50"
                            onClick={() => {
                              setEditingField({ type: 'table', name: selectedTable.table_name });
                              setEditValue(selectedTable.description || "");
                            }}
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Keywords Editor */}
                  {editingField?.type === 'keywords' && editingField.name === selectedTable.table_name ? (
                    <div className="mt-4 flex flex-col gap-2">
                      <Input
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        placeholder="Comma separated keywords..."
                      />
                      <div className="flex items-center gap-2">
                        <Button size="sm" onClick={() => handleUpdateKeywords(selectedTable.table_name, editValue)}>
                          <Check className="w-4 h-4 mr-1" /> Save Keywords
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setEditingField(null)}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-4 flex items-center justify-between group/kw">
                      <div className="flex flex-wrap gap-1.5">
                        {selectedTable.keywords && selectedTable.keywords.length > 0 ? (
                          selectedTable.keywords.map((kw, i) => (
                            <span key={i} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded-md border border-gray-200">
                              #{kw}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-gray-400 italic">No keywords</span>
                        )}
                      </div>
                      {isAdmin && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 opacity-0 group-hover/kw:opacity-100 transition-opacity flex-shrink-0 text-gray-400 hover:text-blue-600 hover:bg-blue-50"
                          onClick={() => {
                            setEditingField({ type: 'keywords', name: selectedTable.table_name });
                            setEditValue(selectedTable.keywords?.join(", ") || "");
                          }}
                        >
                          <Edit2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* LLM draft review card */}
              {llmDraft && llmDraft.table_name === selectedTable.table_name && (
                <Card className="border-amber-200 shadow-sm bg-amber-50/40">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base font-semibold text-amber-900 flex items-center gap-2">
                        <FileText className="w-4 h-4" />
                        LLM Draft — review before applying ({llmDraft.language.toUpperCase()})
                      </CardTitle>
                      <Button variant="ghost" size="sm" onClick={() => setLlmDraft(null)}>
                        <X className="w-4 h-4 mr-1" /> Dismiss
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {llmDraft.status === "error" && (
                      <p className="text-sm text-red-600">Error: {llmDraft.error}</p>
                    )}
                    {llmDraft.status === "skipped" && (
                      <p className="text-sm text-gray-600">Nothing empty to fill for this table.</p>
                    )}

                    {llmDraft.suggested_description && (
                      <div className="rounded-lg border border-amber-200 bg-white p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-xs font-semibold uppercase text-gray-500 mb-1">Description</p>
                            <p className="text-sm text-gray-700">{llmDraft.suggested_description}</p>
                          </div>
                          <Button size="sm" className="bg-green-600 hover:bg-green-700 flex-shrink-0" onClick={acceptDraftDescription}>
                            <Check className="w-4 h-4 mr-1" /> Accept
                          </Button>
                        </div>
                      </div>
                    )}

                    {llmDraft.suggested_keywords?.length > 0 && (
                      <div className="rounded-lg border border-amber-200 bg-white p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-xs font-semibold uppercase text-gray-500 mb-1">Keywords</p>
                            <div className="flex flex-wrap gap-1.5">
                              {llmDraft.suggested_keywords.map((kw, i) => (
                                <span key={i} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded-md border border-gray-200">#{kw}</span>
                              ))}
                            </div>
                          </div>
                          <Button size="sm" className="bg-green-600 hover:bg-green-700 flex-shrink-0" onClick={acceptDraftKeywords}>
                            <Check className="w-4 h-4 mr-1" /> Accept
                          </Button>
                        </div>
                      </div>
                    )}

                    {llmDraft.columns?.length > 0 && (
                      <div className="rounded-lg border border-amber-200 bg-white p-3">
                        <p className="text-xs font-semibold uppercase text-gray-500 mb-2">Column descriptions ({llmDraft.columns.length})</p>
                        <div className="space-y-2">
                          {llmDraft.columns.map((col) => (
                            <div key={col.name} className="flex items-start justify-between gap-3 border-b border-gray-100 pb-2 last:border-0">
                              <div>
                                <span className="text-sm font-mono text-gray-900">{col.name}</span>
                                <p className="text-sm text-gray-600">{col.suggested_description}</p>
                              </div>
                              <Button size="sm" variant="outline" className="flex-shrink-0" onClick={() => acceptDraftColumn(col)}>
                                <Check className="w-4 h-4 mr-1" /> Accept
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {llmDraft.relationships?.length > 0 && (
                      <div className="rounded-lg border border-amber-200 bg-white p-3">
                        <p className="text-xs font-semibold uppercase text-gray-500 mb-2">Suggested relationships</p>
                        <div className="space-y-1">
                          {llmDraft.relationships.map((r, i) => (
                            <div key={i} className="flex items-center justify-between gap-3 text-sm">
                              <span className="font-mono text-gray-700">
                                {r.source_column} → {r.target_table}.{r.target_column}
                                <span className="ml-2 text-xs text-gray-400">({Math.round(r.confidence * 100)}%)</span>
                              </span>
                              <Button
                                size="sm"
                                variant="outline"
                                className="flex-shrink-0"
                                onClick={() =>
                                  handleAddRelationship(
                                    selectedTable.table_name,
                                    r.source_column,
                                    r.target_table,
                                    r.target_column,
                                  )
                                }
                              >
                                <Check className="w-4 h-4 mr-1" /> Accept
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Columns Section */}
              <Card className="border-gray-200 shadow-sm">
                <CardHeader className="border-b border-gray-100 bg-gray-50/50 pb-4">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                      <TableIcon className="w-5 h-5 text-gray-500" />
                      Columns
                    </CardTitle>
                    <span className="text-xs font-medium text-gray-500 bg-gray-200 px-2 py-1 rounded-full">
                      {selectedTable.column_count}
                    </span>
                  </div>
                </CardHeader>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs text-gray-500 uppercase bg-gray-50/80 border-b border-gray-200">
                      <tr>
                        <th className="px-6 py-3 font-semibold">Column Name</th>
                        <th className="px-6 py-3 font-semibold w-32">Type</th>
                        <th className="px-6 py-3 font-semibold w-24">Nullable</th>
                        <th className="px-6 py-3 font-semibold">Description</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 bg-white">
                      {selectedTable.columns.map((col) => (
                        <tr key={col.name} className="hover:bg-gray-50 transition-colors group">
                          <td className="px-6 py-4 font-medium text-gray-900 flex items-center gap-2">
                            {col.name}
                            {col.is_pk && <span title="Primary Key"><Key className="w-3.5 h-3.5 text-amber-500" /></span>}
                          </td>
                          <td className="px-6 py-4">
                            <span className="font-mono text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-100">
                              {col.type}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-gray-500">
                            {col.nullable ? "Yes" : "No"}
                          </td>
                          <td className="px-6 py-4">
                            {editingField?.type === 'column' && editingField.name === col.name ? (
                              <div className="flex items-start gap-2">
                                <textarea
                                  className="flex-1 text-sm border-gray-200 rounded-md focus:ring-blue-500 focus:border-blue-500 p-2 min-h-[60px]"
                                  value={editValue}
                                  onChange={(e) => setEditValue(e.target.value)}
                                  autoFocus
                                />
                                <div className="flex flex-col gap-1">
                                  <Button size="icon" variant="default" className="h-7 w-7 bg-blue-600 hover:bg-blue-700" onClick={() => handleUpdateColumnDescription(selectedTable.table_name, col.name, editValue)}>
                                    <Check className="w-3.5 h-3.5" />
                                  </Button>
                                  <Button size="icon" variant="outline" className="h-7 w-7" onClick={() => setEditingField(null)}>
                                    <X className="w-3.5 h-3.5" />
                                  </Button>
                                </div>
                              </div>
                            ) : (
                              <>
                              <div className="flex items-start justify-between min-h-[28px]">
                                <span className={col.description ? "text-gray-700 leading-relaxed" : "text-gray-400 italic"}>
                                  {col.description || "No description"}
                                </span>
                                {isAdmin && (
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 text-gray-400 hover:text-blue-600 hover:bg-blue-50 -mt-1 -mr-2"
                                    onClick={() => {
                                      setEditingField({ type: 'column', name: col.name });
                                      setEditValue(col.description || "");
                                    }}
                                  >
                                    <Edit2 className="w-3.5 h-3.5" />
                                  </Button>
                                )}
                              </div>
                              {(selectedTable.sampled_values?.[col.name]?.length ?? 0) > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1.5" title="Sampled distinct values">
                                  {selectedTable.sampled_values[col.name].slice(0, 12).map((v) => (
                                    <span key={v} className="font-mono text-[11px] bg-purple-50 text-purple-700 border border-purple-100 rounded px-1.5 py-0.5">
                                      {v}
                                    </span>
                                  ))}
                                  {selectedTable.sampled_values[col.name].length > 12 && (
                                    <span className="text-[11px] text-gray-400 self-center">
                                      +{selectedTable.sampled_values[col.name].length - 12}
                                    </span>
                                  )}
                                </div>
                              )}
                              </>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Sampled Values Section */}
              {selectedTable.sampled_values && Object.keys(selectedTable.sampled_values).length > 0 && (
                <Card className="border-gray-200 shadow-sm">
                  <CardHeader className="border-b border-gray-100 bg-gray-50/50 pb-4">
                    <CardTitle className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                      <Database className="w-5 h-5 text-gray-500" />
                      Sampled Values
                      <span className="text-xs font-normal text-gray-400">
                        ({Object.keys(selectedTable.sampled_values).length} columns)
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-3">
                    {Object.entries(selectedTable.sampled_values).map(([colName, vals]) => (
                      <div key={colName} className="flex flex-col sm:flex-row sm:items-start gap-2">
                        <span className="font-mono text-xs font-semibold text-gray-700 sm:w-48 shrink-0 pt-1">
                          {colName}
                        </span>
                        <div className="flex flex-wrap gap-1">
                          {vals.map((v) => (
                            <span key={v} className="font-mono text-[11px] bg-purple-50 text-purple-700 border border-purple-100 rounded px-1.5 py-0.5">
                              {v}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {/* Relationships Section */}
              <Card className="border-gray-200 shadow-sm">
                <CardHeader className="border-b border-gray-100 bg-gray-50/50 pb-4">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                      <LinkIcon className="w-5 h-5 text-gray-500" />
                      Relationships
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="pt-4">
                  {selectedTable.relationships && selectedTable.relationships.length > 0 ? (
                    <ul className="space-y-3 mb-4">
                      {selectedTable.relationships.map((rel, idx) => (
                        <li key={idx} className="group flex items-start gap-3 p-3 rounded-lg bg-gray-50 border border-gray-100">
                          <div className="mt-0.5 w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center flex-shrink-0">
                            <LinkIcon className="w-3 h-3" />
                          </div>
                          <span className="flex-1 text-sm text-gray-700 font-medium break-words">
                            {rel.raw}
                          </span>
                          {isAdmin && (
                            <button
                              onClick={() => handleDeleteRelationship(selectedTable.table_name, rel.raw)}
                              title="Remove relationship"
                              className="opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 text-gray-400 hover:text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500 italic mb-4">No manual relationships defined.</p>
                  )}

                  {isAdmin && (
                    <div className="mt-4 p-4 border border-dashed border-gray-300 rounded-lg">
                      {addingRel ? (
                        <div className="flex flex-col gap-3">
                          <h4 className="text-sm font-semibold">Add Manual Relationship</h4>
                          <div className="grid grid-cols-2 gap-3 text-sm">
                            <div>
                              <label className="block text-xs text-gray-500 mb-1">Source Column</label>
                              <Input value={relSourceCol} onChange={e => setRelSourceCol(e.target.value)} placeholder="e.g. USER_ID" />
                            </div>
                            <div>
                              <label className="block text-xs text-gray-500 mb-1">Target Table</label>
                              <Input value={relTargetTable} onChange={e => setRelTargetTable(e.target.value)} placeholder="e.g. DIM_USERS" />
                            </div>
                            <div className="col-span-2">
                              <label className="block text-xs text-gray-500 mb-1">Target Column</label>
                              <Input value={relTargetCol} onChange={e => setRelTargetCol(e.target.value)} placeholder="e.g. ID" />
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <Button size="sm" onClick={() => handleAddRelationship(selectedTable.table_name)} disabled={!relSourceCol || !relTargetTable || !relTargetCol}>
                              Save Relationship
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => setAddingRel(false)}>
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <Button variant="outline" size="sm" onClick={() => setAddingRel(true)}>
                          + Add Relationship
                        </Button>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Example Queries Section */}
              <Card className="border-gray-200 shadow-sm">
                <CardHeader className="border-b border-gray-100 bg-gray-50/50 pb-4">
                  <CardTitle className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    <FileText className="w-5 h-5 text-gray-500" />
                    Example Queries
                    <span className="text-xs font-medium text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
                      {selectedTable.example_queries?.length ?? 0}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-4">
                  {selectedTable.example_queries && selectedTable.example_queries.length > 0 ? (
                    <ul className="space-y-4 mb-4">
                      {selectedTable.example_queries.map((eq, idx) => (
                        <li key={idx} className="group rounded-lg border border-gray-100 bg-gray-50/60 overflow-hidden">
                          <div className="flex items-start justify-between gap-3 px-3 py-2 border-b border-gray-100">
                            <span className="text-sm font-medium text-gray-800">{eq.question}</span>
                            {isAdmin && (
                              <button
                                onClick={() => handleDeleteExampleQuery(eq.question)}
                                title="Remove example query"
                                className="opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 text-gray-400 hover:text-red-600"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                          {eq.answer && (
                            <p className="text-sm text-gray-600 whitespace-pre-wrap px-3 pt-2">{eq.answer}</p>
                          )}
                          <pre className="text-xs font-mono text-gray-700 p-3 overflow-x-auto whitespace-pre">{eq.sql}</pre>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500 italic mb-4">No example queries yet.</p>
                  )}

                  {isAdmin && (
                    <div className="mt-2 p-4 border border-dashed border-gray-300 rounded-lg">
                      {addingEq ? (
                        <div className="flex flex-col gap-3">
                          <h4 className="text-sm font-semibold">Add Example Query</h4>
                          <Input
                            value={eqQuestion}
                            onChange={(e) => setEqQuestion(e.target.value)}
                            placeholder="Natural-language question (e.g. Top 10 customers by recharge)"
                          />
                          <textarea
                            value={eqAnswer}
                            onChange={(e) => setEqAnswer(e.target.value)}
                            placeholder="Explanation / answer text shown with the result (optional) — rules, caveats, which columns to use…"
                            className="w-full min-h-[80px] rounded-md border border-gray-200 bg-white p-3 text-sm text-gray-800 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                          <textarea
                            value={eqSql}
                            onChange={(e) => setEqSql(e.target.value)}
                            placeholder="SELECT ..."
                            spellCheck={false}
                            className="w-full min-h-[140px] rounded-md border border-gray-200 bg-white p-3 text-xs font-mono text-gray-800 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                          <div className="flex gap-2">
                            <Button size="sm" onClick={handleAddExampleQuery} disabled={!eqQuestion.trim() || !eqSql.trim()}>
                              <Check className="w-4 h-4 mr-1" /> Save Query
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => setAddingEq(false)}>
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <Button variant="outline" size="sm" onClick={() => setAddingEq(true)}>
                          + Add Example Query
                        </Button>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="flex flex-col h-full items-center justify-center text-gray-500 space-y-4">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-2">
                <Database className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-lg font-medium text-gray-900">No Table Selected</p>
              <p className="text-sm">Select a table from the sidebar to view its metadata and schema.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
