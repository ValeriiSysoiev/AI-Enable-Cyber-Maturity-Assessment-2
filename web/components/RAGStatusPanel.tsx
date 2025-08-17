"use client";
import { useState, useEffect } from "react";
import { isAdmin } from "@/lib/auth";
import type { RAGConfiguration, IngestionStatus } from "@/types/evidence";

interface RAGStatusPanelProps {
  className?: string;
  engagementId?: string;
  showConfig?: boolean;
  showDocumentStatus?: boolean;
}

interface SystemHealth {
  rag_enabled: boolean;
  search_index_healthy: boolean;
  embeddings_service_healthy: boolean;
  total_documents: number;
  indexed_documents: number;
  pending_documents: number;
  failed_documents: number;
  last_index_update: string;
}

export default function RAGStatusPanel({ 
  className = "",
  engagementId,
  showConfig = true,
  showDocumentStatus = true
}: RAGStatusPanelProps) {
  const [ragConfig, setRagConfig] = useState<RAGConfiguration | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [documentStatuses, setDocumentStatuses] = useState<IngestionStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadRAGStatus();
  }, [engagementId]);

  async function loadRAGStatus() {
    try {
      setLoading(true);
      setError(null);

      // Load RAG configuration
      const configResponse = await fetch("/api/proxy/system/rag-config");
      if (configResponse.ok) {
        const config = await configResponse.json();
        setRagConfig(config);
      }

      // Load system health
      const healthResponse = await fetch("/api/proxy/system/health");
      if (healthResponse.ok) {
        const health = await healthResponse.json();
        setSystemHealth(health);
      }

      // Load document statuses for specific engagement
      if (engagementId && showDocumentStatus) {
        const statusResponse = await fetch(`/api/proxy/engagements/${engagementId}/docs/ingestion-status`);
        if (statusResponse.ok) {
          const statuses = await statusResponse.json();
          setDocumentStatuses(statuses);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load RAG status");
    } finally {
      setLoading(false);
    }
  }

  async function refreshStatus() {
    setRefreshing(true);
    await loadRAGStatus();
    setRefreshing(false);
  }

  async function testRAGConnection() {
    if (!ragConfig || !isAdmin()) return;

    try {
      setRefreshing(true);
      const response = await fetch("/api/proxy/system/rag-test", {
        method: "POST",
      });
      
      if (response.ok) {
        const result = await response.json();
        alert(`RAG Test: ${result.status}\n${result.message}`);
      } else {
        alert("RAG test failed");
      }
    } catch (err) {
      alert(`RAG test error: ${err}`);
    } finally {
      setRefreshing(false);
    }
  }

  function getStatusIcon(status: string) {
    switch (status) {
      case 'healthy': return '🟢';
      case 'degraded': return '🟡';
      case 'offline': return '🔴';
      default: return '❓';
    }
  }

  function getStatusColor(status: string) {
    switch (status) {
      case 'healthy': return 'text-green-600 bg-green-50 border-green-200';
      case 'degraded': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'offline': return 'text-red-600 bg-red-50 border-red-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  }

  function getIngestionStatusIcon(status: IngestionStatus['status']) {
    switch (status) {
      case 'completed': return '✅';
      case 'processing': return '⏳';
      case 'pending': return '⏱️';
      case 'failed': return '❌';
      default: return '❓';
    }
  }

  if (loading) {
    return (
      <div className={`rounded-xl border p-4 ${className}`}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 rounded w-1/3"></div>
          <div className="space-y-2">
            <div className="h-3 bg-gray-200 rounded"></div>
            <div className="h-3 bg-gray-200 rounded w-2/3"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* RAG Configuration Status */}
      {showConfig && ragConfig && (
        <div className="rounded-xl border p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="font-medium text-lg">RAG System Status</div>
            <div className="flex items-center gap-2">
              <button
                onClick={refreshStatus}
                disabled={refreshing}
                className="text-xs text-gray-600 hover:text-gray-800 border border-gray-300 px-2 py-1 rounded"
              >
                {refreshing ? "⟳ Refreshing..." : "🔄 Refresh"}
              </button>
              {isAdmin() && (
                <button
                  onClick={testRAGConnection}
                  disabled={refreshing}
                  className="text-xs text-blue-600 hover:text-blue-800 border border-blue-300 px-2 py-1 rounded"
                >
                  🧪 Test RAG
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* RAG Configuration */}
            <div className="space-y-3">
              <div className="font-medium text-sm text-gray-700">Configuration</div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Mode:</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    ragConfig.mode === 'azure_openai' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {ragConfig.mode}
                  </span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-gray-600">Status:</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium border ${
                    getStatusColor(ragConfig.status)
                  }`}>
                    {getStatusIcon(ragConfig.status)} {ragConfig.status}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-gray-600">Enabled:</span>
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    ragConfig.enabled ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {ragConfig.enabled ? '✓ Yes' : '✗ No'}
                  </span>
                </div>

                {ragConfig.model && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Model:</span>
                    <span className="text-gray-900 font-mono text-xs">{ragConfig.model}</span>
                  </div>
                )}

                {ragConfig.version && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Version:</span>
                    <span className="text-gray-900 font-mono text-xs">{ragConfig.version}</span>
                  </div>
                )}

                {ragConfig.last_check && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Last Check:</span>
                    <span className="text-gray-900 text-xs">
                      {new Date(ragConfig.last_check).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* System Health */}
            {systemHealth && (
              <div className="space-y-3">
                <div className="font-medium text-sm text-gray-700">System Health</div>
                
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Search Index:</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      systemHealth.search_index_healthy ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {systemHealth.search_index_healthy ? '🟢 Healthy' : '🔴 Unhealthy'}
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-gray-600">Embeddings:</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      systemHealth.embeddings_service_healthy ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {systemHealth.embeddings_service_healthy ? '🟢 Healthy' : '🔴 Unhealthy'}
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-gray-600">Documents:</span>
                    <span className="text-gray-900 text-xs">
                      {systemHealth.indexed_documents}/{systemHealth.total_documents} indexed
                    </span>
                  </div>

                  {systemHealth.pending_documents > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Pending:</span>
                      <span className="text-yellow-600 text-xs">
                        ⏳ {systemHealth.pending_documents}
                      </span>
                    </div>
                  )}

                  {systemHealth.failed_documents > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Failed:</span>
                      <span className="text-red-600 text-xs">
                        ❌ {systemHealth.failed_documents}
                      </span>
                    </div>
                  )}

                  <div className="flex justify-between">
                    <span className="text-gray-600">Last Update:</span>
                    <span className="text-gray-900 text-xs">
                      {new Date(systemHealth.last_index_update).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
              {error}
            </div>
          )}
        </div>
      )}

      {/* Document Ingestion Status */}
      {showDocumentStatus && engagementId && documentStatuses.length > 0 && (
        <div className="rounded-xl border p-4">
          <div className="font-medium text-lg mb-4">Document Processing Status</div>
          
          <div className="space-y-2">
            {documentStatuses.map((status, index) => (
              <div key={status.document_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <span className="text-lg">{getIngestionStatusIcon(status.status)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">
                      Document {status.document_id.slice(-8)}
                    </div>
                    <div className="text-xs text-gray-500">
                      Status: {status.status}
                      {status.chunks_created && ` • ${status.chunks_created} chunks`}
                      {status.processed_at && ` • ${new Date(status.processed_at).toLocaleString()}`}
                    </div>
                  </div>
                </div>
                
                <div className={`px-2 py-1 rounded text-xs font-medium ${
                  status.status === 'completed' ? 'bg-green-100 text-green-800' :
                  status.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                  status.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {status.status}
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="mt-4 pt-4 border-t border-gray-200 text-xs text-gray-500">
            <div className="flex justify-between">
              <span>
                Total: {documentStatuses.length} documents
              </span>
              <span>
                Completed: {documentStatuses.filter(s => s.status === 'completed').length}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* RAG Availability Notice */}
      {!ragConfig?.enabled && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-amber-600">⚠️</span>
            <span className="font-medium text-amber-900">RAG Not Available</span>
          </div>
          <div className="text-sm text-amber-800 space-y-1">
            <div>• RAG (Retrieval-Augmented Generation) is currently disabled</div>
            <div>• Evidence search will use basic text matching</div>
            <div>• Contact your administrator to enable advanced AI-powered search</div>
          </div>
        </div>
      )}

      {/* Performance Tips */}
      {ragConfig?.enabled && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-blue-600">💡</span>
            <span className="font-medium text-blue-900">RAG Tips</span>
          </div>
          <div className="text-sm text-blue-800 space-y-1">
            <div>• Ask specific questions for better grounded answers</div>
            <div>• Use domain-specific terminology for more relevant results</div>
            <div>• Combine keywords with context for improved accuracy</div>
            <div>• Check citation relevance scores to gauge confidence</div>
          </div>
        </div>
      )}
    </div>
  );
}