"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, MessageSquare, Database, Settings } from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Chat", href: "/chat", icon: MessageSquare },
    { name: "Schema", href: "/schema", icon: Database },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  return (
    <div className="w-16 md:w-64 bg-white border-r border-gray-200 flex flex-col transition-all h-screen">
      <div className="h-16 flex items-center justify-center md:justify-start md:px-6 border-b border-gray-200">
        <span className="text-xl font-bold text-blue-600 hidden md:block">ARIA</span>
        <span className="text-xl font-bold text-blue-600 md:hidden">A</span>
      </div>
      <nav className="flex-1 py-4 flex flex-col gap-2 px-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                isActive
                  ? "bg-blue-50 text-blue-700 font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
              title={item.name}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              <span className="hidden md:block text-sm">{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
