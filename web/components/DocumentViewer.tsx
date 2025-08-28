"use client";
import React, { useState, useEffect, useRef, useCallback } from "react";
import type { Citation } from "../types/csf";
import type { Evidence } from "../types/evidence";

interface DocumentViewerProps {
  evidence: Evidence | null;
  citation?: Citation | null;
  isOpen: boolean;
  onClose: () => void;
  correlationId?: string;
}

interface HighlightRange {
  start: number;
  end: number;
  id: string;
}

export default function DocumentViewer({
  evidence,
  citation,
  isOpen,
  onClose,
  correlationId
}: DocumentViewerProps) {
  const [documentContent, setDocumentContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [highlightedText, setHighlightedText] = useState<HighlightRange[]>([]);
  
  const contentRef = useRef<HTMLDivElement>(null);
  const highlightRef = useRef<HTMLSpanElement>(null);

  // Load document content
  const loadDocumentContent = useCallback(async () => {
    if (!evidence) return;

    setLoading(true);
    setError(null);
    
    try {
      console.log(`[${correlationId}] Loading document content for: ${evidence.filename}`);
      
      // Mock document content loading - in real implementation, this would fetch from API
      // For now, we'll simulate document content with the citation excerpt
      const mockContent = `
Document: ${evidence.filename}

${citation?.excerpt || "Document content would be loaded here..."}

This is a mock document viewer that demonstrates the "View in context" functionality.
In a production environment, this would display the actual document content with 
proper highlighting of the relevant excerpts and citations.

The document would be rendered with appropriate formatting and navigation controls
to allow users to browse through the document and see highlighted relevant sections.
      `.trim();
      
      setDocumentContent(mockContent);
      
      // If we have a citation, create highlight range
      if (citation?.excerpt) {
        const startIndex = mockContent.indexOf(citation.excerpt);
        if (startIndex !== -1) {
          setHighlightedText([{
            start: startIndex,
            end: startIndex + citation.excerpt.length,
            id: `highlight-${citation.chunk_index}`
          }]);
        }
      }
      
      console.log(`[${correlationId}] Document content loaded successfully`);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load document content';
      console.error(`[${correlationId}] Document loading error:`, err);
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [evidence, citation, correlationId]);

  useEffect(() => {
    if (isOpen && evidence) {
      loadDocumentContent();
    }
  }, [isOpen, evidence, loadDocumentContent]);

  // Scroll to highlighted text when content loads
  useEffect(() => {
    if (highlightedText.length > 0 && highlightRef.current) {
      setTimeout(() => {
        highlightRef.current?.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'center' 
        });
      }, 100);
    }
  }, [highlightedText]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!isOpen) return;

      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const handleCopyCitation = useCallback(() => {
    if (!citation || !evidence) return;

    const citationText = `"${citation.excerpt}" - ${evidence.filename}${citation.page_number ? `, page ${citation.page_number}` : ''}`;
    
    navigator.clipboard.writeText(citationText).then(() => {
      console.log(`[${correlationId}] Citation copied to clipboard`);
      // You could add a toast notification here
    }).catch(err => {
      console.error(`[${correlationId}] Failed to copy citation:`, err);
    });
  }, [citation, evidence, correlationId]);

  const renderDocumentContent = () => {
    if (!documentContent) return null;

    if (highlightedText.length === 0) {
      return <div className="whitespace-pre-wrap text-gray-800">{documentContent}</div>;
    }

    // Split content and highlight relevant sections
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;

    highlightedText.forEach((highlight, index) => {
      // Add text before highlight
      if (highlight.start > lastIndex) {
        parts.push(
          <span key={`before-${index}`}>
            {documentContent.slice(lastIndex, highlight.start)}
          </span>
        );
      }

      // Add highlighted text
      parts.push(
        <span
          key={`highlight-${index}`}
          ref={index === 0 ? highlightRef : undefined}
          className="bg-yellow-200 border border-yellow-400 rounded px-1 py-0.5 font-medium"
          id={highlight.id}
        >
          {documentContent.slice(highlight.start, highlight.end)}
        </span>
      );

      lastIndex = highlight.end;
    });

    // Add remaining text
    if (lastIndex < documentContent.length) {
      parts.push(
        <span key="after">
          {documentContent.slice(lastIndex)}
        </span>
      );
    }

    return <div className="whitespace-pre-wrap text-gray-800">{parts}</div>;
  };

  if (!isOpen || !evidence) {
    return null;
  }

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="document-viewer-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div 
        className="w-full max-w-4xl h-full max-h-[90vh] bg-white rounded-lg shadow-xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="border-b border-gray-200 p-4 flex items-center justify-between">
          <div className="flex-1">
            <h2 id="document-viewer-title" className="text-xl font-semibold text-gray-900">
              {evidence.filename}
            </h2>
            {citation && (
              <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                {citation.page_number && (
                  <span>Page {citation.page_number}</span>
                )}
                <span>Relevance: {(citation.relevance_score * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {citation && (
              <button
                onClick={handleCopyCitation}
                className="px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="Copy citation"
              >
                Copy Citation
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Close document viewer"
            >
              <span className="text-xl">×</span>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex items-center justify-center py-12" role="status" aria-live="polite">
              <div className="flex items-center gap-3">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                <span className="text-gray-600">Loading document...</span>
              </div>
            </div>
          )}

          {error && (
            <div className="p-4" role="alert" aria-live="assertive">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-red-800">
                  <span role="img" aria-label="Error">⚠️</span>
                  <span className="font-medium">Failed to load document</span>
                </div>
                <p className="text-red-600 text-sm mt-1">{error}</p>
                <button 
                  onClick={loadDocumentContent}
                  className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {!loading && !error && (
            <div ref={contentRef} className="max-w-none">
              {citation && (
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h3 className="text-sm font-medium text-blue-800 mb-2">
                    Highlighted Citation
                  </h3>
                  <p className="text-sm text-blue-700">
                    The relevant excerpt is highlighted in yellow below. Use the scroll position to navigate to the highlighted content.
                  </p>
                </div>
              )}
              
              <div className="prose prose-sm max-w-none">
                {renderDocumentContent()}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <div>
              Document Size: {(evidence.size / 1024).toFixed(1)} KB • 
              Type: {evidence.mime_type}
            </div>
            <div className="flex items-center gap-4">
              <span>Press Escape to close</span>
              {citation && (
                <span>Citation chunk: {citation.chunk_index}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}