import type { StatCardData } from "@/lib/types";

interface StatCardProps {
  data: StatCardData;
}

export default function StatCard({ data }: StatCardProps) {
  const changeColor =
    data.changeType === "up"
      ? "text-green-500"
      : data.changeType === "down"
        ? "text-red-500"
        : "text-gray-400";

  const changeArrow =
    data.changeType === "up" ? "↑" : data.changeType === "down" ? "↓" : "";

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-1 shadow-sm hover:shadow-md transition-shadow">
      <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
        {data.label}
      </span>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold text-gray-900">{data.value}</span>
        {data.change && (
          <span className={`text-xs font-medium ${changeColor}`}>
            {changeArrow} {data.change}
          </span>
        )}
      </div>
    </div>
  );
}
