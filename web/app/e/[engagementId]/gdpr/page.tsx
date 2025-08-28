"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useRequireAuth } from "../../../../components/AuthProvider";
import { isAdmin } from "../../../../lib/auth";
import GDPRDashboard from "../../../../components/gdpr/GDPRDashboard";
import DataExportDialog from "../../../../components/gdpr/DataExportDialog";
import DataPurgeDialog from "../../../../components/gdpr/DataPurgeDialog";
import AuditLogViewer from "../../../../components/gdpr/AuditLogViewer";

export default function GDPRPage() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [activeTab, setActiveTab] = useState<'overview' | 'audit-logs'>('overview');
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [showPurgeDialog, setShowPurgeDialog] = useState(false);
  
  // Require authentication
  const auth = useRequireAuth();

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
        <div className="text-red-600">No engagement selected.</div>
      </div>
    );
  }

  // Check if user has access (should be Lead/Admin)
  const hasAccess = isAdmin(); // You may want to extend this with Lead role checking
  
  if (!hasAccess) {
    return (
      <div className="p-6">
        <div className="text-red-600">
          Access denied. GDPR data management requires Lead or Admin privileges.
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">GDPR Data Management</h1>
          <p className="text-sm text-gray-600 mt-1">
            Manage data exports, purging, and compliance for engagement {engagementId}
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-500">
            User: {auth.user?.name} • Mode: {auth.mode.mode === 'aad' ? 'Azure AD' : 'Demo'}
          </div>
        </div>
      </div>

      {/* Compliance Notice */}
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start space-x-3">
          <svg className="w-6 h-6 text-blue-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 className="text-sm font-medium text-blue-800">GDPR Compliance</h3>
            <p className="text-sm text-blue-700 mt-1">
              This interface allows you to export or permanently delete personal data in compliance with GDPR Article 15 (Right of Access) 
              and Article 17 (Right to Erasure). All actions are logged for audit purposes.
            </p>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {[
            { id: 'overview', label: 'GDPR Overview' },
            { id: 'audit-logs', label: 'Audit Logs' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <GDPRDashboard
          engagementId={engagementId}
          onExportClick={() => setShowExportDialog(true)}
          onPurgeClick={() => setShowPurgeDialog(true)}
          onViewAuditLogs={() => setActiveTab('audit-logs')}
          className="max-w-6xl"
        />
      )}

      {activeTab === 'audit-logs' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium">Audit Logs</h2>
            <div className="text-sm text-gray-500">
              Showing GDPR-related activities for this engagement
            </div>
          </div>
          <AuditLogViewer
            engagementId={engagementId}
            className="max-w-6xl"
          />
        </div>
      )}

      {/* Dialogs */}
      <DataExportDialog
        engagementId={engagementId}
        isOpen={showExportDialog}
        onClose={() => setShowExportDialog(false)}
        onSuccess={() => {
          // Optionally refresh dashboard data
          console.log('Export request successful');
        }}
        onDownloadComplete={(response) => {
          console.log('Download completed:', response);
        }}
      />

      <DataPurgeDialog
        engagementId={engagementId}
        isOpen={showPurgeDialog}
        onClose={() => setShowPurgeDialog(false)}
        onSuccess={() => {
          // Optionally refresh dashboard data
          console.log('Purge request successful');
        }}
        onPurgeComplete={(response) => {
          console.log('Purge completed:', response);
          // You might want to redirect or show a success message
        }}
      />
    </div>
  );
}