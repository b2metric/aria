export interface StatCardData {
  label: string;
  value: string;
  change?: string;
  changeType?: "up" | "down" | "neutral";
  icon?: string;
}

export interface Conversation {
  id: string;
  query: string;
  timestamp: string;
  status: "completed" | "running" | "failed";
  rowCount?: number;
  duration?: string;
}

export interface SavedQuery {
  id: string;
  name: string;
  question: string;
  sql: string;
  created_at: string;
}

export interface ChartDataPoint {
  [key: string]: string | number;
}

export interface DashboardData {
  stats: StatCardData[];
  workspaceStats: StatCardData[];
  recentConversations: Conversation[];
  savedQueries: SavedQuery[];
  chartData: ChartDataPoint[];
  chartConfig: ChartConfig;
  filters?: { team_id: string | null; user_id: string | null };
}

/** A selectable team or user for the dashboard activity filters. */
export interface PickerItem {
  id: string;
  name: string;
}

export interface ChartConfig {
  type: "bar" | "line" | "area" | "pie";
  xKey: string;
  yKeys: string[];
  title?: string;
  colors?: string[];
}

export interface FilterState {
  dateRange?: "7d" | "30d" | "90d" | "1y" | "all";
  status?: string;
  search?: string;
}

export interface ZoomState {
  startIndex: number;
  endIndex: number;
}

// ── Chat types ───────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sql?: string;
  chartSpec?: ChartSpec;
  chartHtml?: string;
  chartUrl?: string;
  chartData?: any[]; // The raw JSON rows
  summary?: string;
  suggestions?: string[];
  status?: "streaming" | "complete" | "error";
  error?: string;
}

export interface ChartSpec {
  type: "bar" | "line" | "area" | "pie" | "table" | "scatter";
  title?: string;
  colors?: string[];
  data?: ChartDataPoint[];
  xKey?: string;
  yKeys?: string[];
  chart_html?: string;
  chart_url?: string;
  csv_url?: string;
  row_count?: number;
}

export interface SSEEvent {
  event: string;
  data: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}
