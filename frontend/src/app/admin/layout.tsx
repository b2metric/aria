"use client";

import { ReactNode, useState } from "react";
import Link from "next/link";
import { Database, Settings, ShieldAlert, ChevronLeft, ChevronRight, Users, Brain, Lock, Activity, Cpu, Link2, MessagesSquare, Boxes, BookOpen, KeyRound } from "lucide-react";
import { usePathname } from "next/navigation";
import { AdminGuard } from "@/components/AdminGuard";

export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <AdminGuard>
      <div className="flex h-screen bg-gray-50 text-gray-900">
        <aside 
          className={`bg-white p-6 flex flex-col border-r border-gray-200 relative transition-all duration-300 ease-in-out
            ${isCollapsed ? "w-24" : "w-64"}
          `}
        >
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="absolute -right-3 top-6 bg-white border border-gray-200 rounded-full p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 transition-colors z-10 hidden md:block shadow-sm"
            title={isCollapsed ? "Expand admin menu" : "Collapse admin menu"}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>

          <div className={`flex items-center mb-8 transition-all duration-300 ${isCollapsed ? "justify-center gap-0" : "justify-start gap-2"}`}>
            <ShieldAlert className="w-6 h-6 text-blue-600 flex-shrink-0" />
            {!isCollapsed && (
              <span className="font-bold text-xl tracking-wide text-blue-600 whitespace-nowrap overflow-hidden transition-opacity duration-300">
                ARIA Admin
              </span>
            )}
          </div>
          
          <nav className="flex-1 space-y-1 overflow-x-hidden">

            <Link 
              href="/admin/health"
              className={`flex items-center p-3 rounded-lg transition-colors whitespace-nowrap ${
                pathname === "/admin/health" 
                  ? "bg-blue-50 text-blue-700" 
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              } ${isCollapsed ? "justify-center" : "justify-start"}`}
              title={isCollapsed ? "System Health" : undefined}
            >
              <Activity className={`w-5 h-5 flex-shrink-0 ${isCollapsed ? "" : "mr-3"} ${pathname === "/admin/health" ? "text-blue-600" : "text-gray-500"}`} />
              {!isCollapsed && <span className="font-medium">System Health</span>}
            </Link>

            <Link
              href="/admin/consoles"
              className={`flex items-center p-3 rounded-lg transition-colors whitespace-nowrap ${
                pathname === "/admin/consoles"
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              } ${isCollapsed ? "justify-center" : "justify-start"}`}
              title={isCollapsed ? "Service Consoles" : undefined}
            >
              <Boxes className={`w-5 h-5 flex-shrink-0 ${isCollapsed ? "" : "mr-3"} ${pathname === "/admin/consoles" ? "text-blue-600" : "text-gray-500"}`} />
              {!isCollapsed && <span className="font-medium">Service Consoles</span>}
            </Link>



            <Link 
              href="/admin/memory" 
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/memory") && !pathname?.includes("team-memory") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="Memory Manager"
            >
              <Brain className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Agent Memory</span>}
            </Link>
            
            <Link 
              href="/admin/team-memory" 
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/team-memory") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="Team Conventions"
            >
              <BookOpen className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Team Conventions</span>}
            </Link>
            
            <Link 
              href="/admin/tenant-config" 
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/tenant-config") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="Tenant Config"
            >
              <Settings className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Tenant Config</span>}
            </Link>
            <Link
              href="/admin/encryption"
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/encryption") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="Encryption (CMEK)"
            >
              <KeyRound className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Encryption</span>}
            </Link>
            <Link
              href="/admin/llm-config"
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/llm-config") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="LLM Config"
            >
              <Cpu className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">LLM Config</span>}
            </Link>

            
            <Link 
              href="/admin/schema" 
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/schema") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="Vault Schema"
            >
              <Database className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Vault Schema</span>}
            </Link>
            
            <Link
              href="/admin/conversations"
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/conversations") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="Conversation Debug"
            >
              <MessagesSquare className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Conversations</span>}
            </Link>

            <Link
              href="/admin/audit-log"
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/audit-log") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="Audit Logs"
            >
              <ShieldAlert className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Audit Logs</span>}
            </Link>
            
            <Link 
              href="/admin/vault-access" 
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/vault-access") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="Vault Access"
            >
              <Lock className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Vault Access</span>}
            </Link>

            <Link
              href="/admin/join-keys"
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/join-keys") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="Join Keys"
            >
              <Link2 className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Join Keys</span>}
            </Link>

            <Link
              href="/admin/users"
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/users") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="Users & Teams"
            >
              <Users className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Users & Teams</span>}
            </Link>

            <Link 
              href="/admin/tokens" 
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/tokens") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="Token Management"
            >
              <Settings className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Token Quotas</span>}
            </Link>
          </nav>
        </aside>
        <main className="flex-1 p-8 overflow-y-auto w-full transition-all duration-300">
          {children}
        </main>
      </div>
    </AdminGuard>
  );
}
