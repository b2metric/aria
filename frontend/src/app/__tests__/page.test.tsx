/**
 * Dashboard page render tests.
 * Tests: auth guard, loading state, rendered state, stat cards, search navigation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession } from "next-auth/react";
import DashboardPage from "../page";

// ── Mock next-auth ───────────────────────────────────────────────────
vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
  signIn: vi.fn(),
}));
// The dashboard page fetches GET /api/dashboard directly; pull the same mock
// shape the @/lib/api mock exposes so we can stub `fetch` with it.
import { getMockDashboardData } from "@/lib/api";

// ── Mock next/navigation ─────────────────────────────────────────────
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => new URLSearchParams(),
}));

// ── Mock API ─────────────────────────────────────────────────────────
const mockDashboard = {
  stats: [
    { label: "Total Queries", value: "12.4K", change: "+14%", changeType: "up" as const },
    { label: "Accuracy", value: "94.2%", change: "+2.1%", changeType: "up" as const },
    { label: "Avg Response", value: "1.8s", change: "-0.3s", changeType: "down" as const },
    { label: "Active Users", value: "342", change: "+8%", changeType: "up" as const },
  ],
  workspaceStats: [],
  recentConversations: [
    {
      id: "c1",
      query: "Show me prepaid revenue by region",
      timestamp: "2 min ago",
      status: "completed" as const,
      rowCount: 142,
      duration: "1.2s",
    },
  ],
  savedQueries: [
    {
      id: "s1",
      name: "Monthly Revenue",
      query: "Show monthly prepaid revenue",
      createdAt: "2026-05-15",
      tags: ["revenue"],
    },
  ],
  chartData: [
    { month: "Jan", revenue: 2400 },
    { month: "Feb", revenue: 1398 },
  ],
  chartConfig: {
    type: "bar" as const,
    xKey: "month",
    yKeys: ["revenue"],
    title: "Monthly Revenue",
  },
};
const mockFetchConversations = vi.fn();
vi.mock("@/lib/api", () => ({
  getMockDashboardData: () => mockDashboard,
  getDashboard: async () => mockDashboard,
  fetchConversations: (...args: any[]) => mockFetchConversations(...args),
  listSavedQueries: async () => mockDashboard.savedQueries,
  deleteSavedQuery: async () => undefined,
  listAdminTeams: async () => [],
  listAdminUsers: async () => [],
}));

// ── Mock recharts (avoid SVG rendering in jsdom) ─────────────────────
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

const mockUseSession = vi.mocked(useSession);

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchConversations.mockResolvedValue([]);
    // The page loads dashboard data via `fetch(GET /api/dashboard)`; stub it.
    global.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => getMockDashboardData(),
    })) as unknown as typeof fetch;
  });

  it("redirects to /login when unauthenticated", () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "unauthenticated",
      update: vi.fn(),
    } as any);

    render(<DashboardPage />);

    expect(mockPush).toHaveBeenCalledWith("/login");
  });

  it("renders loading indicator while session is loading", () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "loading",
      update: vi.fn(),
    } as any);

    const { container } = render(<DashboardPage />);

    // When status is "loading", the component shows a skeleton placeholder
    // (aria-busy region) instead of a blank screen or plain text.
    expect(container.querySelector('[aria-busy="true"]')).toBeInTheDocument();
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("renders dashboard heading when authenticated", async () => {
    mockUseSession.mockReturnValue({
      data: { user: { name: "Test" }, accessToken: "token" },
      status: "authenticated",
      update: vi.fn(),
    } as any);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });
  });

  it("renders all four stat cards with values", async () => {
    mockUseSession.mockReturnValue({
      data: { user: { name: "Test" }, accessToken: "token" },
      status: "authenticated",
      update: vi.fn(),
    } as any);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Total Queries")).toBeInTheDocument();
      expect(screen.getByText("12.4K")).toBeInTheDocument();
      expect(screen.getByText("Accuracy")).toBeInTheDocument();
      expect(screen.getByText("Avg Response")).toBeInTheDocument();
      expect(screen.getByText("Active Users")).toBeInTheDocument();
    });
  });

  it("renders chart with title from mock data", async () => {
    mockUseSession.mockReturnValue({
      data: { user: { name: "Test" }, accessToken: "token" },
      status: "authenticated",
      update: vi.fn(),
    } as any);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Monthly Revenue")).toBeInTheDocument();
    });
  });

  it("renders Recent and Saved query tabs", async () => {
    mockUseSession.mockReturnValue({
      data: { user: { name: "Test" }, accessToken: "token" },
      status: "authenticated",
      update: vi.fn(),
    } as any);

    render(<DashboardPage />);

    await waitFor(() => {
      const recentElements = screen.getAllByText("Recent Queries");
      expect(recentElements.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Saved Queries")).toBeInTheDocument();
    });
  });

  it("navigates to /chat on search submit", async () => {
    mockUseSession.mockReturnValue({
      data: { user: { name: "Test" }, accessToken: "token" },
      status: "authenticated",
      update: vi.fn(),
    } as any);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });

    // Find the search input and submit
    const input = screen.getByPlaceholderText(/ask a question/i);
    await userEvent.type(input, "revenue{Enter}");

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("/chat?q=revenue")
    );
  });
});
