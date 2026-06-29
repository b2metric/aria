"use client";

import { ReactNode, useState } from "react";
import Link from "next/link";
import { Database, Settings, ChevronLeft, ChevronRight, Users, LayoutDashboard, ShieldAlert } from "lucide-react";
import { usePathname } from "next/navigation";

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900">
      <aside 
        className={`bg-white p-6 flex flex-col border-r border-gray-200 relative transition-all duration-300 ease-in-out
          ${isCollapsed ? "w-24" : "w-64"}
        `}
      >
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="absolute -right-3 top-6 bg-white border border-gray-200 rounded-full p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 transition-colors z-10 hidden md:block shadow-sm"
          title={isCollapsed ? "Expand menu" : "Collapse menu"}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>

        <div className={`flex items-center mb-8 transition-all duration-300 ${isCollapsed ? "justify-center gap-0" : "justify-start gap-2"}`}>
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-[#ffffff] font-bold text-xl">A</span>
          </div>
          {!isCollapsed && (
            <span className="font-bold text-xl tracking-wide text-gray-900 whitespace-nowrap overflow-hidden transition-opacity duration-300">
              Workspace
            </span>
          )}
        </div>
        
        <nav className="flex-1 space-y-1 overflow-x-hidden">
          <Link 
            href="/"
            className={`flex items-center p-3 rounded-lg transition-colors whitespace-nowrap text-gray-600 hover:bg-gray-100 hover:text-gray-900 ${isCollapsed ? "justify-center" : "justify-start"}`}
            title={isCollapsed ? "Back to Dashboard" : undefined}
          >
            <LayoutDashboard className={`w-5 h-5 flex-shrink-0 ${isCollapsed ? "" : "mr-3"} text-gray-500`} />
            {!isCollapsed && <span className="font-medium">Back to App</span>}
          </Link>

          <div className="pt-4 pb-2">
            <div className={`text-xs font-semibold text-gray-400 uppercase tracking-wider ${isCollapsed ? "text-center" : "px-3"}`}>
              {isCollapsed ? "---" : "Settings"}
            </div>
          </div>

          <Link 
            href="/settings/team" 
            className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
              ${isCollapsed ? "justify-center" : "justify-start gap-3"}
              ${pathname?.includes("/settings/team") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
            `}
            title="Team Members"
          >
            <Users className="w-5 h-5 flex-shrink-0" />
            {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Team Members</span>}
          </Link>
          
          <Link 
            href="/settings/database" 
            className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
              ${isCollapsed ? "justify-center" : "justify-start gap-3"}
              ${pathname?.includes("/settings/database") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
            `}
            title="Database Connection"
          >
            <Database className="w-5 h-5 flex-shrink-0" />
            {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Database Connection</span>}
          </Link>

          <Link 
            href="/settings/encryption" 
            className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
              ${isCollapsed ? "justify-center" : "justify-start gap-3"}
              ${pathname?.includes("/settings/encryption") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
            `}
            title="Encryption (CMEK)"
          >
            <ShieldAlert className="w-5 h-5 flex-shrink-0" />
            {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Encryption</span>}
          </Link>
          
          <Link 
            href="/settings/general" 
            className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
              ${isCollapsed ? "justify-center" : "justify-start gap-3"}
              ${pathname?.includes("/settings/general") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
            `}
            title="General Settings"
          >
            <Settings className="w-5 h-5 flex-shrink-0" />
            {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">General</span>}
          </Link>
        </nav>
      </aside>
      <main className="flex-1 p-8 overflow-y-auto w-full transition-all duration-300">
        {children}
      </main>
    </div>
  );
}
