"use client";
import { useState } from "react";
import DocumentsPanel from "../../components/DocumentsPanel";
import EvidenceSearch from "../../components/EvidenceSearch";
import AnalysisWithEvidence from "../../components/AnalysisWithEvidence";
import EvidenceAdminPanel from "../../components/EvidenceAdminPanel";

export default function TestEvidencePage() {
  const [activeComponent, setActiveComponent] = useState<'documents' | 'search' | 'analysis' | 'admin'>('documents');

  // Mock engagement ID for testing
  const mockEngagementId = "test-engagement-123";

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Evidence Features Test</h1>
        <div className="text-sm text-gray-500">
          Mock Engagement: {mockEngagementId}
        </div>
      </div>

      {/* Component Selector */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {[
            { id: 'documents', label: 'Documents Panel' },
            { id: 'search', label: 'Evidence Search' },
            { id: 'analysis', label: 'AI Analysis' },
            { id: 'admin', label: 'Admin Panel' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveComponent(tab.id as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeComponent === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Mock URL update to test routing */}
      <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded">
        Note: This is a test page. Components expect engagement ID from URL params.
        Current URL should be: /e/{mockEngagementId}/dashboard
      </div>

      {/* Component Display */}
      <div className="min-h-96">
        {activeComponent === 'documents' && (
          <div>
            <h2 className="text-lg font-medium mb-4">Documents Panel</h2>
            <DocumentsPanel />
          </div>
        )}

        {activeComponent === 'search' && (
          <div>
            <h2 className="text-lg font-medium mb-4">Evidence Search</h2>
            <EvidenceSearch className="max-w-4xl" />
          </div>
        )}

        {activeComponent === 'analysis' && (
          <div>
            <h2 className="text-lg font-medium mb-4">AI Analysis with Evidence</h2>
            <AnalysisWithEvidence 
              className="max-w-4xl"
              initialContent="Analyze the security posture of our AI systems"
            />
          </div>
        )}

        {activeComponent === 'admin' && (
          <div>
            <h2 className="text-lg font-medium mb-4">Evidence Admin Panel</h2>
            <EvidenceAdminPanel className="max-w-2xl" />
          </div>
        )}
      </div>

      {/* Feature Status */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-medium mb-2">Implementation Status</h3>
        <div className="text-sm space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-green-600">✓</span>
            <span>TypeScript types for Evidence and RAG features</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-green-600">✓</span>
            <span>Enhanced Documents Panel with ingestion status</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-green-600">✓</span>
            <span>Evidence Search component with highlighting</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-green-600">✓</span>
            <span>Analysis component with evidence integration</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-green-600">✓</span>
            <span>AAD Authentication context and UI</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-green-600">✓</span>
            <span>API proxy routes for backend integration</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-green-600">✓</span>
            <span>Admin panel for bulk operations</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-green-600">✓</span>
            <span>Mobile responsive design</span>
          </div>
        </div>
      </div>
    </div>
  );
}