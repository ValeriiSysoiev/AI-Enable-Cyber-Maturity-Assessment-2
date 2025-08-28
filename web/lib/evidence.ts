import { apiFetch } from "./api";
import type {
  IngestionStatus,
  EvidenceSearchRequest,
  EvidenceSearchResponse,
  DocumentWithIngestion,
  BulkReindexRequest,
  BulkReindexResponse,
  Citation,
  RAGConfiguration,
  RAGSearchRequest,
  RAGSearchResponse,
  RAGAnalysisRequest,
  RAGAnalysisResponse,
  Evidence,
  SASRequest,
  SASResponse,
  CompleteRequest,
  CompleteResponse,
  LinkRequest,
  LinkResponse,
  UnlinkResponse,
  EvidenceListResponse
} from "../types/evidence";

// Evidence search endpoints
export async function searchEvidence(request: EvidenceSearchRequest): Promise<EvidenceSearchResponse> {
  const response = await fetch("/api/proxy/evidence/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Search failed" }));
    throw new Error(error.detail || `Search failed: ${response.status}`);
  }
  
  return response.json();
}

// Document ingestion status
export async function getIngestionStatus(engagementId: string, documentId: string): Promise<IngestionStatus> {
  const response = await fetch(`/api/proxy/engagements/${engagementId}/docs/${documentId}/ingestion-status`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to get ingestion status" }));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export async function getIngestionStatuses(engagementId: string): Promise<IngestionStatus[]> {
  const response = await fetch(`/api/proxy/engagements/${engagementId}/docs/ingestion-status`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to get ingestion statuses" }));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

// Manual document ingestion
export async function ingestDocument(engagementId: string, documentId: string): Promise<{ message: string }> {
  const response = await fetch(`/api/proxy/engagements/${engagementId}/docs/${documentId}/ingest`, {
    method: "POST",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Ingestion failed" }));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

// Bulk reindexing operations
export async function bulkReindex(request: BulkReindexRequest): Promise<BulkReindexResponse> {
  const response = await fetch("/api/proxy/evidence/reindex", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Bulk reindex failed" }));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

// Get documents with ingestion status
export async function getDocumentsWithIngestion(engagementId: string): Promise<DocumentWithIngestion[]> {
  const [documents, statuses] = await Promise.all([
    apiFetch(`/engagements/${engagementId}/docs`),
    getIngestionStatuses(engagementId).catch(() => [])
  ]);

  return documents.map((doc: any) => ({
    ...doc,
    ingestion_status: statuses.find((s: IngestionStatus) => s.document_id === doc.id)
  }));
}

// Evidence-enhanced analysis
export async function analyzeWithEvidence(
  engagementId: string,
  content: string,
  useEvidence: boolean = false
): Promise<any> {
  const response = await fetch("/api/proxy/analysis/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      engagement_id: engagementId,
      content,
      use_evidence: useEvidence,
    }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Analysis failed" }));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

// Get citations for an analysis
export async function getCitations(analysisId: string): Promise<Citation[]> {
  const response = await fetch(`/api/proxy/analysis/${analysisId}/citations`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to get citations" }));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

// Evidence export functionality
export async function exportEvidenceReport(engagementId: string): Promise<Blob> {
  const response = await fetch(`/api/proxy/evidence/${engagementId}/export`, {
    method: "GET",
    headers: {
      "Accept": "application/pdf",
    },
  });

  if (!response.ok) {
    throw new Error(`Export failed: ${response.statusText}`);
  }

  return response.blob();
}

// RAG Configuration
export async function getRAGConfiguration(): Promise<RAGConfiguration> {
  const response = await fetch("/api/proxy/system/rag-config");
  if (!response.ok) {
    throw new Error(`Failed to get RAG configuration: ${response.status}`);
  }
  return response.json();
}

export async function updateRAGConfiguration(config: Partial<RAGConfiguration>): Promise<RAGConfiguration> {
  const response = await fetch("/api/proxy/system/rag-config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    throw new Error(`Failed to update RAG configuration: ${response.status}`);
  }
  return response.json();
}

export async function testRAGConnection(): Promise<{ status: string; message: string }> {
  const response = await fetch("/api/proxy/system/rag-test", {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`RAG test failed: ${response.status}`);
  }
  return response.json();
}

// RAG Search
export async function ragSearch(request: RAGSearchRequest): Promise<RAGSearchResponse> {
  const response = await fetch("/api/proxy/orchestrations/rag-search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "RAG search failed" }));
    throw new Error(error.detail || `RAG search failed: ${response.status}`);
  }
  
  return response.json();
}

// RAG Analysis
export async function ragAnalyze(request: RAGAnalysisRequest): Promise<RAGAnalysisResponse> {
  const response = await fetch("/api/proxy/orchestrations/rag-analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "RAG analysis failed" }));
    throw new Error(error.detail || `RAG analysis failed: ${response.status}`);
  }
  
  return response.json();
}

export async function ragRecommend(engagementId: string, content?: string): Promise<RAGAnalysisResponse> {
  const response = await fetch("/api/proxy/orchestrations/rag-recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      engagement_id: engagementId,
      content: content || "",
      use_rag: true,
      analysis_type: 'recommend'
    }),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "RAG recommendations failed" }));
    throw new Error(error.detail || `RAG recommendations failed: ${response.status}`);
  }
  
  return response.json();
}

// System Health
export async function getSystemHealth(): Promise<any> {
  const response = await fetch("/api/proxy/system/health");
  if (!response.ok) {
    throw new Error(`Failed to get system health: ${response.status}`);
  }
  return response.json();
}

// Enhanced evidence search with optional RAG
export async function enhancedEvidenceSearch(
  request: EvidenceSearchRequest & { use_rag?: boolean }
): Promise<EvidenceSearchResponse | RAGSearchResponse> {
  if (request.use_rag) {
    return ragSearch({
      query: request.query,
      engagement_id: request.engagement_id!,
      top_k: request.top_k,
      score_threshold: request.score_threshold,
      use_grounding: true,
    });
  } else {
    return searchEvidence(request);
  }
}

// Enhanced analysis with evidence and optional RAG
export async function enhancedAnalyzeWithEvidence(
  engagementId: string,
  content: string,
  useEvidence: boolean = false,
  useRAG: boolean = false
): Promise<RAGAnalysisResponse> {
  if (useRAG) {
    return ragAnalyze({
      engagement_id: engagementId,
      content,
      use_evidence: useEvidence,
      use_rag: true,
      analysis_type: 'analyze'
    });
  } else {
    // Fallback to standard analysis
    const result = await analyzeWithEvidence(engagementId, content, useEvidence);
    // Ensure compatibility with RAGAnalysisResponse interface
    return {
      ...result,
      use_rag: false,
      confidence_score: undefined,
      rag_grounding: undefined,
      grounded_insights: undefined,
      evidence_quality_score: undefined,
      recommendations_count: undefined,
      processing_time_ms: undefined
    };
  }
}

// Evidence Upload and Management API Methods

// Generate SAS token for evidence upload
export async function generateEvidenceSAS(request: SASRequest): Promise<SASResponse> {
  const response = await fetch("/api/proxy/evidence/sas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "SAS generation failed" }));
    throw new Error(error.detail || `SAS generation failed: ${response.status}`);
  }
  
  return response.json();
}

// Complete evidence upload after file upload
export async function completeEvidenceUpload(request: CompleteRequest): Promise<CompleteResponse> {
  const response = await fetch("/api/proxy/evidence/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload completion failed" }));
    throw new Error(error.detail || `Upload completion failed: ${response.status}`);
  }
  
  return response.json();
}

// List evidence for an engagement with pagination
export async function listEvidence(
  engagementId: string,
  page: number = 1,
  pageSize: number = 50
): Promise<EvidenceListResponse> {
  const params = new URLSearchParams({
    engagement_id: engagementId,
    page: page.toString(),
    page_size: pageSize.toString(),
  });
  
  const response = await fetch(`/api/proxy/evidence?${params}`);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to list evidence" }));
    throw new Error(error.detail || `Failed to list evidence: ${response.status}`);
  }
  
  const data = await response.json();
  
  // Extract pagination info from headers
  const total = parseInt(response.headers.get('X-Total-Count') || '0');
  const currentPage = parseInt(response.headers.get('X-Page') || '1');
  const pageSizeHeader = parseInt(response.headers.get('X-Page-Size') || '50');
  const totalPages = parseInt(response.headers.get('X-Total-Pages') || '1');
  const hasNext = response.headers.get('X-Has-Next') === 'true';
  const hasPrevious = response.headers.get('X-Has-Previous') === 'true';
  
  return {
    data,
    total,
    page: currentPage,
    page_size: pageSizeHeader,
    total_pages: totalPages,
    has_next: hasNext,
    has_previous: hasPrevious,
  };
}

// Link evidence to an assessment item
export async function linkEvidence(evidenceId: string, request: LinkRequest): Promise<LinkResponse> {
  const response = await fetch(`/api/proxy/evidence/${evidenceId}/links`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Evidence linking failed" }));
    throw new Error(error.detail || `Evidence linking failed: ${response.status}`);
  }
  
  return response.json();
}

// Unlink evidence from an assessment item
export async function unlinkEvidence(evidenceId: string, linkId: string): Promise<UnlinkResponse> {
  const response = await fetch(`/api/proxy/evidence/${evidenceId}/links/${linkId}`, {
    method: "DELETE",
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Evidence unlinking failed" }));
    throw new Error(error.detail || `Evidence unlinking failed: ${response.status}`);
  }
  
  return response.json();
}

// Utility function to upload file to Azure Storage with SAS URL
export async function uploadFileToAzure(sasUrl: string, file: File): Promise<void> {
  const response = await fetch(sasUrl, {
    method: "PUT",
    headers: {
      "x-ms-blob-type": "BlockBlob",
      "Content-Type": file.type || "application/octet-stream",
    },
    body: file,
  });
  
  if (!response.ok) {
    throw new Error(`Azure upload failed: ${response.statusText}`);
  }
}

// Compute client-side checksum (SHA-256) for file integrity
export async function computeFileChecksum(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
}

// Format file size for display
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Get file icon based on MIME type
export function getFileIcon(mimeType: string): string {
  if (mimeType.startsWith('image/')) return '🖼️';
  if (mimeType.includes('pdf')) return '📄';
  if (mimeType.includes('word') || mimeType.includes('document')) return '📝';
  if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return '📊';
  if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) return '📽️';
  if (mimeType.startsWith('text/')) return '📄';
  if (mimeType.includes('zip') || mimeType.includes('archive')) return '📦';
  return '📄';
}