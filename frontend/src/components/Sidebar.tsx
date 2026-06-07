"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";

const NAV_ITEMS = [
  { icon: "◈", label: "Dashboard", href: "/" },
  { icon: "💬", label: "Conversations", href: "/chat" },
  { icon: "📊", label: "Saved Queries", href: "/saved" },
  { icon: "🗄️", label: "Semantic Vault", href: "/vault" },
  { icon: "⚙️", label: "Settings", href: "/settings" },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      className={`flex flex-col bg-gray-950 text-white transition-all duration-200 ${
        collapsed ? "w-14" : "w-52"
      }`}
    >
      {/* Brand */}
      <div className="flex items-center gap-2 px-4 py-4 border-b border-gray-800">
        <span className="text-xl font-bold tracking-tight">ARIA</span>
        {!collapsed && (
          <span className="text-xs text-gray-500 ml-auto">v0.1</span>
        )}
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-2 py-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.label}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white"
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="p-3 text-gray-500 hover:text-white hover:bg-gray-800 transition-colors border-t border-gray-800"
        aria-label="Toggle sidebar"
      >
        {collapsed ? "▶" : "◀"}
      </button>
    </aside>
  );
}
