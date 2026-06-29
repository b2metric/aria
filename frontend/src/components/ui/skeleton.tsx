import * as React from "react"
import { cn } from "@/lib/utils"

/** Loading placeholder. Use to reserve layout while async data loads
 *  instead of a blank screen or "Loading..." text. */
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-gray-200/70", className)}
      aria-hidden="true"
      {...props}
    />
  )
}

export { Skeleton }
