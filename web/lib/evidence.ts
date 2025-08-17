import { apiFetch } from "@/lib/api";
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
  RAGAnalysisResponse
} from "@/types/evidence";

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