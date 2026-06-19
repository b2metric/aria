"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Search, Database, Table as TableIcon, Edit2, Check, X, FileText, Link as LinkIcon, Key, ChevronRight, RefreshCw } from "lucide-react";
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
  enriched_at: string;
  generated_at: string;
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

  const handleAddRelationship = async (sourceTable: string) => {
    if (!isAdmin) return;
    try {
      const res = await fetch(`${API_BASE}/api/workspaces/vault/enrich/relationship?source_table=${sourceTable}&source_column=${relSourceCol}&target_table=${relTargetTable}&target_column=${relTargetCol}&workspace_id=${workspaceId}`, {
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
                    {selectedTable.data_domain && (
                      <span className="px-2.5 py-1 text-xs font-medium bg-blue-50 text-blue-700 rounded-full border border-blue-100">
                        {selectedTable.data_domain}
                      </span>
                    )}
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
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

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
                        <li key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 border border-gray-100">
                          <div className="mt-0.5 w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center flex-shrink-0">
                            <LinkIcon className="w-3 h-3" />
                          </div>
                          <span className="text-sm text-gray-700 font-medium">
                            {rel.raw}
                          </span>
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
