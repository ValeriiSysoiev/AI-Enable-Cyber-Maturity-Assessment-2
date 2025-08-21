"use client";
import React, { useState, useCallback } from "react";
import CitationCard from "./CitationCard";
import DocumentViewer from "./DocumentViewer";
import type { Citation } from "@/types/csf";
import type { Evidence } from "@/types/evidence";

interface EnhancedCitationsListProps {
  citations: Citation[];
  evidence?: Evidence[];
  engagementId: string;
  className?: string;
  maxVisible?: number;
  showScore?: boolean;
  allowExpansion?: boolean;
  correlationId?: string;
}

export default function EnhancedCitationsList({
  citations,
  evidence = [],
  engagementId,
  className = "",
  maxVisible = 5,
  showScore = true,
  allowExpansion = true,
  correlationId
}: EnhancedCitationsListProps) {
  const [showAll, setShowAll] = useState(false);
  const [documentViewerOpen, setDocumentViewerOpen] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);

  const visibleCitations = showAll ? citations : citations.slice(0, maxVisible);
  const hasMore = citations.length > maxVisible;

  const findEvidenceForCitation = useCallback((citation: Citation): Evidence | undefined => {
    return evidence.find(e => e.id === citation.document_id);
  }, [evidence]);

  const handleViewInContext = useCallback((citation: Citation, evidenceItem?: Evidence) => {
    console.log(`[${correlationId}] Opening document viewer for citation: ${citation.document_id}:${citation.chunk_index}`);
    
    const targetEvidence = evidenceItem || findEvidenceForCitation(citation);
    
    setSelectedCitation(citation);
    setSelectedEvidence(targetEvidence || null);
    setDocumentViewerOpen(true);
  }, [findEvidenceForCitation, correlationId]);

  const handleCitationCopy = useCallback((citation: Citation, evidenceItem?: Evidence) => {
    console.log(`[${correlationId}] Citation copied: ${citation.document_id}:${citation.chunk_index}`);
    // Additional tracking or analytics could be added here
  }, [correlationId]);

  const handleCloseDocumentViewer = useCallback(() => {
    console.log(`[${correlationId}] Document viewer closed`);
    setDocumentViewerOpen(false);
    setSelectedCitation(null);
    setSelectedEvidence(null);
  }, [correlationId]);

  const exportCitationsAsJson = useCallback(async () => {
    const exportData = {
      timestamp: new Date().toISOString(),
      engagement_id: engagementId,
      correlation_id: correlationId,
      total_citations: citations.length,
      citations: citations.map((citation, index) => ({
        citation_number: index + 1,
        document_id: citation.document_id,
        document_name: citation.document_name,
        relevance_score: citation.relevance_score,
        page_number: citation.page_number,
        chunk_index: citation.chunk_index,
        excerpt: citation.excerpt,
        url: citation.url,
        metadata: citation.metadata
      }))
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { 
      type: "application/json" 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `citations-${engagementId}-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    console.log(`[${correlationId}] Citations exported as JSON`);
  }, [citations, engagementId, correlationId]);

  const exportCitationsAsCsv = useCallback(async () => {
    const headers = [
      'Citation Number',
      'Document Name', 
      'Relevance Score',
      'Page Number',
      'Chunk Index',
      'Excerpt',
      'URL'
    ];

    const csvContent = [
      headers.join(','),
      ...citations.map((citation, index) => [
        index + 1,
        `"${citation.document_name.replace(/"/g, '""')}"`,
        citation.relevance_score,
        citation.page_number || '',
        citation.chunk_index,
        `"${citation.excerpt.replace(/"/g, '""')}"`,
        citation.url || ''
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `citations-${engagementId}-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    console.log(`[${correlationId}] Citations exported as CSV`);
  }, [citations, engagementId, correlationId]);

  if (citations.length === 0) {
    return (
      <div className={`text-center py-8 text-gray-500 ${className}`} role="status">
        <div className="text-2xl mb-2" role="img" aria-label="No citations">📄</div>
        <div className="text-sm">No citations available</div>
        <div className="text-xs mt-1">Citations will appear here when evidence is analyzed</div>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-gray-900">
            Supporting Evidence
          </h3>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            {citations.length} citation{citations.length !== 1 ? 's' : ''}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Export Options */}
          <div className="flex items-center gap-1">
            <button
              onClick={exportCitationsAsJson}
              className="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-800 border border-gray-300 hover:border-gray-400 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Export citations as JSON"
            >
              Export JSON
            </button>
            <button
              onClick={exportCitationsAsCsv}
              className="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-800 border border-gray-300 hover:border-gray-400 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Export citations as CSV"
            >
              Export CSV
            </button>
          </div>
        </div>
      </div>

      {/* Quality Summary */}
      <div className="bg-gray-50 rounded-lg p-3">
        <div className="flex items-center justify-between text-sm">
          <div className="text-gray-700">
            Average relevance: <span className="font-medium">{((citations.reduce((sum, c) => sum + c.relevance_score, 0) / citations.length) * 100).toFixed(1)}%</span>
          </div>
          <div className="text-gray-700">
            High confidence: <span className="font-medium">{citations.filter(c => c.relevance_score >= 0.7).length}/{citations.length}</span>
          </div>
        </div>
        <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
          <div 
            className="bg-gradient-to-r from-yellow-400 to-green-500 h-1.5 rounded-full"
            style={{ 
              width: `${(citations.reduce((sum, c) => sum + c.relevance_score, 0) / citations.length) * 100}%` 
            }}
          />
        </div>
      </div>

      {/* Citations Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-1">
        {visibleCitations.map((citation, index) => (
          <CitationCard
            key={`${citation.document_id}-${citation.chunk_index}`}
            citation={citation}
            evidence={findEvidenceForCitation(citation)}
            onViewInContext={handleViewInContext}
            onCitationCopy={handleCitationCopy}
            correlationId={correlationId}
          />
        ))}
      </div>

      {/* Show More/Less Toggle */}
      {hasMore && (
        <div className="text-center">
          <button
            onClick={() => setShowAll(!showAll)}
            className="px-4 py-2 text-sm text-blue-600 hover:text-blue-700 border border-blue-200 hover:border-blue-300 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {showAll ? (
              <>Show Less ({maxVisible} of {citations.length})</>
            ) : (
              <>Show All Citations ({citations.length})</>
            )}
          </button>
        </div>
      )}

      {/* Document Viewer Modal */}
      <DocumentViewer
        evidence={selectedEvidence}
        citation={selectedCitation}
        isOpen={documentViewerOpen}
        onClose={handleCloseDocumentViewer}
        correlationId={correlationId}
      />
    </div>
  );
}