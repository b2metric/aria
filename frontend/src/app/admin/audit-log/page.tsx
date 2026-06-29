"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { ShieldAlert, Search, RefreshCw, AlertCircle, CheckCircle2, XCircle, Eye } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type AuditLog = {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: any;
  user_id: string | null;
  ip_address: string | null;
  created_at: string;
};

export default function AuditLogPage() {
  const { data: session, status } = useSession();
  const token = (session as any)?.accessToken;
  const router = useRouter();

  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [actionFilter, setActionFilter] = useState<string>("all");

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/api/auth/signin');
  }, [status, router]);

  const fetchLogs = async () => {
    if (!token) return;
    try {
      setLoading(true);
      let url = `${API_BASE}/api/admin/audit-logs?limit=100`;
      if (actionFilter !== "all") url += `&action=${actionFilter}`;
      // Status filter is now applied server-side via the `success` query param
      // (backend matches details->>'success'), instead of slicing client-side.
      if (statusFilter === "success") url += `&success=true`;
      else if (statusFilter === "failed") url += `&success=false`;

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setLogs(data.data || []);
      }
    } catch (err) {
      console.error("Failed to fetch audit logs", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void (async () => {
      await fetchLogs();
    })();
  }, [token, statusFilter, actionFilter]);

  const getStatusBadge = (logStatus: string) => {
    switch (logStatus) {
      case 'success': return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200"><CheckCircle2 className="w-3 h-3 mr-1"/> Success</Badge>;
      case 'failed': return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200"><XCircle className="w-3 h-3 mr-1"/> Failed</Badge>;
      case 'denied': return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200"><AlertCircle className="w-3 h-3 mr-1"/> Denied</Badge>;
      default: return <Badge variant="outline">{logStatus}</Badge>;
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-blue-600" />
            Audit Logs
          </h1>
          <p className="text-gray-500 mt-1">Monitor data access, queries, and system events.</p>
        </div>
        <Button variant="outline" onClick={fetchLogs} disabled={loading} className="w-full sm:w-auto">
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="flex flex-wrap gap-4 bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
        <div className="w-full sm:w-48">
          <label className="text-xs font-medium text-gray-500 mb-1.5 block">Status</label>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger><SelectValue placeholder="All Statuses" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="success">Success</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="denied">Denied</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="w-full sm:w-48">
          <label className="text-xs font-medium text-gray-500 mb-1.5 block">Action</label>
          <Select value={actionFilter} onValueChange={setActionFilter}>
            <SelectTrigger><SelectValue placeholder="All Actions" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Actions</SelectItem>
              <SelectItem value="query">Query Executed</SelectItem>
              <SelectItem value="export">Data Exported</SelectItem>
              <SelectItem value="policy_evaluation">Policy Evaluation</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 font-semibold">Timestamp</th>
                <th className="px-6 py-3 font-semibold">User ID</th>
                <th className="px-6 py-3 font-semibold">Action & Status</th>
                <th className="px-6 py-3 font-semibold">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading && logs.length === 0 ? (
                <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500">Loading audit logs...</td></tr>
              ) : logs.length === 0 ? (
                <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-500">No audit logs found matching criteria.</td></tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-gray-600">
                      {log.user_id || 'System'}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1.5 items-start">
                        <span className="font-medium text-gray-900">{log.action}</span>
                        {log.details && log.details.success !== undefined && getStatusBadge(log.details.success ? "success" : "failed")}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="max-w-md">
                        {log.action === 'query' && log.details?.sql ? (
                          <div className="bg-gray-50 p-2 rounded border border-gray-200 font-mono text-xs text-gray-800 line-clamp-2" title={log.details.sql}>
                            {log.details.sql}
                          </div>
                        ) : log.resource_id ? (
                          <span className="font-medium">{log.resource_type}: {log.resource_id}</span>
                        ) : (
                          <span className="text-gray-400 italic">No details</span>
                        )}
                        {log.details?.row_count !== undefined && (
                          <div className="mt-1 text-xs text-blue-600 font-medium">
                            Returned {log.details.row_count} rows
                          </div>
                        )}
                        {log.details && log.details.success === false && log.details.error && (
                          <div className="mt-1 text-xs text-red-600 line-clamp-1" title={log.details.error}>
                            Error: {log.details.error}
                          </div>
                        )}

                        <div className="mt-2">
                          <Dialog>
                            <DialogTrigger asChild>
                              <Button variant="ghost" size="sm" className="h-6 px-2 text-xs">
                                <Eye className="w-3 h-3 mr-1" /> View Full Details
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                              <DialogHeader>
                                <DialogTitle>Audit Log Details</DialogTitle>
                              </DialogHeader>
                              <div className="mt-4 space-y-4">
                                <div>
                                  <h4 className="text-sm font-semibold mb-1 text-gray-700">Metadata</h4>
                                  <div className="bg-gray-50 p-3 rounded text-sm text-gray-600 grid grid-cols-2 gap-2">
                                    <div><span className="font-medium text-gray-500">ID:</span> {log.id}</div>
                                    <div><span className="font-medium text-gray-500">Action:</span> {log.action}</div>
                                    <div><span className="font-medium text-gray-500">Resource Type:</span> {log.resource_type}</div>
                                    <div><span className="font-medium text-gray-500">Status:</span> {log.details?.success !== undefined ? (log.details.success ? "success" : "failed") : "N/A"}</div>
                                  </div>
                                </div>
                                {log.details && (
                                  <div>
                                    <h4 className="text-sm font-semibold mb-1 text-gray-700">Payload</h4>
                                    <pre className="bg-[#0d0d14] text-gray-100 p-4 rounded-lg text-xs overflow-x-auto whitespace-pre-wrap break-all">
                                      {JSON.stringify(log.details, null, 2)}
                                    </pre>
                                  </div>
                                )}
                              </div>
                            </DialogContent>
                          </Dialog>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
