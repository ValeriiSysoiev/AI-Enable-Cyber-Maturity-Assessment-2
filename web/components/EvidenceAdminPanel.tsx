"use client";
import { useState } from "react";
import { bulkReindex } from "../lib/evidence";
import { isAdmin } from "../lib/auth";
import RAGStatusPanel from "./RAGStatusPanel";
import type { BulkReindexResponse } from "../types/evidence";

interface EvidenceAdminPanelProps {
  className?: string;
}

export default function EvidenceAdminPanel({ className = "" }: EvidenceAdminPanelProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BulkReindexResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [engagementId, setEngagementId] = useState("");

  // Only show to admins
  if (!isAdmin()) {
    return null;
  }

  async function handleBulkReindex() {
    if (!engagementId.trim()) {
      setError("Please enter an engagement ID");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setResult(null);

      const response = await bulkReindex({
        engagement_id: engagementId.trim(),
        force: true,
      });

      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk reindex failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleGlobalReindex() {
    try {
      setLoading(true);
      setError(null);
      setResult(null);

      const response = await bulkReindex({
        engagement_id: "*", // Special value for all engagements
        force: true,
      });

      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Global reindex failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* RAG Status Panel */}
      <RAGStatusPanel 
        showConfig={true}
        showDocumentStatus={false}
      />
      
      <div className="rounded-xl border p-4 space-y-4">
        <div className="font-medium text-lg">Evidence Administration</div>
        <div className="text-sm text-gray-600">
          Admin-only tools for managing evidence search indexes
        </div>

      {/* Engagement-specific reindex */}
      <div className="space-y-3">
        <div className="font-medium">Reindex Engagement</div>
        <div className="flex gap-2">
          <input
            type="text"
            value={engagementId}
            onChange={(e) => setEngagementId(e.target.value)}
            placeholder="Enter engagement ID"
            className="flex-1 px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            onClick={handleBulkReindex}
            disabled={loading || !engagementId.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Reindexing..." : "Reindex"}
          </button>
        </div>
      </div>

      {/* Global reindex */}
      <div className="space-y-3 pt-4 border-t">
        <div className="font-medium">Global Operations</div>
        <div className="flex gap-2">
          <button
            onClick={handleGlobalReindex}
            disabled={loading}
            className="px-4 py-2 bg-orange-600 text-white rounded-md text-sm hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Reindexing..." : "Reindex All Engagements"}
          </button>
        </div>
        <div className="text-xs text-gray-500">
          ⚠️ This will reindex all documents across all engagements. Use with caution.
        </div>
      </div>

      {/* Results */}
      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          Error: {error}
        </div>
      )}

      {result && (
        <div className="text-sm text-green-600 bg-green-50 border border-green-200 rounded px-3 py-2">
          <div className="font-medium">✓ {result.message}</div>
          <div className="text-xs mt-1">
            Documents queued: {result.documents_queued}
            {result.estimated_completion_time && (
              <> • Estimated completion: {result.estimated_completion_time}</>
            )}
          </div>
        </div>
      )}

        {/* Status Information */}
        <div className="pt-4 border-t text-xs text-gray-500 space-y-1">
          <div>• Documents are processed in the background</div>
          <div>• Check individual engagement dashboards for ingestion status</div>
          <div>• Large document sets may take several minutes to process</div>
          <div>• RAG functionality requires documents to be successfully indexed</div>
        </div>
      </div>
    </div>
  );
}