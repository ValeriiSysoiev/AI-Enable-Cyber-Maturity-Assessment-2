// GDPR data export request and response types
export interface GDPRDataExportRequest {
  engagement_id: string;
  export_format: 'json' | 'csv' | 'pdf';
  include_assessments?: boolean;
  include_documents?: boolean;
  include_findings?: boolean;
  include_recommendations?: boolean;
  include_runlogs?: boolean;
  include_audit_logs?: boolean;
}

export interface GDPRDataExportResponse {
  request_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  download_url?: string;
  file_size?: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
  expires_at?: string;
}

// GDPR data purge request and response types
export interface GDPRDataPurgeRequest {
  engagement_id: string;
  purge_assessments?: boolean;
  purge_documents?: boolean;
  purge_findings?: boolean;
  purge_recommendations?: boolean;
  purge_runlogs?: boolean;
  purge_audit_logs?: boolean;
  confirmation_token: string;
}

export interface GDPRDataPurgeResponse {
  request_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  items_purged?: {
    assessments: number;
    documents: number;
    findings: number;
    recommendations: number;
    runlogs: number;
    audit_logs: number;
  };
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

// GDPR job status and monitoring types
export interface GDPRJobStatus {
  job_id: string;
  job_type: 'export' | 'purge';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  engagement_id: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  progress_percentage?: number;
  current_step?: string;
  error_message?: string;
  result?: GDPRDataExportResponse | GDPRDataPurgeResponse;
}

// GDPR audit log types
export interface GDPRAuditLogEntry {
  id: string;
  timestamp: string;
  engagement_id: string;
  user_email: string;
  action: 'data_export_requested' | 'data_export_completed' | 'data_purge_requested' | 'data_purge_completed' | 'data_accessed' | 'consent_given' | 'consent_withdrawn';
  details: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
}

export interface GDPRAuditLogResponse {
  entries: GDPRAuditLogEntry[];
  total_count: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}

// GDPR compliance status types
export interface GDPRComplianceStatus {
  engagement_id: string;
  data_retention_policy: {
    retention_days: number;
    auto_purge_enabled: boolean;
    next_purge_date?: string;
  };
  consent_status: {
    given_at?: string;
    withdrawn_at?: string;
    current_status: 'given' | 'withdrawn' | 'pending';
  };
  data_summary: {
    total_data_points: number;
    oldest_data_date: string;
    latest_data_date: string;
    estimated_size_bytes: number;
  };
  export_history: {
    total_exports: number;
    last_export_date?: string;
    pending_exports: number;
  };
  purge_history: {
    total_purges: number;
    last_purge_date?: string;
    pending_purges: number;
  };
}

// GDPR dashboard admin view types
export interface GDPRAdminDashboard {
  total_engagements: number;
  engagements_with_data: number;
  pending_export_requests: number;
  pending_purge_requests: number;
  failed_jobs_last_24h: number;
  total_data_size_bytes: number;
  oldest_data_date: string;
  recent_jobs: GDPRJobStatus[];
  compliance_alerts: GDPRComplianceAlert[];
}

export interface GDPRComplianceAlert {
  id: string;
  type: 'retention_violation' | 'failed_export' | 'failed_purge' | 'consent_expired';
  severity: 'low' | 'medium' | 'high' | 'critical';
  engagement_id: string;
  message: string;
  created_at: string;
  resolved_at?: string;
}

// GDPR settings and configuration types
export interface GDPRTTLPolicy {
  engagement_data_retention_days: number;
  assessment_data_retention_days: number;
  document_retention_days: number;
  audit_log_retention_days: number;
  auto_purge_enabled: boolean;
  notification_before_purge_days: number;
}

// Component prop types
export interface GDPRComponentProps {
  engagementId: string;
  className?: string;
}

export interface GDPRDialogProps extends GDPRComponentProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

// Form validation types
export interface GDPRExportFormData {
  format: 'json' | 'csv' | 'pdf';
  includeAssessments: boolean;
  includeDocuments: boolean;
  includeFindings: boolean;
  includeRecommendations: boolean;
  includeRunlogs: boolean;
  includeAuditLogs: boolean;
}

export interface GDPRPurgeFormData {
  purgeAssessments: boolean;
  purgeDocuments: boolean;
  purgeFindings: boolean;
  purgeRecommendations: boolean;
  purgeRunlogs: boolean;
  purgeAuditLogs: boolean;
  confirmationText: string;
}

// Error types specific to GDPR operations
export interface GDPRError {
  code: 'INSUFFICIENT_PERMISSIONS' | 'INVALID_ENGAGEMENT' | 'EXPORT_LIMIT_EXCEEDED' | 'PURGE_IN_PROGRESS' | 'INVALID_FORMAT' | 'NETWORK_ERROR' | 'UNKNOWN_ERROR';
  message: string;
  details?: Record<string, any>;
}