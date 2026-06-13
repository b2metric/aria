"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  className?: string;
}

export function Checkbox({
  checked,
  onCheckedChange,
  className,
  disabled,
  id,
  ...props
}: CheckboxProps) {
  return (
    <input
      type="checkbox"
      id={id}
      checked={checked}
      disabled={disabled}
      onChange={(e) => onCheckedChange?.(e.target.checked)}
      className={cn(
        "peer h-4 w-4 shrink-0 rounded-sm border border-gray-300 bg-white",
        "text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "cursor-pointer accent-blue-600",
        className
      )}
      {...props}
    />
  );
}
