"use client";

import { useEffect, useState } from "react";
import { Sun, Moon, Monitor } from "lucide-react";
import { getThemePreference, setThemePreference, type ThemePreference } from "@/lib/theme";

const OPTIONS: { value: ThemePreference; label: string; Icon: typeof Sun }[] = [
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
  { value: "system", label: "System", Icon: Monitor },
];

export default function AppearanceSettings() {
  const [pref, setPref] = useState<ThemePreference>("system");

  // Sync from the value the no-flicker inline script already applied.
  useEffect(() => setPref(getThemePreference()), []);

  const choose = (value: ThemePreference) => {
    setPref(value);
    setThemePreference(value);
  };

  return (
    <div className="max-w-2xl mx-auto py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Appearance</h1>
        <p className="text-gray-500 mt-1">Choose how ARIA looks on this browser.</p>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <p id="theme-group-label" className="text-sm font-medium text-gray-700 mb-3">Theme</p>
        <div role="group" aria-labelledby="theme-group-label" className="grid grid-cols-3 gap-3">
          {OPTIONS.map(({ value, label, Icon }) => {
            const active = pref === value;
            return (
              <button
                key={value}
                type="button"
                aria-pressed={active}
                onClick={() => choose(value)}
                className={`flex flex-col items-center justify-center gap-2 rounded-lg border px-4 py-5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                  active
                    ? "border-blue-600 bg-blue-50 text-blue-700"
                    : "border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`}
              >
                <Icon className="h-5 w-5" />
                {label}
              </button>
            );
          })}
        </div>
        <p className="mt-3 text-xs text-gray-500">
          This preference is stored in your browser. &quot;System&quot; follows your OS setting.
        </p>
      </div>
    </div>
  );
}
