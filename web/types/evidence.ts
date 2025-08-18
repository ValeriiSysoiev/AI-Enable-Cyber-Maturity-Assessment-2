// Evidence and RAG-related TypeScript types

export interface IngestionStatus {
  document_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  chunks_created?: number;
  error_message?: string;
  processed_at?: string;
}

export interface RAGConfiguration {
  mode: 'azure_openai' | 'none';
  enabled: boolean;
  endpoint?: string;
  version?: string;
  model?: string;
  status: 'healthy' | 'degraded' | 'offline';
  last_check?: string;
}

export interface RAGSearchRequest {
  query: string;
  engagement_id: string;
  top_k?: number;
  score_threshold?: number;
  use_grounding?: boolean;
}

export interface RAGSearchResponse {
  results: SearchResult[];
  grounded_answer?: string;
  query: string;
  total_results: number;
  processing_time_ms: number;
  sources_used: number;
}

export interface SearchResult {
  content: string;
  score: number;
  document_id: string;
  document_name: string;
  page_number?: number;
  chunk_index: number;
  url?: string;
}

export interface EvidenceSearchRequest {
  query: string;
  top_k?: number;
  score_threshold?: number;
  engagement_id?: string;
}

export interface EvidenceSearchResponse {
  results: SearchResult[];
  query: string;
  total_results: number;
  processing_time_ms: number;
}

export interface DocumentWithIngestion {
  id: string;
  engagement_id: string;
  filename: string;
  content_type?: string;
  size: number;
  uploaded_by: string;
  uploaded_at: string;
  ingestion_status?: IngestionStatus;
}

export interface BulkReindexRequest {
  engagement_id: string;
  force?: boolean;
}

export interface BulkReindexResponse {
  message: string;
  documents_queued: number;
  estimated_completion_time?: string;
}

export interface Citation {
  document_id: string;
  document_name: string;
  page_number?: number;
  chunk_index: number;
  relevance_score: number;
  excerpt: string;
  url?: string;
  metadata?: Record<string, any>;
}

export interface AnalysisWithEvidence {
  id: string;
  content: string;
  use_evidence: boolean;
  use_rag?: boolean;
  citations?: Citation[];
  evidence_used: boolean;
  rag_grounding?: string;
  confidence_score?: number;
  created_at: string;
  processing_time_ms?: number;
}

export interface RAGAnalysisRequest {
  engagement_id: string;
  content: string;
  use_evidence?: boolean;
  use_rag?: boolean;
  analysis_type?: 'analyze' | 'recommend' | 'summarize';
}

export interface RAGAnalysisResponse extends AnalysisWithEvidence {
  grounded_insights?: string[];
  evidence_quality_score?: number;
  recommendations_count?: number;
}

// Authentication types for AAD integration
export interface AADUser {
  id: string;
  email: string;
  name: string;
  roles?: string[];
  tenant_id?: string;
}

export interface AuthMode {
  mode: 'demo' | 'aad';
  enabled: boolean;
}

export interface AuthContext {
  user: AADUser | null;
  mode: AuthMode;
  isAuthenticated: boolean;
  isLoading: boolean;
  error?: string;
}

// Evidence Upload and Management Types
export interface Evidence {
  id: string;
  engagement_id: string;
  blob_path: string;
  filename: string;
  checksum_sha256: string;
  size: number;
  mime_type: string;
  uploaded_by: string;
  uploaded_at: string;
  pii_flag: boolean;
  linked_items: EvidenceLink[];
}

export interface EvidenceLink {
  item_type: string;
  item_id: string;
}

export interface SASRequest {
  engagement_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
}

export interface SASResponse {
  upload_url: string;
  blob_path: string;
  expires_at: string;
  max_size: number;
  allowed_types: string[];
}

export interface CompleteRequest {
  engagement_id: string;
  blob_path: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  client_checksum?: string;
}

export interface CompleteResponse {
  evidence_id: string;
  checksum: string;
  pii_flag: boolean;
  size: number;
}

export interface LinkRequest {
  item_type: string;
  item_id: string;
}

export interface LinkResponse {
  message: string;
  evidence_id: string;
  item_type: string;
  item_id: string;
  total_links: number;
}

export interface UnlinkResponse {
  message: string;
  evidence_id: string;
  item_type: string;
  item_id: string;
  remaining_links: number;
}

export interface EvidenceListResponse {
  data: Evidence[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface UploadState {
  status: 'idle' | 'generating_sas' | 'uploading' | 'completing' | 'completed' | 'error';
  progress: number;
  error?: string;
  evidence?: Evidence;
}