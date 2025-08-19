// GDPR Components Export Index
// This file provides easy imports for all GDPR-related components

export { default as GDPRDashboard } from './GDPRDashboard';
export { default as DataExportDialog } from './DataExportDialog';
export { default as DataPurgeDialog } from './DataPurgeDialog';
export { default as AuditLogViewer } from './AuditLogViewer';

// Re-export GDPR types for convenience
export type {
  GDPRComponentProps,
  GDPRDialogProps,
  GDPRDataExportRequest,
  GDPRDataExportResponse,
  GDPRDataPurgeRequest,
  GDPRDataPurgeResponse,
  GDPRJobStatus,
  GDPRAuditLogEntry,
  GDPRAuditLogResponse,
  GDPRComplianceStatus,
  GDPRAdminDashboard,
  GDPRTTLPolicy,
  GDPRError,
  GDPRExportFormData,
  GDPRPurgeFormData
} from '@/types/gdpr';

// Re-export GDPR API functions for convenience
export {
  requestDataExport,
  getExportStatus,
  downloadExportData,
  requestDataPurge,
  getPurgeStatus,
  getJobStatus,
  getJobHistory,
  getAuditLogs,
  getComplianceStatus,
  getAdminDashboard,
  getTTLPolicy,
  updateTTLPolicy,
  getGlobalAuditLogs,
  recordConsent,
  withdrawConsent,
  formatFileSize,
  getJobStatusColor,
  getActionDisplayName,
  GDPRJobPoller
} from '@/lib/gdpr';