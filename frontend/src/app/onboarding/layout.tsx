"use client";

import { ReactNode } from "react";
import { Database, CheckCircle2, Server } from "lucide-react";
import { usePathname } from "next/navigation";

export default function OnboardingLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  
  const steps = [
    { id: "database", title: "Connect Database", icon: Database },
    { id: "sync", title: "Sync Schema", icon: Server },
    { id: "done", title: "Ready", icon: CheckCircle2 }
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xl">A</span>
              </div>
              <span className="font-bold text-xl tracking-wide text-gray-900">ARIA</span>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 max-w-3xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <nav aria-label="Progress" className="mb-12">
          <ol role="list" className="flex items-center">
            {steps.map((step, stepIdx) => (
              <li key={step.title} className={`relative ${stepIdx !== steps.length - 1 ? 'pr-8 sm:pr-20' : ''}`}>
                <div className="flex items-center">
                  <div className={`
                    relative flex h-8 w-8 items-center justify-center rounded-full 
                    ${pathname.includes(step.id) 
                      ? 'bg-blue-600 ring-4 ring-blue-100' 
                      : pathname === '/onboarding/done' || (stepIdx === 0 && pathname.includes('sync'))
                        ? 'bg-blue-600'
                        : 'bg-gray-200'}
                  `}>
                    <step.icon className={`h-5 w-5 ${pathname.includes(step.id) || pathname === '/onboarding/done' || (stepIdx === 0 && pathname.includes('sync')) ? 'text-white' : 'text-gray-500'}`} />
                  </div>
                  <div className="ml-4 hidden sm:block">
                    <p className={`text-sm font-medium ${pathname.includes(step.id) ? 'text-blue-600' : 'text-gray-500'}`}>
                      {step.title}
                    </p>
                  </div>
                </div>
                {stepIdx !== steps.length - 1 ? (
                  <div className="absolute top-4 left-0 -ml-px mt-0.5 h-0.5 w-full bg-gray-200" aria-hidden="true" />
                ) : null}
              </li>
            ))}
          </ol>
        </nav>

        <div className="bg-white shadow rounded-lg p-6 sm:p-8">
          {children}
        </div>
      </div>
    </div>
  );
}
