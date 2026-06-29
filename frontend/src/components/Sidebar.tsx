"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import { useState } from "react";
import { LayoutDashboard, MessageSquare, Settings, ShieldAlert, ChevronLeft, ChevronRight, LogOut } from "lucide-react";

import { keycloakLogout } from "@/lib/auth";
import { ThemeToggle } from "@/components/ThemeToggle";

export function Sidebar() {
  const pathname = usePathname();
  const { data: session, status } = useSession();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const navItems = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Chat", href: "/chat", icon: MessageSquare },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  const anySession = session as any;
  const roles = anySession?.user?.roles || [];
  if (roles.includes("admin")) {
    navItems.push({ name: "Admin Panel", href: "/admin/schema", icon: ShieldAlert });
  }

  return (
    <div
      className={`bg-white border-r border-gray-200 flex flex-col transition-all duration-300 ease-in-out h-screen relative
        ${isCollapsed ? "w-16" : "w-64"}
      `}
    >
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-6 bg-white border border-gray-200 rounded-full p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 transition-colors z-10 hidden md:block shadow-sm"
        title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>

      <div className={`h-16 flex items-center border-b border-gray-200 overflow-hidden transition-all duration-300 ${isCollapsed ? "justify-center" : "justify-start px-6"}`}>
        <span className={`text-xl font-bold text-blue-600 transition-opacity duration-300 ${isCollapsed ? "hidden" : "block"}`}>
          ARIA
        </span>
        <span className={`text-xl font-bold text-blue-600 transition-opacity duration-300 ${isCollapsed ? "block" : "hidden"}`}>
          A
        </span>
      </div>

      <nav className="flex-1 py-4 flex flex-col gap-2 px-2 overflow-x-hidden">
        {navItems.map((item) => {
          const isActive = item.href === "/" ? pathname === "/" : pathname?.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${isActive
                  ? "bg-blue-50 text-blue-700 font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
              title={item.name}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && (
                <span className="text-sm transition-opacity duration-300">
                  {item.name}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="p-2 border-t border-gray-200">
        <ThemeToggle collapsed={isCollapsed} />
      </div>

      {status === "authenticated" && (
        <div className="p-2 border-t border-gray-200">
          <button
            onClick={() => keycloakLogout(anySession?.idToken || anySession?.user?.idToken)}
            className={`w-full flex items-center px-3 py-2.5 rounded-lg text-red-600 hover:bg-red-50 transition-colors whitespace-nowrap
              ${isCollapsed ? "justify-center" : "justify-start gap-3"}`}
            title="Logout"
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            {!isCollapsed && <span className="text-sm">Logout</span>}
          </button>
        </div>
      )}
    </div>
  );
}
