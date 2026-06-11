"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";

export default function TenantConfigPage() {
  const { data: session } = useSession();
  const [tokenLimit, setTokenLimit] = useState(50000);
  const [rowLimit, setRowLimit] = useState(1000);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    // Simulate API call to save config
    setTimeout(() => {
      setIsSaving(false);
      alert("Tenant configuration saved successfully.");
    }, 800);
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Tenant Configuration</h1>
        <p className="text-gray-500">Manage system-wide limits and behavior for the current tenant.</p>
      </div>
      
      <div className="space-y-6 bg-white border border-gray-200 p-8 rounded-xl shadow-sm">
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Daily Token Limit (Per User/Team)</label>
          <input 
            type="number" 
            value={tokenLimit}
            onChange={(e) => setTokenLimit(Number(e.target.value))}
            className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
          <p className="text-xs text-gray-500 mt-2">Applies to all LLM requests including local/Ollama models.</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Max Row Limit per Query</label>
          <input 
            type="number" 
            value={rowLimit}
            onChange={(e) => setRowLimit(Number(e.target.value))}
            className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
          <p className="text-xs text-gray-500 mt-2">Queries exceeding this limit will trigger a high-row artifact upload to MinIO.</p>
        </div>

        <div className="pt-6 border-t border-gray-100">
          <button 
            onClick={handleSave}
            disabled={isSaving}
            className={`px-6 py-2.5 rounded-lg font-medium transition-all ${
              isSaving 
                ? "bg-blue-100 text-blue-400 cursor-not-allowed" 
                : "bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow-md"
            }`}
          >
            {isSaving ? "Saving..." : "Save Configuration"}
          </button>
        </div>

      </div>
    </div>
  );
}
