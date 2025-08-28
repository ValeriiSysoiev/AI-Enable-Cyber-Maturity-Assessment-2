"use client";
import { useState, useEffect } from "react";
import { 
  getComplianceStatus, 
  getJobHistory, 
  formatFileSize, 
  getJobStatusColor,
  getActionDisplayName 
} from "../../lib/gdpr";
import type { 
  GDPRComponentProps, 
  GDPRComplianceStatus, 
  GDPRJobStatus,
  GDPRError 
} from "../../types/gdpr";

interface GDPRDashboardProps extends GDPRComponentProps {
  onExportClick?: () => void;
  onPurgeClick?: () => void;
  onViewAuditLogs?: () => void;
}

export default function GDPRDashboard({ 
  engagementId, 
  className = "",
  onExportClick,
  onPurgeClick,
  onViewAuditLogs 
}: GDPRDashboardProps) {
  const [complianceStatus, setComplianceStatus] = useState<GDPRComplianceStatus | null>(null);
  const [jobHistory, setJobHistory] = useState<GDPRJobStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    loadDashboardData();
  }, [engagementId]);

  const loadDashboardData = async () => {
    setIsLoading(true);
    setError("");

    try {
      const [compliance, jobs] = await Promise.all([
        getComplianceStatus(engagementId),
        getJobHistory(engagementId)
      ]);

      setComplianceStatus(compliance);
      setJobHistory(jobs.slice(0, 10)); // Show last 10 jobs
    } catch (err) {
      const gdprError = err as GDPRError;
      setError(gdprError.message);
    } finally {
      setIsLoading(false);
    }
  };

  const getConsentStatusColor = (status: string) => {
    switch (status) {
      case 'given':
        return 'bg-green-100 text-green-800';
      case 'withdrawn':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getRetentionStatusColor = (daysUntilPurge: number) => {
    if (daysUntilPurge < 7) return 'bg-red-100 text-red-800';
    if (daysUntilPurge < 30) return 'bg-yellow-100 text-yellow-800';
    return 'bg-green-100 text-green-800';
  };

  const calculateDaysUntilPurge = () => {
    if (!complianceStatus?.data_retention_policy.next_purge_date) return null;
    const purgeDate = new Date(complianceStatus.data_retention_policy.next_purge_date);
    const now = new Date();
    const diffTime = purgeDate.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  if (isLoading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
          <button
            onClick={loadDashboardData}
            className="mt-2 text-sm text-red-600 underline hover:text-red-800"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!complianceStatus) return null;

  const daysUntilPurge = calculateDaysUntilPurge();

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <button
          onClick={onExportClick}
          className="p-4 text-left border rounded-lg hover:bg-blue-50 hover:border-blue-200 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <div className="font-medium">Export Data</div>
              <div className="text-sm text-gray-500">Download your data</div>
            </div>
          </div>
        </button>

        <button
          onClick={onPurgeClick}
          className="p-4 text-left border rounded-lg hover:bg-red-50 hover:border-red-200 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-red-100 rounded">
              <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </div>
            <div>
              <div className="font-medium">Purge Data</div>
              <div className="text-sm text-gray-500">Permanently delete data</div>
            </div>
          </div>
        </button>

        <button
          onClick={onViewAuditLogs}
          className="p-4 text-left border rounded-lg hover:bg-gray-50 hover:border-gray-300 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-gray-100 rounded">
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <div className="font-medium">Audit Logs</div>
              <div className="text-sm text-gray-500">View activity history</div>
            </div>
          </div>
        </button>
      </div>

      {/* Compliance Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Data Summary */}
        <div className="border rounded-lg p-4">
          <h3 className="text-lg font-medium mb-4">Data Summary</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Total Data Points</span>
              <span className="font-medium">{complianceStatus.data_summary.total_data_points.toLocaleString()}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Estimated Size</span>
              <span className="font-medium">{formatFileSize(complianceStatus.data_summary.estimated_size_bytes)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Oldest Data</span>
              <span className="font-medium">{new Date(complianceStatus.data_summary.oldest_data_date).toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Latest Data</span>
              <span className="font-medium">{new Date(complianceStatus.data_summary.latest_data_date).toLocaleDateString()}</span>
            </div>
          </div>
        </div>

        {/* Retention Policy */}
        <div className="border rounded-lg p-4">
          <h3 className="text-lg font-medium mb-4">Data Retention</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Retention Period</span>
              <span className="font-medium">{complianceStatus.data_retention_policy.retention_days} days</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Auto Purge</span>
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                complianceStatus.data_retention_policy.auto_purge_enabled 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {complianceStatus.data_retention_policy.auto_purge_enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            {daysUntilPurge !== null && (
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Next Auto Purge</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${getRetentionStatusColor(daysUntilPurge)}`}>
                  {daysUntilPurge > 0 ? `${daysUntilPurge} days` : 'Overdue'}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Consent Status */}
      <div className="border rounded-lg p-4">
        <h3 className="text-lg font-medium mb-4">Consent Status</h3>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">Current Status:</span>
              <span className={`px-2 py-1 rounded text-xs font-medium ${getConsentStatusColor(complianceStatus.consent_status.current_status)}`}>
                {complianceStatus.consent_status.current_status.charAt(0).toUpperCase() + complianceStatus.consent_status.current_status.slice(1)}
              </span>
            </div>
            {complianceStatus.consent_status.given_at && (
              <div className="text-sm text-gray-500 mt-1">
                Given: {new Date(complianceStatus.consent_status.given_at).toLocaleString()}
              </div>
            )}
            {complianceStatus.consent_status.withdrawn_at && (
              <div className="text-sm text-gray-500 mt-1">
                Withdrawn: {new Date(complianceStatus.consent_status.withdrawn_at).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Activity Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Export History */}
        <div className="border rounded-lg p-4">
          <h3 className="text-lg font-medium mb-4">Export Activity</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Total Exports</span>
              <span className="font-medium">{complianceStatus.export_history.total_exports}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Pending Exports</span>
              <span className="font-medium">{complianceStatus.export_history.pending_exports}</span>
            </div>
            {complianceStatus.export_history.last_export_date && (
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Last Export</span>
                <span className="font-medium">{new Date(complianceStatus.export_history.last_export_date).toLocaleDateString()}</span>
              </div>
            )}
          </div>
        </div>

        {/* Purge History */}
        <div className="border rounded-lg p-4">
          <h3 className="text-lg font-medium mb-4">Purge Activity</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Total Purges</span>
              <span className="font-medium">{complianceStatus.purge_history.total_purges}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Pending Purges</span>
              <span className="font-medium">{complianceStatus.purge_history.pending_purges}</span>
            </div>
            {complianceStatus.purge_history.last_purge_date && (
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Last Purge</span>
                <span className="font-medium">{new Date(complianceStatus.purge_history.last_purge_date).toLocaleDateString()}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Jobs */}
      {jobHistory.length > 0 && (
        <div className="border rounded-lg p-4">
          <h3 className="text-lg font-medium mb-4">Recent GDPR Activities</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Type</th>
                  <th className="text-left py-2">Status</th>
                  <th className="text-left py-2">Created</th>
                  <th className="text-left py-2">Completed</th>
                  <th className="text-left py-2">Progress</th>
                </tr>
              </thead>
              <tbody>
                {jobHistory.map((job) => (
                  <tr key={job.job_id} className="border-t">
                    <td className="py-2">
                      <span className="capitalize">{job.job_type}</span>
                    </td>
                    <td className="py-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getJobStatusColor(job.status)}`}>
                        {job.status}
                      </span>
                    </td>
                    <td className="py-2">{new Date(job.created_at).toLocaleDateString()}</td>
                    <td className="py-2">
                      {job.completed_at ? new Date(job.completed_at).toLocaleDateString() : '-'}
                    </td>
                    <td className="py-2">
                      {job.progress_percentage !== undefined ? `${job.progress_percentage}%` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}