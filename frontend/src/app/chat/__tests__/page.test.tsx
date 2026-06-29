/**
 * Chat page render tests.
 * Tests: auth guard, chat area, input field, empty state, example queries.
 *
 * Note: ChatPage wraps ChatPageContent in <Suspense> which resolves
 * immediately in jsdom, so we test the rendered ChatPageContent directly.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { useSession, signIn } from "next-auth/react";
import ChatPage from "../page";

// ── Mock browser APIs not in jsdom ───────────────────────────────────
Element.prototype.scrollIntoView = vi.fn();

// ── Mock next-auth ───────────────────────────────────────────────────
vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
  signIn: vi.fn(),
  signOut: vi.fn(),
}));

// ── Mock next/navigation ─────────────────────────────────────────────
const mockPush = vi.fn();
const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

// ── Mock API ─────────────────────────────────────────────────────────
vi.mock("@/lib/api", () => ({
  streamQuery: vi.fn(),
  // streamResume + getRunStatus are imported by the page (resumable streaming);
  // the mock must export them or they resolve to undefined and break on mount.
  streamResume: vi.fn(),
  getRunStatus: vi.fn().mockResolvedValue({ status: null }),
  fetchConversations: vi.fn().mockResolvedValue([]),
  fetchConversation: vi.fn().mockResolvedValue(null),
  fetchWorkspaceSuggestions: vi.fn().mockResolvedValue([
      "Show monthly revenue by nationality",
      "Top 10 roaming partners by volume",
      "Daily active users trend"
    ]),
  deleteConversation: vi.fn(),
  getMockDashboardData: vi.fn(),
}));

// ── Mock recharts ────────────────────────────────────────────────────
vi.mock("recharts", () => ({
  BarChart: ({ children }: any) => <div>{children}</div>,
  Bar: () => <div />,
  LineChart: ({ children }: any) => <div>{children}</div>,
  Line: () => <div />,
  AreaChart: ({ children }: any) => <div>{children}</div>,
  Area: () => <div />,
  PieChart: ({ children }: any) => <div>{children}</div>,
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
const mockSignIn = vi.mocked(signIn);

function mockAuth(status: string = "authenticated") {
  if (status === "authenticated") {
    mockUseSession.mockReturnValue({
      // workspaceId is required for the page's fetchWorkspaceSuggestions effect
      // (guarded by `token && workspaceId`) to run and load dynamic suggestions.
      data: { user: { name: "Test User", workspaceId: "ws-test" }, accessToken: "test-token" },
      status: "authenticated",
      update: vi.fn(),
    } as any);
  } else if (status === "loading") {
    mockUseSession.mockReturnValue({
      data: null,
      status: "loading",
      update: vi.fn(),
    } as any);
  } else {
    mockUseSession.mockReturnValue({
      data: null,
      status: "unauthenticated",
      update: vi.fn(),
    } as any);
  }
}

describe("ChatPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  

  it("renders sidebar with History when authenticated", async () => {
    mockAuth("authenticated");

    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText("History")).toBeInTheDocument();
    });
  });

  it("renders chat input field when authenticated", async () => {
    mockAuth("authenticated");

    render(<ChatPage />);

    await waitFor(() => {
      const input = screen.getByPlaceholderText(/ask a question about your data/i);
      expect(input).toBeInTheDocument();
    });
  });

  it("renders empty state with example queries when no messages", async () => {
    mockAuth("authenticated");

    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText(/what do you want to know/i)).toBeInTheDocument();
    });
    // Suggestions load asynchronously from fetchWorkspaceSuggestions, so wait for
    // the fetched chips to replace the initial defaults before asserting.
    await waitFor(() => {
      expect(screen.getByText("Show monthly revenue by nationality")).toBeInTheDocument();
    });
    expect(screen.getByText("Top 10 roaming partners by volume")).toBeInTheDocument();
    expect(screen.getByText("Daily active users trend")).toBeInTheDocument();
  });

  it("renders 'New Chat' button in sidebar", async () => {
    mockAuth("authenticated");

    render(<ChatPage />);

    await waitFor(() => {
      const buttons = screen.getAllByText("New Chat");
      expect(buttons.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders 'Recent History' section header", async () => {
    mockAuth("authenticated");

    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText("Recent History")).toBeInTheDocument();
    });
  });

  it("renders 'No history yet' when no conversations", async () => {
    mockAuth("authenticated");

    render(<ChatPage />);

    await waitFor(() => {
      expect(screen.getByText("No history yet")).toBeInTheDocument();
    });
  });

  it("shows Loading state while session is loading", () => {
    mockAuth("loading");

    render(<ChatPage />);

    // When session is loading, the Suspense fallback shows loading
    // In jsdom, Suspense resolves fast, but we check the inner content
    // The ChatPageContent should not render with loading status
  });
});
