"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { 
  getDocumentsWithIngestion, 
  ingestDocument, 
  bulkReindex,
  getIngestionStatuses 
} from "../lib/evidence";
import { uploadDocs, deleteDoc, downloadUrl } from "../lib/docs";
import { isAdmin } from "../lib/auth";
import type { DocumentWithIngestion, IngestionStatus } from "../types/evidence";

export default function DocumentsPanel() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [documents, setDocuments] = useState<DocumentWithIngestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [ingestionStatuses, setIngestionStatuses] = useState<Record<string, IngestionStatus>>({});

  // Load documents and ingestion statuses
  useEffect(() => {
    if (!engagementId) return;
    loadDocuments();
    
    // Set up polling for ingestion status updates
    const interval = setInterval(pollIngestionStatuses, 5000);
    return () => clearInterval(interval);
  }, [engagementId]);

  async function loadDocuments() {
    if (!engagementId) return;
    
    try {
      setLoading(true);
      const docs = await getDocumentsWithIngestion(engagementId);
      setDocuments(docs);
      
      // Update ingestion statuses map
      const statusMap: Record<string, IngestionStatus> = {};
      docs.forEach(doc => {
        if (doc.ingestion_status) {
          statusMap[doc.id] = doc.ingestion_status;
        }
      });
      setIngestionStatuses(statusMap);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }

  async function pollIngestionStatuses() {
    if (!engagementId || documents.length === 0) return;
    
    try {
      const statuses = await getIngestionStatuses(engagementId);
      const statusMap: Record<string, IngestionStatus> = {};
      statuses.forEach(status => {
        statusMap[status.document_id] = status;
      });
      setIngestionStatuses(statusMap);
    } catch (err) {
      // Silent failure for polling
      console.warn("Failed to poll ingestion statuses:", err);
    }
  }

  async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const files = event.target.files;
    if (!files || !engagementId) return;

    try {
      setUploading(true);
      await uploadDocs(engagementId, Array.from(files));
      await loadDocuments();
      // Reset file input
      event.target.value = "";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleIngestDocument(documentId: string) {
    if (!engagementId) return;
    
    try {
      await ingestDocument(engagementId, documentId);
      // Update local status to processing
      setIngestionStatuses(prev => ({
        ...prev,
        [documentId]: {
          document_id: documentId,
          status: 'processing',
        }
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingestion failed");
    }
  }

  async function handleBulkReindex() {
    if (!engagementId) return;
    
    try {
      setReindexing(true);
      const result = await bulkReindex({ engagement_id: engagementId });
      
      // Update all document statuses to processing
      const updatedStatuses: Record<string, IngestionStatus> = {};
      documents.forEach(doc => {
        updatedStatuses[doc.id] = {
          document_id: doc.id,
          status: 'processing',
        };
      });
      setIngestionStatuses(updatedStatuses);
      
      setError(null);
      // Show success message temporarily
      const originalError = error;
      setError(`✓ ${result.message}`);
      setTimeout(() => setError(originalError), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk reindex failed");
    } finally {
      setReindexing(false);
    }
  }

  async function handleDeleteDocument(documentId: string) {
    if (!engagementId) return;
    
    try {
      await deleteDoc(engagementId, documentId);
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  function getStatusIcon(status?: IngestionStatus) {
    if (!status) return "⚪"; // Not indexed
    
    switch (status.status) {
      case 'completed': return "✅";
      case 'processing': return "🔄";
      case 'pending': return "⏳";
      case 'failed': return "❌";
      default: return "⚪";
    }
  }

  function getStatusText(status?: IngestionStatus) {
    if (!status) return "Not indexed";
    
    switch (status.status) {
      case 'completed': return `Indexed (${status.chunks_created || 0} chunks)`;
      case 'processing': return "Processing...";
      case 'pending': return "Pending";
      case 'failed': return `Failed: ${status.error_message || 'Unknown error'}`;
      default: return "Unknown";
    }
  }

  if (loading) {
    return (
      <div className="rounded-xl border p-4">
        <div className="font-medium mb-2">Documents</div>
        <div className="text-sm text-gray-500">Loading documents...</div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="font-medium">Documents & Evidence</div>
        <div className="flex gap-2">
          {isAdmin() && (
            <button
              onClick={handleBulkReindex}
              disabled={reindexing || documents.length === 0}
              className="px-3 py-1 text-sm border rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {reindexing ? "Reindexing..." : "Reindex All"}
            </button>
          )}
          <label className="px-3 py-1 text-sm border rounded-md hover:bg-gray-50 cursor-pointer">
            {uploading ? "Uploading..." : "Upload Files"}
            <input
              type="file"
              multiple
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
              accept=".pdf,.docx,.xlsx,.csv,.md,.txt,.png,.jpg,.jpeg"
            />
          </label>
        </div>
      </div>

      {error && (
        <div className={`text-sm px-3 py-2 rounded ${
          error.startsWith('✓') 
            ? 'bg-green-50 text-green-700 border border-green-200' 
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {error}
        </div>
      )}

      {documents.length === 0 ? (
        <div className="text-sm text-gray-500 text-center py-4">
          No documents uploaded yet.
        </div>
      ) : (
        <div className="space-y-2">
          {documents.map((doc) => {
            const status = ingestionStatuses[doc.id] || doc.ingestion_status;
            return (
              <div key={doc.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">{getStatusIcon(status)}</span>
                    <span className="font-medium text-sm truncate">{doc.filename}</span>
                  </div>
                  <div className="text-xs text-gray-500 space-y-1">
                    <div>Size: {(doc.size / 1024).toFixed(1)} KB • Uploaded: {new Date(doc.uploaded_at).toLocaleDateString()}</div>
                    <div>Status: {getStatusText(status)}</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2 ml-3">
                  {(!status || status.status === 'failed') && (
                    <button
                      onClick={() => handleIngestDocument(doc.id)}
                      className="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded hover:bg-blue-100"
                    >
                      Ingest
                    </button>
                  )}
                  <a
                    href={downloadUrl(engagementId!, doc.id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2 py-1 text-xs bg-gray-50 text-gray-700 rounded hover:bg-gray-100"
                  >
                    Download
                  </a>
                  <button
                    onClick={() => handleDeleteDocument(doc.id)}
                    className="px-2 py-1 text-xs bg-red-50 text-red-700 rounded hover:bg-red-100"
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
      
      <div className="text-xs text-gray-500 pt-2 border-t">
        {documents.length} document{documents.length !== 1 ? 's' : ''} • 
        {Object.values(ingestionStatuses).filter(s => s.status === 'completed').length} indexed for evidence search
      </div>
    </div>
  );
}