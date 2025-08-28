"use client";
import React, { useState, useCallback } from "react";
import type { Citation } from "../types/csf";
import type { Evidence } from "../types/evidence";

interface CitationCardProps {
  citation: Citation;
  evidence?: Evidence;
  onViewInContext?: (citation: Citation, evidence?: Evidence) => void;
  onCitationCopy?: (citation: Citation, evidence?: Evidence) => void;
  className?: string;
  correlationId?: string;
}

interface CopyToast {
  visible: boolean;
  message: string;
}

export default function CitationCard({
  citation,
  evidence,
  onViewInContext,
  onCitationCopy,
  className = "",
  correlationId
}: CitationCardProps) {
  const [copyToast, setCopyToast] = useState<CopyToast>({ visible: false, message: "" });

  const handleViewInContext = useCallback(() => {
    console.log(`[${correlationId}] View in context requested for citation: ${citation.document_id}:${citation.chunk_index}`);
    onViewInContext?.(citation, evidence);
  }, [citation, evidence, onViewInContext, correlationId]);

  const handleCopyCitation = useCallback(async () => {
    try {
      console.log(`[${correlationId}] Copy citation requested for: ${citation.document_id}:${citation.chunk_index}`);
      
      // Format citation in different styles
      const citationFormats = {
        apa: `"${citation.excerpt}" (${citation.document_name}${citation.page_number ? `, p. ${citation.page_number}` : ''}).`,
        mla: `"${citation.excerpt}" (${citation.document_name}${citation.page_number ? ` ${citation.page_number}` : ''}).`,
        chicago: `"${citation.excerpt}," ${citation.document_name}${citation.page_number ? `, ${citation.page_number}` : ''}.`,
        simple: `"${citation.excerpt}" - ${citation.document_name}${citation.page_number ? `, page ${citation.page_number}` : ''}`,
        markdown: `> ${citation.excerpt}\n\n*Source: ${citation.document_name}${citation.page_number ? `, page ${citation.page_number}` : ''}*`,
        json: JSON.stringify({
          excerpt: citation.excerpt,
          document: citation.document_name,
          page: citation.page_number,
          relevance: citation.relevance_score,
          chunk: citation.chunk_index,
          url: citation.url
        }, null, 2)
      };

      // Default to simple format, but could be configurable
      const formattedCitation = citationFormats.simple;
      
      await navigator.clipboard.writeText(formattedCitation);
      
      setCopyToast({ 
        visible: true, 
        message: "Citation copied to clipboard" 
      });
      
      // Hide toast after 2 seconds
      setTimeout(() => {
        setCopyToast({ visible: false, message: "" });
      }, 2000);
      
      onCitationCopy?.(citation, evidence);
      console.log(`[${correlationId}] Citation copied successfully`);
    } catch (error) {
      console.error(`[${correlationId}] Failed to copy citation:`, error);
      setCopyToast({ 
        visible: true, 
        message: "Failed to copy citation" 
      });
      
      setTimeout(() => {
        setCopyToast({ visible: false, message: "" });
      }, 2000);
    }
  }, [citation, evidence, onCitationCopy, correlationId]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleViewInContext();
    }
  }, [handleViewInContext]);

  return (
    <div className={`relative bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow ${className}`}>
      {/* Copy Success Toast */}
      {copyToast.visible && (
        <div 
          className="absolute top-2 right-2 px-3 py-1 bg-green-600 text-white text-xs rounded shadow-lg z-10"
          role="alert"
          aria-live="polite"
        >
          {copyToast.message}
        </div>
      )}

      <div className="p-4">
        {/* Header with document info */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h4 className="text-sm font-medium text-gray-900 truncate">
              {citation.document_name}
            </h4>
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
              {citation.page_number && (
                <span>Page {citation.page_number}</span>
              )}
              <span>Relevance: {(citation.relevance_score * 100).toFixed(0)}%</span>
              <span>Chunk {citation.chunk_index}</span>
            </div>
          </div>
          
          {/* Action buttons */}
          <div className="flex items-center gap-1 ml-3">
            <button
              onClick={handleCopyCitation}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
              title="Copy citation"
              aria-label="Copy citation to clipboard"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
            
            {onViewInContext && (
              <button
                onClick={handleViewInContext}
                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                title="View in context"
                aria-label="View citation in document context"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Citation excerpt */}
        <div 
          className="cursor-pointer"
          onClick={handleViewInContext}
          onKeyDown={handleKeyDown}
          tabIndex={onViewInContext ? 0 : -1}
          role={onViewInContext ? "button" : undefined}
          aria-label={onViewInContext ? "Click to view citation in context" : undefined}
        >
          <blockquote className="text-sm text-gray-700 italic border-l-4 border-blue-200 pl-3 mb-3">
            "{citation.excerpt}"
          </blockquote>
        </div>

        {/* Metadata */}
        {citation.metadata && Object.keys(citation.metadata).length > 0 && (
          <div className="border-t border-gray-100 pt-3">
            <div className="text-xs text-gray-500">
              <span className="font-medium">Metadata:</span>
              {Object.entries(citation.metadata).map(([key, value]) => (
                <span key={key} className="ml-2">
                  {key}: {String(value)}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* URL if available */}
        {citation.url && (
          <div className="border-t border-gray-100 pt-3 mt-3">
            <a
              href={citation.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:text-blue-800 underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
            >
              View original source ↗
            </a>
          </div>
        )}
      </div>

      {/* Hover actions overlay */}
      <div className="absolute inset-0 bg-blue-50 opacity-0 hover:opacity-5 transition-opacity rounded-lg pointer-events-none" />
    </div>
  );
}