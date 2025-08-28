"use client";
import { useState, useEffect } from "react";
import { 
  getAuditLogs, 
  getActionDisplayName 
} from "../../lib/gdpr";
import type { 
  GDPRComponentProps, 
  GDPRAuditLogEntry, 
  GDPRAuditLogResponse,
  GDPRError 
} from "../../types/gdpr";

interface AuditLogViewerProps extends GDPRComponentProps {
  isAdminView?: boolean;
  defaultPageSize?: number;
}

export default function AuditLogViewer({ 
  engagementId, 
  className = "",
  isAdminView = false,
  defaultPageSize = 20 
}: AuditLogViewerProps) {
  const [logs, setLogs] = useState<GDPRAuditLogEntry[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(defaultPageSize);
  const [totalCount, setTotalCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrev, setHasPrev] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [selectedAction, setSelectedAction] = useState<string>("");
  const [selectedEngagement, setSelectedEngagement] = useState<string>("");
  const [expandedLog, setExpandedLog] = useState<string | null>(null);

  const actionTypes = [
    'data_export_requested',
    'data_export_completed',
    'data_purge_requested',
    'data_purge_completed',
    'data_accessed',
    'consent_given',
    'consent_withdrawn'
  ];

  useEffect(() => {
    loadAuditLogs();
  }, [engagementId, currentPage, pageSize, selectedAction, selectedEngagement]);

  const loadAuditLogs = async () => {
    setIsLoading(true);
    setError("");

    try {
      let response: GDPRAuditLogResponse;
      
      if (isAdminView) {
        // Import the global admin function when needed
        const { getGlobalAuditLogs } = await import("../../lib/gdpr");
        response = await getGlobalAuditLogs(
          currentPage, 
          pageSize, 
          selectedAction || undefined,
          selectedEngagement || undefined
        );
      } else {
        response = await getAuditLogs(
          engagementId, 
          currentPage, 
          pageSize, 
          selectedAction || undefined
        );
      }

      setLogs(response.entries);
      setTotalCount(response.total_count);
      setHasNext(response.has_next);
      setHasPrev(response.has_prev);
    } catch (err) {
      const gdprError = err as GDPRError;
      setError(gdprError.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
  };

  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize);
    setCurrentPage(1);
  };

  const handleActionFilter = (action: string) => {
    setSelectedAction(action);
    setCurrentPage(1);
  };

  const handleEngagementFilter = (engagement: string) => {
    setSelectedEngagement(engagement);
    setCurrentPage(1);
  };

  const toggleLogDetails = (logId: string) => {
    setExpandedLog(expandedLog === logId ? null : logId);
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'data_export_requested':
      case 'data_export_completed':
        return 'bg-blue-100 text-blue-800';
      case 'data_purge_requested':
      case 'data_purge_completed':
        return 'bg-red-100 text-red-800';
      case 'consent_given':
        return 'bg-green-100 text-green-800';
      case 'consent_withdrawn':
        return 'bg-yellow-100 text-yellow-800';
      case 'data_accessed':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatLogDetails = (details: Record<string, any>) => {
    if (!details || Object.keys(details).length === 0) return null;
    
    return Object.entries(details).map(([key, value]) => (
      <div key={key} className="text-xs">
        <span className="text-gray-500">{key}:</span>
        <span className="ml-1 font-mono">
          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
        </span>
      </div>
    ));
  };

  if (isLoading) {
    return (
      <div className={`space-y-4 ${className}`}>
        <div className="animate-pulse space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center justify-between">
        <div className="flex flex-wrap gap-4">
          {/* Action Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Action Type</label>
            <select
              value={selectedAction}
              onChange={(e) => handleActionFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Actions</option>
              {actionTypes.map((action) => (
                <option key={action} value={action}>
                  {getActionDisplayName(action)}
                </option>
              ))}
            </select>
          </div>

          {/* Engagement Filter (Admin View Only) */}
          {isAdminView && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Engagement ID</label>
              <input
                type="text"
                value={selectedEngagement}
                onChange={(e) => handleEngagementFilter(e.target.value)}
                placeholder="Filter by engagement"
                className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}

          {/* Page Size */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Per Page</label>
            <select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>

        {/* Refresh Button */}
        <button
          onClick={loadAuditLogs}
          className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 border"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Results Summary */}
      <div className="text-sm text-gray-600">
        Showing {logs.length} of {totalCount.toLocaleString()} audit log entries
        {(selectedAction || selectedEngagement) && (
          <span className="ml-2">
            (filtered)
            <button
              onClick={() => {
                setSelectedAction("");
                setSelectedEngagement("");
                setCurrentPage(1);
              }}
              className="ml-1 text-blue-600 hover:text-blue-800 underline"
            >
              Clear filters
            </button>
          </span>
        )}
      </div>

      {/* Audit Logs */}
      {logs.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No audit log entries found.
        </div>
      ) : (
        <div className="space-y-2">
          {logs.map((log) => (
            <div key={log.id} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getActionColor(log.action)}`}>
                      {getActionDisplayName(log.action)}
                    </span>
                    <span className="text-sm font-medium">{log.user_email}</span>
                    <span className="text-sm text-gray-500">
                      {new Date(log.timestamp).toLocaleString()}
                    </span>
                  </div>
                  
                  {isAdminView && (
                    <div className="text-sm text-gray-600 mb-2">
                      <span className="font-medium">Engagement:</span> 
                      <span className="ml-1 font-mono text-xs">{log.engagement_id}</span>
                    </div>
                  )}

                  {log.ip_address && (
                    <div className="text-xs text-gray-500">
                      IP: {log.ip_address}
                    </div>
                  )}
                </div>

                {/* Expand Button */}
                {(Object.keys(log.details).length > 0 || log.user_agent) && (
                  <button
                    onClick={() => toggleLogDetails(log.id)}
                    className="ml-4 p-1 text-gray-400 hover:text-gray-600"
                  >
                    <svg 
                      className={`w-4 h-4 transition-transform ${expandedLog === log.id ? 'rotate-180' : ''}`}
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                )}
              </div>

              {/* Expanded Details */}
              {expandedLog === log.id && (
                <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
                  {log.user_agent && (
                    <div className="text-xs">
                      <span className="text-gray-500">User Agent:</span>
                      <div className="mt-1 font-mono text-xs break-all bg-gray-50 p-2 rounded">
                        {log.user_agent}
                      </div>
                    </div>
                  )}
                  
                  {Object.keys(log.details).length > 0 && (
                    <div className="text-xs">
                      <span className="text-gray-500">Details:</span>
                      <div className="mt-1 bg-gray-50 p-2 rounded space-y-1">
                        {formatLogDetails(log.details)}
                      </div>
                    </div>
                  )}
                  
                  <div className="text-xs text-gray-400">
                    Log ID: {log.id}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {(hasNext || hasPrev) && (
        <div className="flex items-center justify-between border-t pt-4">
          <div className="text-sm text-gray-600">
            Page {currentPage} of {Math.ceil(totalCount / pageSize)}
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={!hasPrev}
              className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={!hasNext}
              className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}