"use client";

import { Settings } from "lucide-react";

export default function GeneralSettings() {
  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Settings className="w-6 h-6 text-blue-600" />
            General Settings
          </h1>
          <p className="text-gray-500 mt-1">Manage your workspace preferences.</p>
        </div>
      </div>
      
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Workspace Details</h3>
        <p className="text-gray-600">Your workspace configuration options will appear here.</p>
      </div>
    </div>
  );
}
