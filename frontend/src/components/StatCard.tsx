import type { StatCardData } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

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
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-5 flex flex-col gap-1">
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
      </CardContent>
    </Card>
  );
}
