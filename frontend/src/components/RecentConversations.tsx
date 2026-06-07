import type { Conversation } from "@/lib/types";

interface RecentConversationsProps {
  conversations: Conversation[];
  onSelect: (conversation: Conversation) => void;
}

const statusBadge: Record<Conversation["status"], { label: string; className: string }> = {
  completed: { label: "Done", className: "bg-green-100 text-green-700" },
  running: { label: "Running", className: "bg-blue-100 text-blue-700" },
  failed: { label: "Failed", className: "bg-red-100 text-red-700" },
};

export default function RecentConversations({
  conversations,
  onSelect,
}: RecentConversationsProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="px-5 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900">Recent Queries</h3>
      </div>
      <div className="divide-y divide-gray-50">
        {conversations.map((conv) => {
          const badge = statusBadge[conv.status];
          return (
            <button
              key={conv.id}
              onClick={() => onSelect(conv)}
              className="w-full text-left px-5 py-3 hover:bg-gray-50 transition-colors group"
            >
              <div className="flex items-start gap-3">
                <span
                  className={`mt-0.5 text-xs shrink-0 ${
                    conv.status === "failed" ? "text-red-400" : "text-blue-500"
                  }`}
                >
                  ▶
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-800 truncate group-hover:text-blue-600 transition-colors">
                    {conv.query}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-gray-400">{conv.timestamp}</span>
                    {conv.rowCount !== undefined && (
                      <span className="text-xs text-gray-400">
                        {conv.rowCount.toLocaleString()} rows
                      </span>
                    )}
                    {conv.duration && (
                      <span className="text-xs text-gray-400">{conv.duration}</span>
                    )}
                  </div>
                </div>
                <span
                  className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${badge.className}`}
                >
                  {badge.label}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
