"use client";
import React, { useState, useCallback, useMemo } from "react";
import type { Evidence } from "@/types/evidence";
import type { Citation } from "@/types/csf";

interface EvidenceTrayProps {
  evidence: Evidence[];
  citations?: Citation[];
  loading?: boolean;
  error?: string | null;
  onEvidenceSelect?: (evidence: Evidence) => void;
  onCitationView?: (citation: Citation) => void;
  onRetry?: () => void;
  correlationId?: string;
}

interface EvidenceItemProps {
  evidence: Evidence;
  citations: Citation[];
  onSelect: (evidence: Evidence) => void;
  onCitationView: (citation: Citation) => void;
  correlationId?: string;
}

const EvidenceItem: React.FC<EvidenceItemProps> = ({ 
  evidence, 
  citations, 
  onSelect, 
  onCitationView,
  correlationId 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Find citations for this evidence item
  const evidenceCitations = useMemo(
    () => citations.filter(c => c.document_id === evidence.id),
    [citations, evidence.id]
  );

  const handleToggleExpand = useCallback(() => {
    setIsExpanded(prev => !prev);
    console.log(`[${correlationId}] Evidence item ${evidence.id} expanded: ${!isExpanded}`);
  }, [evidence.id, isExpanded, correlationId]);

  const handleEvidenceSelect = useCallback(() => {
    console.log(`[${correlationId}] Evidence selected: ${evidence.filename}`);
    onSelect(evidence);
  }, [evidence, onSelect, correlationId]);

  const handleCitationClick = useCallback((citation: Citation, event: React.MouseEvent) => {
    event.stopPropagation();
    console.log(`[${correlationId}] Citation clicked: ${citation.document_id}:${citation.chunk_index}`);
    onCitationView(citation);
  }, [onCitationView, correlationId]);

  return (
    <div className="border border-gray-200 rounded-lg bg-white shadow-sm">
      <div 
        className="p-4 cursor-pointer hover:bg-gray-50 focus:bg-gray-50"
        onClick={handleEvidenceSelect}
        tabIndex={0}
        role="button"
        aria-expanded={isExpanded}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleEvidenceSelect();
          }
        }}
      >
        <div className="flex items-start gap-3">
          <span className="text-lg mt-1" role="img" aria-label="Document">📄</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-gray-900 truncate">
                {evidence.filename}
              </h4>
              <div className="flex items-center gap-2">
                {evidenceCitations.length > 0 && (
                  <span className="inline-flex items-center px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
                    {evidenceCitations.length} citation{evidenceCitations.length !== 1 ? 's' : ''}
                  </span>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleToggleExpand();
                  }}
                  className="p-1 hover:bg-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  aria-label={isExpanded ? "Collapse details" : "Expand details"}
                >
                  <span className="text-gray-400">
                    {isExpanded ? '−' : '+'}
                  </span>
                </button>
              </div>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {evidence.mime_type} • {(evidence.size / 1024).toFixed(1)} KB
            </div>
            <div className="text-xs text-gray-500">
              Uploaded {new Date(evidence.uploaded_at).toLocaleDateString()}
            </div>
          </div>
        </div>
      </div>

      {isExpanded && (
        <div className="border-t border-gray-100 p-4 bg-gray-50">
          {/* Evidence Details */}
          <div className="space-y-3">
            <div>
              <h5 className="text-xs font-medium text-gray-700 uppercase tracking-wide">
                File Information
              </h5>
              <div className="mt-1 text-sm text-gray-600">
                <div>Size: {(evidence.size / 1024).toFixed(1)} KB</div>
                <div>Type: {evidence.mime_type}</div>
                <div>Uploaded by: {evidence.uploaded_by}</div>
                {evidence.pii_flag && (
                  <div className="flex items-center gap-1 text-orange-600 mt-1">
                    <span role="img" aria-label="Warning">⚠️</span>
                    <span className="text-xs">Potential PII detected</span>
                  </div>
                )}
              </div>
            </div>

            {/* Linked Items */}
            {evidence.linked_items.length > 0 && (
              <div>
                <h5 className="text-xs font-medium text-gray-700 uppercase tracking-wide">
                  Linked Items
                </h5>
                <div className="mt-1 flex flex-wrap gap-1">
                  {evidence.linked_items.map((link, idx) => (
                    <span 
                      key={idx}
                      className="inline-flex items-center px-2 py-1 text-xs bg-green-100 text-green-700 rounded"
                    >
                      {link.item_type}: {link.item_id.substring(0, 8)}...
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Citations */}
            {evidenceCitations.length > 0 && (
              <div>
                <h5 className="text-xs font-medium text-gray-700 uppercase tracking-wide">
                  Inline Citations
                </h5>
                <div className="mt-2 space-y-2">
                  {evidenceCitations.map((citation, idx) => (
                    <div 
                      key={idx}
                      className="p-3 bg-white border border-gray-200 rounded cursor-pointer hover:bg-blue-50 focus:bg-blue-50"
                      onClick={(e) => handleCitationClick(citation, e)}
                      tabIndex={0}
                      role="button"
                      aria-label={`View citation from page ${citation.page_number || 'unknown'}`}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          handleCitationClick(citation, e);
                        }
                      }}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="text-xs text-gray-500 mb-1">
                            {citation.page_number && `Page ${citation.page_number} • `}
                            Relevance: {(citation.relevance_score * 100).toFixed(0)}%
                          </div>
                          <div className="text-sm text-gray-800 line-clamp-3">
                            {citation.excerpt}
                          </div>
                        </div>
                        <button
                          className="ml-2 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          onClick={(e) => handleCitationClick(citation, e)}
                        >
                          View
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default function EvidenceTray({
  evidence,
  citations = [],
  loading = false,
  error = null,
  onEvidenceSelect,
  onCitationView,
  onRetry,
  correlationId
}: EvidenceTrayProps) {
  const handleEvidenceSelect = useCallback((selectedEvidence: Evidence) => {
    onEvidenceSelect?.(selectedEvidence);
  }, [onEvidenceSelect]);

  const handleCitationView = useCallback((citation: Citation) => {
    onCitationView?.(citation);
  }, [onCitationView]);

  // Loading state
  if (loading) {
    return (
      <div className="p-6" role="status" aria-live="polite">
        <div className="flex items-center justify-center">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
            <span className="text-gray-600">Loading evidence...</span>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-6" role="alert" aria-live="assertive">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-800">
            <span role="img" aria-label="Error">⚠️</span>
            <span className="font-medium">Failed to load evidence</span>
          </div>
          <p className="text-red-600 text-sm mt-1">{error}</p>
          {onRetry && (
            <button 
              onClick={onRetry}
              className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  // Empty state
  if (evidence.length === 0) {
    return (
      <div className="p-6" role="status">
        <div className="flex flex-col items-center justify-center py-8">
          <div className="text-4xl mb-4" role="img" aria-label="Empty folder">📂</div>
          <div className="text-gray-600 mb-2">No evidence files found</div>
          <div className="text-sm text-gray-500 text-center">
            Upload documents and link them to see evidence and citations here
          </div>
        </div>
      </div>
    );
  }

  // Evidence list
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Evidence & Citations
        </h3>
        <div className="text-sm text-gray-500">
          {evidence.length} file{evidence.length !== 1 ? 's' : ''} • {citations.length} citation{citations.length !== 1 ? 's' : ''}
        </div>
      </div>
      
      <div className="space-y-3" role="list" aria-label="Evidence files">
        {evidence.map((evidenceItem) => (
          <div key={evidenceItem.id} role="listitem">
            <EvidenceItem
              evidence={evidenceItem}
              citations={citations}
              onSelect={handleEvidenceSelect}
              onCitationView={handleCitationView}
              correlationId={correlationId}
            />
          </div>
        ))}
      </div>
    </div>
  );
}