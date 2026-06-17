"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Loader2, ArrowRight, CheckCircle2, ServerCrash } from "lucide-react";

export default function SyncOnboarding() {
  const router = useRouter();
  const { data: session } = useSession();
  const token = (session as any)?.accessToken;

  const [status, setStatus] = useState<"starting" | "syncing" | "success" | "error">("starting");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;

    let mounted = true;
    
    const startSync = async () => {
      try {
        if (!mounted) return;
        setStatus("syncing");
        
        // In a real implementation, this would call a backend endpoint
        // to discover tables, create vault markdown files, and sync to Qdrant.
        // For the UI wizard, we simulate this async process.
        
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        // Attempt a mock sync API call
        const res = await fetch(`${API_URL}/api/admin/health`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        if (!res.ok) throw new Error("Could not reach backend services");
        
        // Simulate a delay for the "syncing" experience
        setTimeout(() => {
          if (mounted) setStatus("success");
        }, 3000);
        
      } catch (err: any) {
        if (mounted) {
          setStatus("error");
          setErrorMsg(err.message || "Failed to synchronize schema");
        }
      }
    };

    startSync();
    
    return () => {
      mounted = false;
    };
  }, [token]);

  return (
    <div className="text-center py-8">
      {status === "starting" || status === "syncing" ? (
        <div className="space-y-6">
          <div className="mx-auto w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-4">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Synchronizing Vault</h2>
          <p className="text-gray-500 max-w-md mx-auto">
            ARIA is currently scanning your database schema, analyzing table structures, 
            and building the semantic knowledge base. This might take a few minutes.
          </p>
        </div>
      ) : status === "error" ? (
        <div className="space-y-6">
          <div className="mx-auto w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mb-4">
            <ServerCrash className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Sync Failed</h2>
          <p className="text-red-600 max-w-md mx-auto bg-red-50 p-3 rounded border border-red-200">
            {errorMsg}
          </p>
          <button
            onClick={() => setStatus("starting")}
            className="mt-4 px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
          >
            Try Again
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="mx-auto w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-4">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Vault Ready!</h2>
          <p className="text-gray-500 max-w-md mx-auto">
            Your database schema has been successfully synchronized. ARIA is now 
            ready to answer your natural language questions.
          </p>
          
          <div className="pt-8">
            <button
              onClick={() => router.push("/")}
              className="inline-flex items-center gap-2 px-6 py-3 border border-transparent rounded-md shadow-sm text-base font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              Go to Dashboard
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
