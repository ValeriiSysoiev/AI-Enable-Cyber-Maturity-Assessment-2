"use client";
import { useState, useEffect } from "react";
import { useRequireAuth } from "../../../components/AuthProvider";
import { isAdmin } from "../../../lib/auth";
import { 
  getAdminDashboard, 
  getTTLPolicy, 
  updateTTLPolicy,
  formatFileSize,
  getJobStatusColor 
} from "../../../lib/gdpr";
import AuditLogViewer from "../../../components/gdpr/AuditLogViewer";
import type { 
  GDPRAdminDashboard, 
  GDPRTTLPolicy,
  GDPRError 
} from "../../../types/gdpr";

export default function AdminGDPRPage() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'ttl-policy' | 'audit-logs' | 'jobs'>('dashboard');
  const [adminDashboard, setAdminDashboard] = useState<GDPRAdminDashboard | null>(null);
  const [ttlPolicy, setTTLPolicy] = useState<GDPRTTLPolicy | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [isSavingPolicy, setIsSavingPolicy] = useState(false);
  const [policyMessage, setPolicyMessage] = useState<string>("");
  const [isAdminUser, setIsAdminUser] = useState(false);
  const [adminCheckLoading, setAdminCheckLoading] = useState(true);
  
  // Require authentication and admin access
  const auth = useRequireAuth();

  useEffect(() => {
    if (auth.isAuthenticated && auth.user?.email) {
      checkAdminStatus();
    }
  }, [auth.isAuthenticated, auth.user?.email]);

  useEffect(() => {
    if (auth.isAuthenticated && isAdminUser) {
      loadAdminData();
    }
  }, [auth.isAuthenticated, isAdminUser]);

  async function checkAdminStatus() {
    try {
      const headers: Record<string, string> = {};
      if (auth.user?.email) {
        headers['X-User-Email'] = auth.user.email;
      }
      
      const response = await fetch('/api/admin/auth-diagnostics', { headers });
      setIsAdminUser(response.ok);
    } catch {
      setIsAdminUser(false);
    } finally {
      setAdminCheckLoading(false);
    }
  }

  const loadAdminData = async () => {
    setIsLoading(true);
    setError("");

    try {
      const [dashboard, policy] = await Promise.all([
        getAdminDashboard(),
        getTTLPolicy()
      ]);

      setAdminDashboard(dashboard);
      setTTLPolicy(policy);
    } catch (err) {
      const gdprError = err as GDPRError;
      setError(gdprError.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePolicyUpdate = async (field: keyof GDPRTTLPolicy, value: any) => {
    if (!ttlPolicy) return;

    const updatedPolicy = { ...ttlPolicy, [field]: value };
    setTTLPolicy(updatedPolicy);

    setIsSavingPolicy(true);
    setPolicyMessage("");

    try {
      const savedPolicy = await updateTTLPolicy({ [field]: value });
      setTTLPolicy(savedPolicy);
      setPolicyMessage("Policy updated successfully");
      setTimeout(() => setPolicyMessage(""), 3000);
    } catch (err) {
      const gdprError = err as GDPRError;
      setPolicyMessage(`Error: ${gdprError.message}`);
    } finally {
      setIsSavingPolicy(false);
    }
  };

  const getAlertColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (auth.isLoading || adminCheckLoading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading...</div>
      </div>
    );
  }

  if (!isAdminUser) {
    return (
      <div className="p-6">
        <div className="text-red-600">Access denied. Admin privileges required.</div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">GDPR Administration</h1>
          <p className="text-sm text-gray-600 mt-1">
            Global GDPR compliance management and monitoring
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <a 
            href="/admin/ops" 
            className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 border"
          >
            Admin Operations
          </a>
          <button
            onClick={loadAdminData}
            className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 border"
          >
            Refresh
          </button>
          <div className="text-sm text-gray-500">
            User: {auth.user?.name} • Mode: {auth.mode.mode === 'aad' ? 'Azure AD' : 'Demo'}
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {[
            { id: 'dashboard', label: 'Overview' },
            { id: 'jobs', label: 'Background Jobs' },
            { id: 'ttl-policy', label: 'TTL Policy' },
            { id: 'audit-logs', label: 'Global Audit Logs' },
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
      {activeTab === 'dashboard' && adminDashboard && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500">Total Engagements</div>
              <div className="text-2xl font-semibold">{adminDashboard.total_engagements}</div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500">With Data</div>
              <div className="text-2xl font-semibold">{adminDashboard.engagements_with_data}</div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500">Pending Exports</div>
              <div className="text-2xl font-semibold">{adminDashboard.pending_export_requests}</div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500">Pending Purges</div>
              <div className="text-2xl font-semibold">{adminDashboard.pending_purge_requests}</div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500">Failed Jobs (24h)</div>
              <div className="text-2xl font-semibold text-red-600">{adminDashboard.failed_jobs_last_24h}</div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-gray-500">Total Data Size</div>
              <div className="text-lg font-semibold">{formatFileSize(adminDashboard.total_data_size_bytes)}</div>
            </div>
          </div>

          {/* Compliance Alerts */}
          {adminDashboard.compliance_alerts.length > 0 && (
            <div className="border rounded-lg p-4">
              <h3 className="text-lg font-medium mb-4">Compliance Alerts</h3>
              <div className="space-y-3">
                {adminDashboard.compliance_alerts.map((alert) => (
                  <div key={alert.id} className={`p-3 border rounded ${getAlertColor(alert.severity)}`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-medium">{alert.message}</div>
                        <div className="text-sm opacity-75 mt-1">
                          Engagement: {alert.engagement_id} • {new Date(alert.created_at).toLocaleString()}
                        </div>
                      </div>
                      <span className="px-2 py-1 rounded text-xs font-medium bg-white bg-opacity-50">
                        {alert.severity}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Data Retention Overview */}
          <div className="border rounded-lg p-4">
            <h3 className="text-lg font-medium mb-4">Data Retention Overview</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-600">Oldest Data Date</div>
                <div className="font-medium">{new Date(adminDashboard.oldest_data_date).toLocaleDateString()}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Days Since Oldest</div>
                <div className="font-medium">
                  {Math.floor((Date.now() - new Date(adminDashboard.oldest_data_date).getTime()) / (1000 * 60 * 60 * 24))} days
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'jobs' && adminDashboard && (
        <div className="space-y-6">
          <h2 className="text-lg font-medium">Recent Background Jobs</h2>
          {adminDashboard.recent_jobs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No recent jobs found.</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left py-3 px-4">Job ID</th>
                    <th className="text-left py-3 px-4">Type</th>
                    <th className="text-left py-3 px-4">Status</th>
                    <th className="text-left py-3 px-4">Engagement</th>
                    <th className="text-left py-3 px-4">Created</th>
                    <th className="text-left py-3 px-4">Progress</th>
                    <th className="text-left py-3 px-4">Current Step</th>
                  </tr>
                </thead>
                <tbody>
                  {adminDashboard.recent_jobs.map((job) => (
                    <tr key={job.job_id} className="border-t">
                      <td className="py-3 px-4 font-mono text-xs">{job.job_id.substring(0, 8)}...</td>
                      <td className="py-3 px-4 capitalize">{job.job_type}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getJobStatusColor(job.status)}`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-xs">{job.engagement_id.substring(0, 8)}...</td>
                      <td className="py-3 px-4">{new Date(job.created_at).toLocaleDateString()}</td>
                      <td className="py-3 px-4">
                        {job.progress_percentage !== undefined ? `${job.progress_percentage}%` : '-'}
                      </td>
                      <td className="py-3 px-4 text-xs">{job.current_step || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'ttl-policy' && ttlPolicy && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium">Data Retention (TTL) Policy</h2>
            {policyMessage && (
              <div className={`text-sm px-3 py-1 rounded ${
                policyMessage.startsWith('Error') ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'
              }`}>
                {policyMessage}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Retention Periods */}
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-4">Retention Periods (Days)</h3>
              <div className="space-y-4">
                {[
                  { key: 'engagement_data_retention_days', label: 'Engagement Data' },
                  { key: 'assessment_data_retention_days', label: 'Assessment Data' },
                  { key: 'document_retention_days', label: 'Document Data' },
                  { key: 'audit_log_retention_days', label: 'Audit Logs' },
                ].map((field) => (
                  <div key={field.key}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {field.label}
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="3650"
                      value={ttlPolicy[field.key as keyof GDPRTTLPolicy] as number}
                      onChange={(e) => handlePolicyUpdate(field.key as keyof GDPRTTLPolicy, parseInt(e.target.value))}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      disabled={isSavingPolicy}
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Auto-Purge Settings */}
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-4">Auto-Purge Settings</h3>
              <div className="space-y-4">
                <div>
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={ttlPolicy.auto_purge_enabled}
                      onChange={(e) => handlePolicyUpdate('auto_purge_enabled', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      disabled={isSavingPolicy}
                    />
                    <span className="text-sm font-medium">Enable Auto-Purge</span>
                  </label>
                  <p className="text-xs text-gray-500 mt-1">
                    Automatically purge data when retention period expires
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Notification Before Purge (Days)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="90"
                    value={ttlPolicy.notification_before_purge_days}
                    onChange={(e) => handlePolicyUpdate('notification_before_purge_days', parseInt(e.target.value))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={isSavingPolicy || !ttlPolicy.auto_purge_enabled}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Notify users this many days before auto-purge
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Policy Information */}
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="font-medium text-blue-800 mb-2">Policy Information</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• Retention periods are enforced globally across all engagements</li>
              <li>• Changes take effect immediately for new data</li>
              <li>• Existing data follows the retention period from its creation date</li>
              <li>• Auto-purge runs daily and cannot be reversed</li>
              <li>• Users will receive notifications before auto-purge if enabled</li>
            </ul>
          </div>
        </div>
      )}

      {activeTab === 'audit-logs' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium">Global Audit Logs</h2>
            <div className="text-sm text-gray-500">
              Showing GDPR-related activities across all engagements
            </div>
          </div>
          <AuditLogViewer
            engagementId="" // Empty for admin view
            isAdminView={true}
            defaultPageSize={50}
            className="max-w-7xl"
          />
        </div>
      )}
    </div>
  );
}