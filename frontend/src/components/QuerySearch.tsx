"use client";

import { useState, type KeyboardEvent } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface QuerySearchProps {
  onSearch: (query: string) => void;
}

export default function QuerySearch({ onSearch }: QuerySearchProps) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (trimmed) {
      onSearch(trimmed);
      setValue("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSubmit();
  };

  return (
    <div className="flex items-center gap-2 w-full">
      <div className="relative flex-1">
        <Input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your data..."
          className="w-full pl-4 pr-12 py-6 text-sm rounded-xl"
        />
        <Button
          size="icon"
          onClick={handleSubmit}
          disabled={!value.trim()}
          className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 rounded-lg"
          aria-label="Submit query"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </Button>
      </div>
    </div>
  );
}
