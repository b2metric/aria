import type { SavedQuery } from "@/lib/types";

interface SavedQueriesProps {
  queries: SavedQuery[];
  onSelect: (query: SavedQuery) => void;
  onDelete?: (id: string) => void;
}

export default function SavedQueries({ queries, onSelect, onDelete }: SavedQueriesProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Saved Queries</h3>
        <span className="text-xs text-gray-400">{queries.length} saved</span>
      </div>
      <div className="divide-y divide-gray-50 max-h-72 overflow-y-auto">
        {queries.length === 0 && (
          <p className="px-5 py-8 text-center text-sm text-gray-400">
            No saved queries yet. Save one from a chat answer to see it here.
          </p>
        )}
        {queries.map((q) => (
          <div key={q.id} className="flex items-start gap-2 px-5 py-3 hover:bg-gray-50 transition-colors group">
            <button onClick={() => onSelect(q)} className="flex-1 min-w-0 text-left">
              <p className="text-sm font-medium text-gray-800 truncate group-hover:text-blue-600 transition-colors">
                {q.name}
              </p>
              <p className="text-xs text-gray-400 truncate mt-0.5">{q.question}</p>
            </button>
            <span className="text-[10px] text-gray-400 whitespace-nowrap pt-0.5">
              {new Date(q.created_at).toLocaleDateString()}
            </span>
            {onDelete && (
              <button
                onClick={() => onDelete(q.id)}
                aria-label="Delete saved query"
                className="text-gray-300 hover:text-red-500 text-xs px-1"
              >
                ✕
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
