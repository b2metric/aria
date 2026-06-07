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
  query: string;
  createdAt: string;
  lastRun?: string;
  tags?: string[];
}

export interface ChartDataPoint {
  [key: string]: string | number;
}

export interface DashboardData {
  stats: StatCardData[];
  recentConversations: Conversation[];
  savedQueries: SavedQuery[];
  chartData: ChartDataPoint[];
  chartConfig: ChartConfig;
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
