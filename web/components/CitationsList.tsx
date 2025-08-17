"use client";
import { useState } from "react";
import { downloadUrl } from "@/lib/docs";
import type { Citation } from "@/types/evidence";

interface CitationsListProps {
  citations: Citation[];
  engagementId: string;
  className?: string;
  maxVisible?: number;
  showScore?: boolean;
  allowExpansion?: boolean;
}

interface CitationItemProps {
  citation: Citation;
  engagementId: string;
  index: number;
  showScore?: boolean;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

function CitationItem({ 
  citation, 
  engagementId, 
  index, 
  showScore = true,
  isExpanded = false,
  onToggleExpand 
}: CitationItemProps) {
  const [imageError, setImageError] = useState(false);

  function getRelevanceColor(score: number) {
    if (score >= 0.8) return "text-green-600 bg-green-50 border-green-200";
    if (score >= 0.6) return "text-blue-600 bg-blue-50 border-blue-200";
    if (score >= 0.4) return "text-yellow-600 bg-yellow-50 border-yellow-200";
    return "text-gray-600 bg-gray-50 border-gray-200";
  }

  function formatRelevanceScore(score: number) {
    return `${(score * 100).toFixed(1)}%`;
  }

  function getDocumentIcon(documentName: string) {
    const ext = documentName.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf': return '📄';
      case 'doc':
      case 'docx': return '📝';
      case 'txt': return '📃';
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif': return '🖼️';
      default: return '📎';
    }
  }

  async function handleCopyLink() {
    const url = downloadUrl(engagementId, citation.document_id);
    try {
      await navigator.clipboard.writeText(url);
      // Could add a toast notification here
    } catch (error) {
      console.warn("Failed to copy link:", error);
    }
  }

  return (
    <div className={`border rounded-lg transition-all duration-200 ${
      isExpanded ? 'ring-2 ring-blue-200 bg-blue-50/30' : 'bg-gray-50 hover:bg-gray-100'
    }`}>
      {/* Citation Header */}
      <div className="p-3">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-lg">{getDocumentIcon(citation.document_name)}</span>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm text-blue-700 truncate">
                  {citation.document_name}
                </div>
                <div className="text-xs text-gray-500 flex items-center gap-2">
                  {showScore && (
                    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${
                      getRelevanceColor(citation.relevance_score)
                    }`}>
                      {formatRelevanceScore(citation.relevance_score)} relevant
                    </span>
                  )}
                  {citation.page_number && (
                    <span className="flex items-center gap-1">
                      📖 Page {citation.page_number}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    📍 Section {citation.chunk_index + 1}
                  </span>
                  <span className="text-blue-600">#{index + 1}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-1">
            <a
              href={downloadUrl(engagementId, citation.document_id)}
              target="_blank"
              rel="noopener noreferrer"
              className="px-2 py-1 text-xs bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition-colors"
              title="Open document"
            >
              📄 View
            </a>
            <button
              onClick={handleCopyLink}
              className="px-2 py-1 text-xs bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition-colors"
              title="Copy document link"
            >
              🔗 Copy
            </button>
            {onToggleExpand && (
              <button
                onClick={onToggleExpand}
                className="px-2 py-1 text-xs bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition-colors"
                title={isExpanded ? "Collapse details" : "Expand details"}
              >
                {isExpanded ? '▲' : '▼'}
              </button>
            )}
          </div>
        </div>

        {/* Citation Excerpt */}
        <div className="relative">
          <div className="text-sm text-gray-700 italic border-l-3 border-blue-200 pl-3">
            <div className="flex items-start gap-2">
              <span className="text-blue-400 text-lg leading-none">"</span>
              <span className="flex-1">
                {citation.excerpt}
              </span>
              <span className="text-blue-400 text-lg leading-none">"</span>
            </div>
          </div>
        </div>

        {/* Expanded Details */}
        {isExpanded && (
          <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
            {/* Metadata */}
            {citation.metadata && Object.keys(citation.metadata).length > 0 && (
              <div>
                <div className="text-xs font-medium text-gray-600 mb-1">Document Metadata</div>
                <div className="text-xs space-y-1">
                  {Object.entries(citation.metadata).map(([key, value]) => (
                    <div key={key} className="flex">
                      <span className="w-20 text-gray-500 capitalize">{key}:</span>
                      <span className="text-gray-700 flex-1">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Additional Context */}
            <div className="text-xs text-gray-500 space-y-1">
              <div>• This excerpt was automatically extracted and ranked for relevance</div>
              <div>• Citation accuracy depends on document quality and content structure</div>
              {citation.url && (
                <div>• Source URL: <a href={citation.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{citation.url}</a></div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CitationsList({ 
  citations, 
  engagementId, 
  className = "",
  maxVisible = 5,
  showScore = true,
  allowExpansion = true
}: CitationsListProps) {
  const [showAll, setShowAll] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());

  const visibleCitations = showAll ? citations : citations.slice(0, maxVisible);
  const hasMore = citations.length > maxVisible;

  function toggleExpanded(index: number) {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedItems(newExpanded);
  }

  async function exportCitations() {
    const exportData = {
      timestamp: new Date().toISOString(),
      engagement_id: engagementId,
      total_citations: citations.length,
      citations: citations.map((citation, index) => ({
        citation_number: index + 1,
        document_name: citation.document_name,
        relevance_score: citation.relevance_score,
        page_number: citation.page_number,
        section: citation.chunk_index + 1,
        excerpt: citation.excerpt,
        document_url: downloadUrl(engagementId, citation.document_id),
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
  }

  if (citations.length === 0) {
    return null;
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="font-medium text-sm text-gray-900">
            Supporting Evidence
          </div>
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
            {citations.length} source{citations.length !== 1 ? 's' : ''}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {citations.length > 0 && (
            <button
              onClick={exportCitations}
              className="text-xs text-blue-600 hover:text-blue-700 border border-blue-200 hover:border-blue-300 px-2 py-1 rounded transition-colors"
            >
              📊 Export
            </button>
          )}
          {allowExpansion && expandedItems.size > 0 && (
            <button
              onClick={() => setExpandedItems(new Set())}
              className="text-xs text-gray-600 hover:text-gray-700"
            >
              Collapse All
            </button>
          )}
        </div>
      </div>

      {/* Citations List */}
      <div className="space-y-2">
        {visibleCitations.map((citation, index) => (
          <CitationItem
            key={`${citation.document_id}-${citation.chunk_index}`}
            citation={citation}
            engagementId={engagementId}
            index={index}
            showScore={showScore}
            isExpanded={allowExpansion && expandedItems.has(index)}
            onToggleExpand={allowExpansion ? () => toggleExpanded(index) : undefined}
          />
        ))}
      </div>

      {/* Show More Button */}
      {hasMore && (
        <div className="text-center">
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-sm text-blue-600 hover:text-blue-700 border border-blue-200 hover:border-blue-300 px-3 py-1 rounded transition-colors"
          >
            {showAll ? (
              <>Show Less ({maxVisible} of {citations.length})</>
            ) : (
              <>Show All Citations ({citations.length})</>
            )}
          </button>
        </div>
      )}

      {/* Quality Indicator */}
      <div className="text-xs text-gray-500 pt-2 border-t border-gray-100">
        <div className="flex items-center justify-between">
          <span>
            Average relevance: {((citations.reduce((sum, c) => sum + c.relevance_score, 0) / citations.length) * 100).toFixed(1)}%
          </span>
          <span>
            Quality: {citations.filter(c => c.relevance_score >= 0.7).length}/{citations.length} high-confidence
          </span>
        </div>
      </div>
    </div>
  );
}