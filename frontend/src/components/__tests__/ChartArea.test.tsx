/**
 * ChartArea component render tests.
 * Tests: rendering with different chart types, empty data, title display.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import ChartArea from "../ChartArea";
import type { ChartConfig, ChartDataPoint, FilterState } from "@/lib/types";

// ── Mock recharts (avoid SVG complexity in jsdom) ────────────────────
vi.mock("recharts", () => ({
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div />,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div />,
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  Area: () => <div />,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => <div />,
  Cell: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  CartesianGrid: () => <div />,
  Tooltip: () => <div />,
  Legend: () => <div />,
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
}));

const mockData: ChartDataPoint[] = [
  { month: "Jan", revenue: 2400, costs: 1800 },
  { month: "Feb", revenue: 1398, costs: 1200 },
  { month: "Mar", revenue: 9800, costs: 7200 },
];

const barConfig: ChartConfig = {
  type: "bar",
  xKey: "month",
  yKeys: ["revenue", "costs"],
  title: "Monthly Revenue vs Costs",
};

const emptyFilters: FilterState = {};
const noop = () => {};

describe("ChartArea", () => {
  it("renders chart title", () => {
    render(
      <ChartArea
        data={mockData}
        config={barConfig}
        filters={emptyFilters}
        onFilterChange={noop}
      />
    );

    expect(screen.getByText("Monthly Revenue vs Costs")).toBeInTheDocument();
  });

  it("renders bar chart for bar config type", () => {
    render(
      <ChartArea
        data={mockData}
        config={barConfig}
        filters={emptyFilters}
        onFilterChange={noop}
      />
    );

    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });

  it("renders line chart for line config type", () => {
    render(
      <ChartArea
        data={mockData}
        config={{ ...barConfig, type: "line" }}
        filters={emptyFilters}
        onFilterChange={noop}
      />
    );

    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
  });

  it("renders area chart for area config type", () => {
    render(
      <ChartArea
        data={mockData}
        config={{ ...barConfig, type: "area" }}
        filters={emptyFilters}
        onFilterChange={noop}
      />
    );

    expect(screen.getByTestId("area-chart")).toBeInTheDocument();
  });

  it("renders pie chart for pie config type", () => {
    render(
      <ChartArea
        data={mockData}
        config={{ ...barConfig, type: "pie" }}
        filters={emptyFilters}
        onFilterChange={noop}
      />
    );

    expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
  });

  it("shows 'No data' message for empty data array", () => {
    render(
      <ChartArea
        data={[]}
        config={barConfig}
        filters={emptyFilters}
        onFilterChange={noop}
      />
    );

    expect(screen.getByText(/no data to display/i)).toBeInTheDocument();
  });

  it("renders chart controls with type switcher buttons", () => {
    render(
      <ChartArea
        data={mockData}
        config={barConfig}
        filters={emptyFilters}
        onFilterChange={noop}
      />
    );

    expect(screen.getByText("Bar")).toBeInTheDocument();
    expect(screen.getByText("Line")).toBeInTheDocument();
    expect(screen.getByText("Area")).toBeInTheDocument();
    expect(screen.queryByText("Pie")).not.toBeInTheDocument();
  });

  it("renders export buttons", () => {
    render(
      <ChartArea
        data={mockData}
        config={barConfig}
        filters={emptyFilters}
        onFilterChange={noop}
      />
    );

    expect(screen.getByText("PNG")).toBeInTheDocument();
    expect(screen.getByText("CSV")).toBeInTheDocument();
  });
});
