import type { SavedQuery } from "@/lib/types";

interface SavedQueriesProps {
  queries: SavedQuery[];
  onSelect: (query: SavedQuery) => void;
}

export default function SavedQueries({ queries, onSelect }: SavedQueriesProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Saved Queries</h3>
        <span className="text-xs text-gray-400">{queries.length} saved</span>
      </div>
      <div className="divide-y divide-gray-50 max-h-72 overflow-y-auto">
        {queries.map((q) => (
          <button
            key={q.id}
            onClick={() => onSelect(q)}
            className="w-full text-left px-5 py-3 hover:bg-gray-50 transition-colors group"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate group-hover:text-blue-600 transition-colors">
                  {q.name}
                </p>
                <p className="text-xs text-gray-400 truncate mt-0.5">{q.query}</p>
              </div>
              <span className="text-[10px] text-gray-400 whitespace-nowrap">
                {q.lastRun ? `Last: ${q.lastRun}` : `Created: ${q.createdAt}`}
              </span>
            </div>
            {q.tags && q.tags.length > 0 && (
              <div className="flex gap-1 mt-2">
                {q.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
