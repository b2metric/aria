"use client";

import { useCallback, useRef, useState } from "react";
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

function CustomTooltip({ active, payload, label }: TooltipProps<PayloadValue, string>) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-lg p-3 text-xs">
      <p className="font-medium text-gray-800 mb-1">{label}</p>
      {payload.map((entry, i: number) => (
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

export default function ChartArea({
  data,
  config: initialConfig,
  filters,
  onFilterChange,
}: ChartAreaProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [config, setConfig] = useState<ChartConfig>(initialConfig);
  const [zoom, setZoom] = useState<ZoomState>({ startIndex: 0, endIndex: data.length });

  const zoomedData = data.slice(zoom.startIndex, zoom.endIndex);
  const colors = config.colors || COLORS;

  const handleExportPNG = useCallback(async () => {
    if (!chartRef.current) return;
    try {
      const html2canvas = (await import("html2canvas")).default;
      const canvas = await html2canvas(chartRef.current, {
        backgroundColor: "#ffffff",
        scale: 2,
      });
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `chart-${Date.now()}.png`;
          a.click();
          URL.revokeObjectURL(url);
        }
      });
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
              label={({ name, percent }) =>
                `${name} ${(percent * 100).toFixed(0)}%`
              }
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
          filters={filters}
          onFilterChange={onFilterChange}
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
