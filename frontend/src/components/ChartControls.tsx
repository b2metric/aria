"use client";

import type { ChartConfig, FilterState } from "@/lib/types";

interface ChartControlsProps {
  config: ChartConfig;
  onConfigChange: (config: ChartConfig) => void;
  filters: FilterState;
  onFilterChange: (filters: FilterState) => void;
  onExportPNG: () => void;
  onExportCSV: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
}

const DATE_RANGES: { value: FilterState["dateRange"]; label: string }[] = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "1y", label: "1 year" },
  { value: "all", label: "All time" },
];

const CHART_TYPES: { value: ChartConfig["type"]; label: string }[] = [
  { value: "bar", label: "Bar" },
  { value: "line", label: "Line" },
  { value: "area", label: "Area" },
  { value: "pie", label: "Pie" },
];

export default function ChartControls({
  config,
  onConfigChange,
  filters,
  onFilterChange,
  onExportPNG,
  onExportCSV,
  onZoomIn,
  onZoomOut,
  onResetZoom,
}: ChartControlsProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl">
      {/* Chart type switcher */}
      <div className="flex items-center gap-1 bg-white rounded-lg border border-gray-200 p-0.5">
        {CHART_TYPES.map((ct) => (
          <button
            key={ct.value}
            onClick={() => onConfigChange({ ...config, type: ct.value })}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              config.type === ct.value
                ? "bg-blue-600 text-white shadow-sm"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {ct.label}
          </button>
        ))}
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-gray-200" />

      {/* Date range filter */}
      <div className="flex items-center gap-1 bg-white rounded-lg border border-gray-200 p-0.5">
        {DATE_RANGES.map((dr) => (
          <button
            key={dr.value}
            onClick={() => onFilterChange({ ...filters, dateRange: dr.value })}
            className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors ${
              filters.dateRange === dr.value
                ? "bg-blue-600 text-white shadow-sm"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {dr.label}
          </button>
        ))}
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-gray-200" />

      {/* Zoom controls */}
      <div className="flex items-center gap-1 bg-white rounded-lg border border-gray-200 p-0.5">
        <button
          onClick={onZoomIn}
          className="px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
          title="Zoom in"
        >
          🔍+
        </button>
        <button
          onClick={onZoomOut}
          className="px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
          title="Zoom out"
        >
          🔍−
        </button>
        <button
          onClick={onResetZoom}
          className="px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
          title="Reset zoom"
        >
          ↺
        </button>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Export controls */}
      <div className="flex items-center gap-1">
        <button
          onClick={onExportPNG}
          className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-1.5"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
          PNG
        </button>
        <button
          onClick={onExportCSV}
          className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-1.5"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="7" y1="13" x2="17" y2="13"/><line x1="7" y1="17" x2="14" y2="17"/></svg>
          CSV
        </button>
      </div>
    </div>
  );
}
