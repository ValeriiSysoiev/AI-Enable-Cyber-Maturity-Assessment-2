import { apiFetch } from "./api";
import type {
  GDPRDataExportRequest,
  GDPRDataExportResponse,
  GDPRDataPurgeRequest,
  GDPRDataPurgeResponse,
  GDPRJobStatus,
  GDPRAuditLogResponse,
  GDPRComplianceStatus,
  GDPRAdminDashboard,
  GDPRTTLPolicy,
  GDPRError,
} from "@/types/gdpr";

// GDPR Data Export Operations
export async function requestDataExport(request: GDPRDataExportRequest): Promise<GDPRDataExportResponse> {
  try {
    return await apiFetch("/gdpr/export", {
      method: "POST",
      body: JSON.stringify(request),
    });
  } catch (error) {
    throw transformGDPRError(error);
  }
}

export async function getExportStatus(requestId: string): Promise<GDPRDataExportResponse> {
  try {
    return await apiFetch(`/gdpr/export/${requestId}`);
  } catch (error) {
    throw transformGDPRError(error);
  }
}

export async function downloadExportData(requestId: string): Promise<Blob> {
  try {
    // Use direct fetch for file download
    const response = await fetch(`/api/proxy/gdpr/export/${requestId}/download`, {
      headers: {
        "Content-Type": "application/octet-stream",
      },
    });
    
    if (!response.ok) {
      throw new Error(`Download failed: ${response.status}`);
    }
    
    return await response.blob();
  } catch (error) {
    throw transformGDPRError(error);
  }
}

// GDPR Data Purge Operations
export async function requestDataPurge(request: GDPRDataPurgeRequest): Promise<GDPRDataPurgeResponse> {
  try {
    return await apiFetch("/gdpr/purge", {
      method: "POST",
      body: JSON.stringify(request),
    });
  } catch (error) {
    throw transformGDPRError(error);
  }
}

export async function getPurgeStatus(requestId: string): Promise<GDPRDataPurgeResponse> {
  try {
    return await apiFetch(`/gdpr/purge/${requestId}`);
  } catch (error) {
    throw transformGDPRError(error);
  }
}

// GDPR Job Status and Monitoring
export async function getJobStatus(jobId: string): Promise<GDPRJobStatus> {
  try {
    return await apiFetch(`/gdpr/jobs/${jobId}`);
  } catch (error) {
    throw transformGDPRError(error);
  }
}

export async function getJobHistory(engagementId: string, jobType?: 'export' | 'purge'): Promise<GDPRJobStatus[]> {
  try {
    const params = new URLSearchParams();
    if (jobType) params.set('type', jobType);
    
    const url = `/gdpr/jobs?engagement_id=${engagementId}${params.toString() ? '&' + params.toString() : ''}`;
    return await apiFetch(url);
  } catch (error) {
    throw transformGDPRError(error);
  }
}

