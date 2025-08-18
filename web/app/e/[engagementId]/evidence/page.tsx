"use client";
import { useState, useCallback } from "react";
import { useParams } from "next/navigation";
import EvidenceUploader from "@/components/EvidenceUploader";
import EvidenceTable from "@/components/EvidenceTable";
import EvidencePreview from "@/components/EvidencePreview";
import { useRequireAuth } from "@/components/AuthProvider";
import type { Evidence } from "@/types/evidence";

export default function EvidenceManagementPage() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [activeView, setActiveView] = useState<'upload' | 'table' | 'preview'>('table');
  
  // Require authentication
  const auth = useRequireAuth();

  const handleUploadComplete = useCallback((evidence: Evidence) => {
    // Refresh the table and show the uploaded evidence
    setRefreshTrigger(prev => prev + 1);
    setSelectedEvidence(evidence);
    setActiveView('preview');
  }, []);

  const handleEvidenceSelect = useCallback((evidence: Evidence) => {
    setSelectedEvidence(evidence);
    setActiveView('preview');
  }, []);

  const handleLinked = useCallback(() => {
    // Refresh the table to show updated links
    setRefreshTrigger(prev => prev + 1);
  }, []);

  const closePreview = useCallback(() => {
    setSelectedEvidence(null);
    setActiveView('table');
  }, []);

  if (auth.isLoading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading...</div>
      </div>
    );
  }

  if (!engagementId) {
    return (
      <div className="p-6">
        <div className="text-center text-red-600">No engagement selected.</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Evidence Management</h1>
          <p className="text-gray-600 mt-1">
            Upload, organize, and link evidence files for this engagement
          </p>
        </div>
        
        {/* View Toggle */}
        <div className="flex items-center gap-2 border rounded-lg p-1">
          <button
            onClick={() => setActiveView('upload')}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              activeView === 'upload'
                ? 'bg-blue-600 text-white'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Upload
          </button>
          <button
            onClick={() => setActiveView('table')}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              activeView === 'table'
                ? 'bg-blue-600 text-white'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Browse
          </button>
          <button
            onClick={() => setActiveView('preview')}
            disabled={!selectedEvidence}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              activeView === 'preview'
                ? 'bg-blue-600 text-white'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Preview
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Primary Panel */}
        <div className="lg:col-span-2">
          {activeView === 'upload' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-medium mb-4">Upload Evidence</h2>
                <EvidenceUploader
                  onUploadComplete={handleUploadComplete}
                  className="max-w-2xl"
                />
              </div>
              
              {/* Recent Uploads Quick View */}
              <div>
                <h3 className="text-md font-medium mb-4">Recent Uploads</h3>
                <EvidenceTable
                  onEvidenceSelect={handleEvidenceSelect}
                  refreshTrigger={refreshTrigger}
                  className="max-h-96 overflow-y-auto"
                />
              </div>
            </div>
          )}

          {activeView === 'table' && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-medium">Evidence Files</h2>
                <button
                  onClick={() => setActiveView('upload')}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Upload New File
                </button>
              </div>
              <EvidenceTable
                onEvidenceSelect={handleEvidenceSelect}
                refreshTrigger={refreshTrigger}
              />
            </div>
          )}

          {activeView === 'preview' && (
            <div>
              <EvidencePreview
                evidence={selectedEvidence}
                onClose={closePreview}
                onLinked={handleLinked}
              />
            </div>
          )}
        </div>

        {/* Side Panel */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-medium mb-3">Quick Actions</h3>
            <div className="space-y-2">
              <button
                onClick={() => setActiveView('upload')}
                className="w-full px-3 py-2 text-left text-sm bg-white border rounded hover:bg-gray-50"
              >
                📤 Upload Evidence
              </button>
              <button
                onClick={() => setActiveView('table')}
                className="w-full px-3 py-2 text-left text-sm bg-white border rounded hover:bg-gray-50"
              >
                📋 Browse All Files
              </button>
              <button
                onClick={() => {
                  if (selectedEvidence) {
                    navigator.clipboard.writeText(selectedEvidence.checksum_sha256);
                    alert('Checksum copied to clipboard');
                  }
                }}
                disabled={!selectedEvidence}
                className="w-full px-3 py-2 text-left text-sm bg-white border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                📋 Copy Checksum
              </button>
            </div>
          </div>

          {/* Current Selection Info */}
          {selectedEvidence && (
            <div className="bg-blue-50 rounded-lg p-4">
              <h3 className="font-medium mb-2 text-blue-900">Selected File</h3>
              <div className="text-sm space-y-1 text-blue-800">
                <div className="font-medium truncate">{selectedEvidence.filename}</div>
                <div>Size: {(selectedEvidence.size / 1024 / 1024).toFixed(1)} MB</div>
                <div>Links: {selectedEvidence.linked_items.length}</div>
                {selectedEvidence.pii_flag && (
                  <div className="text-orange-700">⚠️ Contains PII</div>
                )}
              </div>
              <button
                onClick={() => setActiveView('preview')}
                className="mt-3 w-full px-3 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
              >
                View Details
              </button>
            </div>
          )}

          {/* Help & Guidelines */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-medium mb-3">Guidelines</h3>
            <div className="text-sm text-gray-600 space-y-2">
              <div>• Maximum file size: 25 MB</div>
              <div>• Supported formats: PDF, DOCX, XLSX, PPTX, TXT, CSV, Images, ZIP</div>
              <div>• Files are automatically scanned for PII</div>
              <div>• Use links to connect evidence to assessments</div>
              <div>• All uploads are audit logged</div>
            </div>
          </div>

          {/* Stats Summary */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-medium mb-3">Summary</h3>
            <div className="text-sm text-gray-600 space-y-1">
              <div>📁 Files: Loading...</div>
              <div>🔗 Links: Loading...</div>
              <div>⚠️ PII Files: Loading...</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}