import type { PickerItem } from "@/lib/types";

interface DashboardFiltersProps {
  teams: PickerItem[];
  users: PickerItem[];
  teamId?: string;
  userId?: string;
  onChange: (next: { teamId?: string; userId?: string }) => void;
}

const selectClass =
  "rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 " +
  "focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-400";

/**
 * Two compact pickers (Team, User) for filtering the workspace-activity
 * cards + trend. Each defaults to "All". Empty string from a <select> means
 * "no filter", which we surface as `undefined` to the parent.
 */
export default function DashboardFilters({
  teams,
  users,
  teamId,
  userId,
  onChange,
}: DashboardFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <label className="flex items-center gap-2 text-xs font-medium text-gray-500">
        Team
        <select
          className={selectClass}
          value={teamId ?? ""}
          onChange={(e) =>
            onChange({ teamId: e.target.value || undefined, userId })
          }
        >
          <option value="">All teams</option>
          {teams.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-xs font-medium text-gray-500">
        User
        <select
          className={selectClass}
          value={userId ?? ""}
          onChange={(e) =>
            onChange({ teamId, userId: e.target.value || undefined })
          }
        >
          <option value="">All users</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
