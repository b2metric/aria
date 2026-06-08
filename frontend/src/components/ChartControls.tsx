"use client";

import type { ChartConfig } from "@/lib/types";
import type { DateOption } from "./ChartArea";

interface ChartControlsProps {
  config: ChartConfig;
  onConfigChange: (config: ChartConfig) => void;
  /** Date-range buttons adapted to the data span; empty -> control hidden. */
  dateOptions: DateOption[];
  rangeDays: number | null;
  onRangeChange: (days: number | null) => void;
  onCyclePalette: () => void;
  onExportPNG: () => void;
  onExportCSV: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
}

const CHART_TYPES: { value: ChartConfig["type"]; label: string }[] = [
  { value: "bar", label: "Bar" },
  { value: "line", label: "Line" },
  { value: "area", label: "Area" },
  { value: "pie", label: "Pie" },
];

export default function ChartControls({
  config,
  onConfigChange,
  dateOptions,
  rangeDays,
  onRangeChange,
  onCyclePalette,
  onExportPNG,
  onExportCSV,
  onZoomIn,
  onZoomOut,
  onResetZoom,
}: ChartControlsProps) {
  // Multi-series verilerde Pie chart desteklenmez.
  const hasMultipleSeries = config.yKeys && config.yKeys.length > 1;
  
  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl">
      {/* Chart type switcher */}
      <div className="flex items-center gap-1 bg-white rounded-lg border border-gray-200 p-0.5">
        {CHART_TYPES.map((ct) => {
          // Eğer veride birden fazla yKey varsa, Pie butonunu hiç gösterme.
          if (ct.value === "pie" && hasMultipleSeries) return null;
          
          return (
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
          );
        })}
      </div>

      {/* Date range filter — only shown when the x-axis is a usable date axis */}
      {dateOptions.length > 0 && (
        <>
          <div className="w-px h-6 bg-gray-200" />
          <div className="flex items-center gap-1 bg-white rounded-lg border border-gray-200 p-0.5">
            {dateOptions.map((dr) => (
              <button
                key={dr.label}
                onClick={() => onRangeChange(dr.days)}
                className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  rangeDays === dr.days
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {dr.label}
              </button>
            ))}
          </div>
        </>
      )}

      {/* Divider */}
      <div className="w-px h-6 bg-gray-200" />

      {/* Zoom + palette controls */}
      <div className="flex items-center gap-1 bg-white rounded-lg border border-gray-200 p-0.5">
        <button onClick={onZoomIn} className="px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-md transition-colors" title="Zoom in">🔍+</button>
        <button onClick={onZoomOut} className="px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-md transition-colors" title="Zoom out">🔍−</button>
        <button onClick={onResetZoom} className="px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-md transition-colors" title="Reset zoom">↺</button>
        <button onClick={onCyclePalette} className="px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-md transition-colors" title="Change color palette">🎨</button>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Export controls */}
      <div className="flex items-center gap-1">
        <button onClick={onExportPNG} className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-1.5">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
          PNG
        </button>
        <button onClick={onExportCSV} className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-1.5">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="7" y1="13" x2="17" y2="13"/><line x1="7" y1="17" x2="14" y2="17"/></svg>
          CSV
        </button>
      </div>
    </div>
  );
}
