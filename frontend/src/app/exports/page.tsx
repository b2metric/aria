"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Download, RefreshCw, FileDown, Clock, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { listExports, downloadExport, type ExportListItem } from "@/lib/api";

function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString();
}

function StatusBadge({ status }: { status: ExportListItem["status"] }) {
  switch (status) {
    case "success":
      return (
        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
          Success
        </Badge>
      );
    case "error":
      return (
        <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
          Error
        </Badge>
      );
    case "running":
      return (
        <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
          Running
        </Badge>
      );
    case "queued":
    default:
      return (
        <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
          Queued
        </Badge>
      );
  }
}

function ExportAction({ job, token }: { job: ExportListItem; token: string | undefined }) {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError(null);
    try {
      await downloadExport(job.id, `export_${job.id}.csv`, token);
    } catch (err) {
      console.error("Failed to download export", err);
      setDownloadError("Download failed");
    } finally {
      setDownloading(false);
    }
  };

  if (job.status === "queued" || job.status === "running") {
    return <span className="text-xs text-gray-400 italic">Preparing…</span>;
  }

  if (job.status === "error") {
    return (
      <span className="text-xs text-red-500 line-clamp-1" title={job.error ?? undefined}>
        {job.error || "Export failed"}
      </span>
    );
  }

  if (job.download_ready) {
    return (
      <div className="flex flex-col items-end gap-1">
        <Button variant="outline" size="sm" onClick={() => void handleDownload()} disabled={downloading}>
          <Download className="w-3.5 h-3.5 mr-1.5" />
          {downloading ? "Downloading…" : "Download CSV"}
        </Button>
        {downloadError && <span className="text-xs text-red-500">{downloadError}</span>}
      </div>
    );
  }

  return <span className="text-xs text-gray-400 italic">Link expired</span>;
}

export default function ExportsPage() {
  const { data: session } = useSession();
  const token = (session as any)?.accessToken;

  const [exports, setExports] = useState<ExportListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchExports = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await listExports(token);
      setExports(data);
    } catch (err) {
      console.error("Failed to fetch exports", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      void (async () => {
        await fetchExports();
      })();
    }
  }, [token]);

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <FileDown className="w-6 h-6 text-blue-600" />
            Exports
          </h1>
          <p className="text-gray-500 mt-1">Your recent CSV exports.</p>
        </div>
        <Button variant="outline" onClick={() => void fetchExports()} disabled={loading} className="w-full sm:w-auto">
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 font-semibold">Question</th>
                <th className="px-6 py-3 font-semibold">Status</th>
                <th className="px-6 py-3 font-semibold">Rows</th>
                <th className="px-6 py-3 font-semibold">Created</th>
                <th className="px-6 py-3 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading && exports.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                    Loading exports...
                  </td>
                </tr>
              ) : exports.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-gray-500">
                    <div className="flex flex-col items-center gap-2">
                      <Clock className="w-6 h-6 text-gray-300" />
                      No exports yet. Large query results will appear here.
                    </div>
                  </td>
                </tr>
              ) : (
                exports.map((job) => (
                  <tr key={job.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 max-w-md">
                      <span className="font-medium text-gray-900 line-clamp-2" title={job.question ?? undefined}>
                        {job.question || <span className="text-gray-400 italic">No question recorded</span>}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                      {job.row_count !== null ? (
                        <span>
                          {job.row_count.toLocaleString()}
                          {job.truncated && (
                            <span className="ml-1 inline-flex items-center gap-1 text-xs text-amber-600">
                              <AlertCircle className="w-3 h-3" /> truncated
                            </span>
                          )}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">{formatDate(job.created_at)}</td>
                    <td className="px-6 py-4 text-right">
                      <ExportAction job={job} token={token} />
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
