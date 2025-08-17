"use client";
import { useState, useEffect } from "react";
import { 
  requestDataExport, 
  getExportStatus, 
  downloadExportData, 
  formatFileSize, 
  getJobStatusColor,
  GDPRJobPoller 
} from "@/lib/gdpr";
import type { 
  GDPRDialogProps, 
  GDPRExportFormData, 
  GDPRDataExportResponse,
  GDPRError 
} from "@/types/gdpr";

interface DataExportDialogProps extends GDPRDialogProps {
  onDownloadComplete?: (response: GDPRDataExportResponse) => void;
}

export default function DataExportDialog({ 
  engagementId, 
  isOpen, 
  onClose, 
  onSuccess,
  onDownloadComplete,
  className = "" 
}: DataExportDialogProps) {
  const [formData, setFormData] = useState<GDPRExportFormData>({
    format: 'json',
    includeAssessments: true,
    includeDocuments: true,
    includeFindings: true,
    includeRecommendations: true,
    includeRunlogs: false,
    includeAuditLogs: false,
  });
  
  const [exportStatus, setExportStatus] = useState<GDPRDataExportResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>("");
  const [poller, setPoller] = useState<GDPRJobPoller | null>(null);
  const [downloadProgress, setDownloadProgress] = useState<number>(0);

  useEffect(() => {
    // Cleanup poller on unmount
    return () => {
      poller?.stop();
    };
  }, [poller]);

  useEffect(() => {
    // Reset state when dialog opens/closes
    if (!isOpen) {
      setExportStatus(null);
      setError("");
      setDownloadProgress(0);
      poller?.stop();
      setPoller(null);
    }
  }, [isOpen, poller]);

  const handleInputChange = (field: keyof GDPRExportFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");

    try {
      const request = {
        engagement_id: engagementId,
        export_format: formData.format,
        include_assessments: formData.includeAssessments,
        include_documents: formData.includeDocuments,
        include_findings: formData.includeFindings,
        include_recommendations: formData.includeRecommendations,
        include_runlogs: formData.includeRunlogs,
        include_audit_logs: formData.includeAuditLogs,
      };

      const response = await requestDataExport(request);
      setExportStatus(response);

      // Start polling for status updates
      const jobPoller = new GDPRJobPoller(response.request_id, {
        onUpdate: (status) => {
          if (status.result) {
            setExportStatus(status.result as GDPRDataExportResponse);
          }
        },
        onComplete: (status) => {
          if (status.result) {
            setExportStatus(status.result as GDPRDataExportResponse);
          }
          onSuccess?.();
        },
        onError: (error) => {
          setError(error.message);
          setPoller(null);
        }
      });

      jobPoller.start();
      setPoller(jobPoller);
    } catch (err) {
      const gdprError = err as GDPRError;
      setError(gdprError.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDownload = async () => {
    if (!exportStatus?.download_url || !exportStatus.request_id) return;

    try {
      setDownloadProgress(0);
      const blob = await downloadExportData(exportStatus.request_id);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `gdpr-export-${engagementId}-${Date.now()}.${formData.format}`;
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
      
      setDownloadProgress(100);
      onDownloadComplete?.(exportStatus);
    } catch (err) {
      const gdprError = err as GDPRError;
      setError(gdprError.message);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className={`bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto ${className}`}>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Export GDPR Data</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {!exportStatus ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Export Format */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Export Format
                </label>
                <select
                  value={formData.format}
                  onChange={(e) => handleInputChange('format', e.target.value as 'json' | 'csv' | 'pdf')}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="json">JSON - Machine readable format</option>
                  <option value="csv">CSV - Spreadsheet format</option>
                  <option value="pdf">PDF - Human readable document</option>
                </select>
              </div>

              {/* Data Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Data to Include
                </label>
                <div className="space-y-3">
                  {[
                    { key: 'includeAssessments', label: 'Assessment Data', description: 'Assessment responses and scores' },
                    { key: 'includeDocuments', label: 'Documents', description: 'Uploaded files and attachments' },
                    { key: 'includeFindings', label: 'Findings', description: 'Security findings and analysis' },
                    { key: 'includeRecommendations', label: 'Recommendations', description: 'Generated recommendations' },
                    { key: 'includeRunlogs', label: 'Run Logs', description: 'System execution logs' },
                    { key: 'includeAuditLogs', label: 'Audit Logs', description: 'User activity and access logs' },
                  ].map((item) => (
                    <label key={item.key} className="flex items-start space-x-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData[item.key as keyof GDPRExportFormData] as boolean}
                        onChange={(e) => handleInputChange(item.key as keyof GDPRExportFormData, e.target.checked)}
                        className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <div>
                        <div className="text-sm font-medium text-gray-900">{item.label}</div>
                        <div className="text-sm text-gray-500">{item.description}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Requesting...' : 'Request Export'}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-6">
              {/* Export Status */}
              <div className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-medium">Export Status</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getJobStatusColor(exportStatus.status)}`}>
                    {exportStatus.status.charAt(0).toUpperCase() + exportStatus.status.slice(1)}
                  </span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Request ID:</span>
                    <div className="font-mono text-xs break-all">{exportStatus.request_id}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">Created:</span>
                    <div>{new Date(exportStatus.created_at).toLocaleString()}</div>
                  </div>
                  {exportStatus.completed_at && (
                    <div>
                      <span className="text-gray-500">Completed:</span>
                      <div>{new Date(exportStatus.completed_at).toLocaleString()}</div>
                    </div>
                  )}
                  {exportStatus.file_size && (
                    <div>
                      <span className="text-gray-500">File Size:</span>
                      <div>{formatFileSize(exportStatus.file_size)}</div>
                    </div>
                  )}
                  {exportStatus.expires_at && (
                    <div>
                      <span className="text-gray-500">Expires:</span>
                      <div>{new Date(exportStatus.expires_at).toLocaleString()}</div>
                    </div>
                  )}
                </div>

                {exportStatus.error_message && (
                  <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded">
                    <p className="text-sm text-red-600">{exportStatus.error_message}</p>
                  </div>
                )}
              </div>

              {/* Download Section */}
              {exportStatus.status === 'completed' && exportStatus.download_url && (
                <div className="border rounded-lg p-4 bg-green-50">
                  <div className="flex items-center space-x-2 mb-3">
                    <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="text-lg font-medium text-green-800">Export Ready</h3>
                  </div>
                  <p className="text-sm text-green-700 mb-4">
                    Your data export is ready for download. The file will expire on{' '}
                    {exportStatus.expires_at ? new Date(exportStatus.expires_at).toLocaleDateString() : 'a future date'}.
                  </p>
                  <button
                    onClick={handleDownload}
                    className="w-full px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    Download Export File
                  </button>
                  
                  {downloadProgress > 0 && downloadProgress < 100 && (
                    <div className="mt-3">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-green-600 h-2 rounded-full transition-all duration-300" 
                          style={{ width: `${downloadProgress}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-gray-600 mt-1">Downloading... {downloadProgress}%</p>
                    </div>
                  )}
                </div>
              )}

              {/* Processing Status */}
              {(exportStatus.status === 'pending' || exportStatus.status === 'processing') && (
                <div className="border rounded-lg p-4 bg-blue-50">
                  <div className="flex items-center space-x-2 mb-3">
                    <svg className="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <h3 className="text-lg font-medium text-blue-800">
                      {exportStatus.status === 'pending' ? 'Export Queued' : 'Processing Export'}
                    </h3>
                  </div>
                  <p className="text-sm text-blue-700">
                    {exportStatus.status === 'pending' 
                      ? 'Your export request is queued and will begin processing shortly.'
                      : 'Your data is being exported. This may take a few minutes depending on the amount of data.'
                    }
                  </p>
                </div>
              )}

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Close
                </button>
                {exportStatus.status !== 'completed' && (
                  <button
                    onClick={() => {
                      setExportStatus(null);
                      setError("");
                      poller?.stop();
                      setPoller(null);
                    }}
                    className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    New Export
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}