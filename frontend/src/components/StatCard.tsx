import type { StatCardData } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";

interface StatCardProps {
  data: StatCardData;
}

export default function StatCard({ data }: StatCardProps) {
  const pill =
    data.changeType === "up"
      ? "bg-green-50 text-green-600"
      : data.changeType === "down"
        ? "bg-red-50 text-red-600"
        : "bg-gray-100 text-gray-500";

  const arrow =
    data.changeType === "up" ? "↑" : data.changeType === "down" ? "↓" : "";

  return (
    <Card className="transition-all hover:-translate-y-0.5 hover:shadow-md">
      <CardContent className="p-5 flex flex-col gap-2">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
          {data.label}
        </span>
        <div className="flex items-end justify-between gap-2">
          <span className="text-3xl font-semibold tracking-tight text-gray-900 tabular-nums">
            {data.value}
          </span>
          {data.change && (
            <span
              className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-medium ${pill}`}
            >
              {arrow} {data.change}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