// GDPR Audit Logs
export async function getAuditLogs(
  engagementId: string,
  page: number = 1,
  pageSize: number = 50,
  action?: string
): Promise<GDPRAuditLogResponse> {
  try {
    const params = new URLSearchParams({
      engagement_id: engagementId,
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    
    if (action) params.set('action', action);
    
    return await apiFetch(`/gdpr/audit-logs?${params.toString()}`);
  } catch (error) {
    throw transformGDPRError(error);
  }
}

// GDPR Compliance Status
export async function getComplianceStatus(engagementId: string): Promise<GDPRComplianceStatus> {
  try {
    return await apiFetch(`/gdpr/compliance/${engagementId}`);
  } catch (error) {
    throw transformGDPRError(error);
  }
}

// Admin Operations
export async function getAdminDashboard(): Promise<GDPRAdminDashboard> {
  try {
    return await apiFetch("/gdpr/admin/dashboard");
  } catch (error) {
    throw transformGDPRError(error);
  }
}

export async function getTTLPolicy(): Promise<GDPRTTLPolicy> {
  try {
    return await apiFetch("/gdpr/admin/ttl-policy");
  } catch (error) {
    throw transformGDPRError(error);
  }
}

export async function updateTTLPolicy(policy: Partial<GDPRTTLPolicy>): Promise<GDPRTTLPolicy> {
  try {
    return await apiFetch("/gdpr/admin/ttl-policy", {
      method: "PUT",
      body: JSON.stringify(policy),
    });
  } catch (error) {
    throw transformGDPRError(error);
  }
}

export async function getGlobalAuditLogs(
  page: number = 1,
  pageSize: number = 50,
  action?: string,
  engagementId?: string
): Promise<GDPRAuditLogResponse> {
  try {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    
    if (action) params.set('action', action);
    if (engagementId) params.set('engagement_id', engagementId);
    
    return await apiFetch(`/gdpr/admin/audit-logs?${params.toString()}`);
  } catch (error) {
    throw transformGDPRError(error);
  }
}

// Consent Management
export async function recordConsent(engagementId: string): Promise<void> {
  try {
    await apiFetch("/gdpr/consent", {
      method: "POST",
      body: JSON.stringify({ engagement_id: engagementId }),
    });
  } catch (error) {
    throw transformGDPRError(error);
  }
}

export async function withdrawConsent(engagementId: string): Promise<void> {
  try {
    await apiFetch("/gdpr/consent", {
      method: "DELETE",
      body: JSON.stringify({ engagement_id: engagementId }),
    });
  } catch (error) {
    throw transformGDPRError(error);
  }
}

// Utility Functions
export function generateConfirmationToken(): string {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}

export function validateConfirmationText(input: string, expected: string): boolean {
  return input.trim().toLowerCase() === expected.trim().toLowerCase();
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function getJobStatusColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800';
    case 'processing':
      return 'bg-blue-100 text-blue-800';
    case 'pending':
      return 'bg-yellow-100 text-yellow-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

export function getActionDisplayName(action: string): string {
  switch (action) {
    case 'data_export_requested':
      return 'Data Export Requested';
    case 'data_export_completed':
      return 'Data Export Completed';
    case 'data_purge_requested':
      return 'Data Purge Requested';
    case 'data_purge_completed':
      return 'Data Purge Completed';
    case 'data_accessed':
      return 'Data Accessed';
    case 'consent_given':
      return 'Consent Given';
    case 'consent_withdrawn':
      return 'Consent Withdrawn';
    default:
      return action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }
}

// Error transformation for consistent error handling
function transformGDPRError(error: any): GDPRError {
  if (error instanceof Error) {
    // Try to parse the error message for specific GDPR error codes
    if (error.message.includes('insufficient permissions')) {
      return {
        code: 'INSUFFICIENT_PERMISSIONS',
        message: 'You do not have permission to perform this GDPR operation.',
        details: { originalError: error.message }
      };
    }
    
    if (error.message.includes('invalid engagement')) {
      return {
        code: 'INVALID_ENGAGEMENT',
        message: 'The specified engagement does not exist or is not accessible.',
        details: { originalError: error.message }
      };
    }
    
    if (error.message.includes('export limit exceeded')) {
      return {
        code: 'EXPORT_LIMIT_EXCEEDED',
        message: 'You have exceeded the maximum number of export requests. Please wait before requesting another export.',
        details: { originalError: error.message }
      };
    }
    
    if (error.message.includes('purge in progress')) {
      return {
        code: 'PURGE_IN_PROGRESS',
        message: 'A data purge operation is already in progress for this engagement.',
        details: { originalError: error.message }
      };
    }
    
    if (error.message.includes('invalid format')) {
      return {
        code: 'INVALID_FORMAT',
        message: 'The requested export format is not supported.',
        details: { originalError: error.message }
      };
    }
    
    if (error.message.includes('timeout') || error.message.includes('network')) {
      return {
        code: 'NETWORK_ERROR',
        message: 'Network error occurred. Please check your connection and try again.',
        details: { originalError: error.message }
      };
    }
  }
  
  return {
    code: 'UNKNOWN_ERROR',
    message: 'An unexpected error occurred during the GDPR operation.',
    details: { originalError: error?.message || String(error) }
  };
}

// Progress polling utility for long-running operations
export class GDPRJobPoller {
  private jobId: string;
  private intervalId?: NodeJS.Timeout;
  private onUpdate?: (status: GDPRJobStatus) => void;
  private onComplete?: (status: GDPRJobStatus) => void;
  private onError?: (error: GDPRError) => void;
  
  constructor(
    jobId: string,
    callbacks: {
      onUpdate?: (status: GDPRJobStatus) => void;
      onComplete?: (status: GDPRJobStatus) => void;
      onError?: (error: GDPRError) => void;
    }
  ) {
    this.jobId = jobId;
    this.onUpdate = callbacks.onUpdate;
    this.onComplete = callbacks.onComplete;
    this.onError = callbacks.onError;
  }
  
  start(pollInterval: number = 2000): void {
    this.stop(); // Ensure we don't have multiple intervals
    
    this.intervalId = setInterval(async () => {
      try {
        const status = await getJobStatus(this.jobId);
        
        this.onUpdate?.(status);
        
        if (status.status === 'completed' || status.status === 'failed') {
          this.stop();
          this.onComplete?.(status);
        }
      } catch (error) {
        this.stop();
        this.onError?.(transformGDPRError(error));
      }
    }, pollInterval);
  }
  
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = undefined;
    }
  }
}