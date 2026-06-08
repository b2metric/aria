"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  type TooltipProps,
} from "recharts";
import type { ChartConfig, ChartDataPoint, ZoomState } from "@/lib/types";
import ChartControls from "./ChartControls";
import type { FilterState } from "@/lib/types";

// Recharts tooltip types
type PayloadEntry = {
  color: string;
  name: string;
  value: number;
  dataKey: string;
};

interface ChartAreaProps {
  data: ChartDataPoint[];
  config: ChartConfig;
  filters: FilterState;
  onFilterChange: (filters: FilterState) => void;
}

const COLORS = [
  "#4a9eed",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
];

// Recharts payload value type
type PayloadValue = number | string;

function CustomTooltip(props: any) {
  const { active, payload, label } = props;
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-white border p-2 text-sm shadow rounded">
      <p className="font-semibold mb-1">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-gray-600">{entry.name}:</span>
          <span className="font-medium text-gray-900">
            {typeof entry.value === "number"
              ? entry.value.toLocaleString()
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export type DateOption = { days: number | null; label: string };

const DAY = 86_400_000;

/** Parse each row's x value to a timestamp (or null if not a date). */
function parseTimestamps(rows: ChartDataPoint[], xKey?: string): (number | null)[] {
  if (!xKey) return rows.map(() => null);
  return rows.map((r) => {
    const v = r[xKey];
    const t = typeof v === "number" ? v : Date.parse(String(v));
    return Number.isNaN(t) ? null : t;
  });
}

/** Build date-range buttons that MATCH the data's actual span/granularity.
 *  Monthly-over-a-year data gets 3M/6M/1Y; daily data gets 7d/30d/90d.
 *  Returns [] when the x-axis isn't dates — caller then hides the control. */
function computeDateOptions(ts: (number | null)[]): DateOption[] {
  const valid = ts.filter((t): t is number => t !== null);
  if (valid.length < ts.length * 0.5 || valid.length < 2) return [];
  const spanDays = (Math.max(...valid) - Math.min(...valid)) / DAY;
  let opts: DateOption[];
  if (spanDays <= 100) {
    opts = [{ days: 7, label: "7d" }, { days: 30, label: "30d" }, { days: 90, label: "90d" }];
  } else if (spanDays <= 900) {
    opts = [{ days: 90, label: "3M" }, { days: 180, label: "6M" }, { days: 365, label: "1Y" }];
  } else {
    opts = [{ days: 365, label: "1Y" }, { days: 1095, label: "3Y" }];
  }
  // keep only windows that actually exclude data, then always offer "All".
  opts = opts.filter((o) => o.days! < spanDays * 0.9);
  return [...opts, { days: null, label: "All" }];
}

function filterByDays(
  rows: ChartDataPoint[],
  ts: (number | null)[],
  days: number | null,
): ChartDataPoint[] {
  if (days === null) return rows;
  const valid = ts.filter((t): t is number => t !== null);
  if (!valid.length) return rows;
  const cutoff = Math.max(...valid) - days * DAY;
  return rows.filter((_, i) => ts[i] !== null && (ts[i] as number) >= cutoff);
}

/** Selectable color palettes (first = backend/default). */
export const PALETTES: string[][] = [
  ["#4a9eed", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4"],
  ["#6366f1", "#14b8a6", "#f43f5e", "#eab308", "#a855f7", "#0ea5e9", "#84cc16"],
  ["#0f172a", "#334155", "#64748b", "#94a3b8", "#cbd5e1", "#475569", "#1e293b"],
  ["#e11d48", "#fb923c", "#facc15", "#4ade80", "#2dd4bf", "#60a5fa", "#c084fc"],
];

export default function ChartArea({
  data: rawData,
  config: initialConfig,
}: ChartAreaProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [config, setConfig] = useState<ChartConfig>(initialConfig);
  const [rangeDays, setRangeDays] = useState<number | null>(null);
  const [paletteIdx, setPaletteIdx] = useState(0);

  const ts = useMemo(() => parseTimestamps(rawData, config.xKey), [rawData, config.xKey]);
  // Date-range buttons adapted to the data span (empty -> not a date axis -> hidden).
  const dateOptions = useMemo(() => computeDateOptions(ts), [ts]);

  // All downstream logic uses `data` (date-filtered view of rawData).
  const data = useMemo(() => filterByDays(rawData, ts, rangeDays), [rawData, ts, rangeDays]);

  const [zoom, setZoom] = useState<ZoomState>({ startIndex: 0, endIndex: data.length });
  useEffect(() => {
    setZoom({ startIndex: 0, endIndex: data.length });
  }, [data.length]);

  const zoomedData = data.slice(zoom.startIndex, zoom.endIndex);
  const colors =
    paletteIdx === 0
      ? config.colors && config.colors.length
        ? config.colors
        : COLORS
      : PALETTES[paletteIdx % PALETTES.length];

  const handleExportPNG = useCallback(async () => {
    if (!chartRef.current) return;
    try {
      const { toBlob } = await import("html-to-image");
      const blob = await toBlob(chartRef.current, {
        backgroundColor: '#ffffff',
        pixelRatio: 2,
        // Ignore hidden elements to prevent issues with SVGs
        filter: (node) => {
          if (node.tagName === 'link' || node.tagName === 'style') return true;
          return true;
        }
      });
      
      if (blob) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `chart-${Date.now()}.png`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error("PNG export failed:", err);
    }
  }, []);

  const handleExportCSV = useCallback(() => {
    try {
      const Papa = require("papaparse");
      const csv = Papa.unparse(zoomedData);
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `chart-data-${Date.now()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("CSV export failed:", err);
    }
  }, [zoomedData]);

  const handleZoomIn = useCallback(() => {
    const len = zoomedData.length;
    if (len <= 2) return;
    const step = Math.max(1, Math.floor(len * 0.2));
    setZoom((z) => ({
      startIndex: Math.min(z.startIndex + step, data.length - 2),
      endIndex: Math.max(z.endIndex - step, z.startIndex + 2),
    }));
  }, [zoomedData.length, data.length]);

  const handleZoomOut = useCallback(() => {
    const step = Math.max(1, Math.floor(data.length * 0.2));
    setZoom((z) => ({
      startIndex: Math.max(z.startIndex - step, 0),
      endIndex: Math.min(z.endIndex + step, data.length),
    }));
  }, [data.length]);

  const handleResetZoom = useCallback(() => {
    setZoom({ startIndex: 0, endIndex: data.length });
  }, [data.length]);

  // Auto-reset zoom when config.type changes to pie
  const handleConfigChange = useCallback(
    (newConfig: ChartConfig) => {
      setConfig(newConfig);
      if (newConfig.type === "pie") {
        handleResetZoom();
      }
    },
    [handleResetZoom],
  );

  const renderChart = () => {
    switch (config.type) {
      case "bar":
        return (
          <BarChart data={zoomedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey={config.xKey} tick={{ fontSize: 11 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: "12px" }}
            />
            {config.yKeys.map((key, i) => (
              <Bar
                key={key}
                dataKey={key}
                fill={colors[i % colors.length]}
                radius={[4, 4, 0, 0]}
                maxBarSize={40}
              />
            ))}
          </BarChart>
        );

      case "line":
        return (
          <LineChart data={zoomedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey={config.xKey} tick={{ fontSize: 11 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "12px" }} />
            {config.yKeys.map((key, i) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[i % colors.length]}
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
              />
            ))}
          </LineChart>
        );

      case "area":
        return (
          <AreaChart data={zoomedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey={config.xKey} tick={{ fontSize: 11 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "12px" }} />
            {config.yKeys.map((key, i) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[i % colors.length]}
                fill={colors[i % colors.length]}
                fillOpacity={0.15}
                strokeWidth={2}
              />
            ))}
          </AreaChart>
        );

      case "pie":
        // For pie, use first yKey and the full (non-zoomed) data
        const pieKey = config.yKeys[0];
        // Filter out entries where value is 0 or missing
        const pieData = data.filter(
          (d) => typeof d[pieKey] === "number" && (d[pieKey] as number) > 0
        );
        return (
          <PieChart>
            <Pie
              data={pieData}
              dataKey={pieKey}
              nameKey={config.xKey}
              cx="50%"
              cy="50%"
              outerRadius="80%"
            label={({ name, percent }) => {
              if (percent === undefined) return name;
              return `${name} ${(percent * 100).toFixed(0)}%`;
            }}
              labelLine={false}
            >
              {pieData.map((_entry, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "12px" }} />
          </PieChart>
        );

      default:
        return null;
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      {/* Title */}
      {config.title && (
        <div className="px-5 pt-4 pb-0">
          <h3 className="text-sm font-semibold text-gray-900">{config.title}</h3>
        </div>
      )}

      {/* Controls */}
      <div className="px-4 py-3">
        <ChartControls
          config={config}
          onConfigChange={handleConfigChange}
          dateOptions={dateOptions}
          rangeDays={rangeDays}
          onRangeChange={setRangeDays}
          onCyclePalette={() => setPaletteIdx((i) => i + 1)}
          onExportPNG={handleExportPNG}
          onExportCSV={handleExportCSV}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onResetZoom={handleResetZoom}
        />
      </div>

      {/* Chart render area */}
      <div ref={chartRef} className="px-4 pb-4" style={{ height: 360 }}>
        {zoomedData.length === 0 ? (
          <div className="h-full flex items-center justify-center text-sm text-gray-400">
            No data to display
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            {renderChart() ?? <div />}
          </ResponsiveContainer>
        )}
      </div>

      {/* Zoom indicator */}
      {config.type !== "pie" && zoomedData.length < data.length && (
        <div className="px-5 pb-3">
          <p className="text-xs text-gray-400">
            Showing {zoom.startIndex + 1}–{zoom.endIndex} of {data.length} data points
            {" · "}
            <button
              onClick={handleResetZoom}
              className="text-blue-600 hover:underline"
            >
              Reset zoom
            </button>
          </p>
        </div>
      )}
    </div>
  );
}
