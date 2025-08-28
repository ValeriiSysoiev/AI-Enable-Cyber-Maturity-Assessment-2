"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { searchEvidence } from "../lib/evidence";
import { downloadUrl } from "../lib/docs";
import type { SearchResult, EvidenceSearchResponse } from "../types/evidence";

interface EvidenceSearchProps {
  className?: string;
  onResultSelect?: (result: SearchResult) => void;
  maxResults?: number;
}

export default function EvidenceSearch({ 
  className = "", 
  onResultSelect,
  maxResults = 10 
}: EvidenceSearchProps) {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchResponse, setSearchResponse] = useState<EvidenceSearchResponse | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || !engagementId) return;

    try {
      setLoading(true);
      setError(null);
      
      const response = await searchEvidence({
        query: query.trim(),
        top_k: maxResults,
        score_threshold: 0.1,
        engagement_id: engagementId,
      });

      setResults(response.results);
      setSearchResponse(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
      setSearchResponse(null);
    } finally {
      setLoading(false);
    }
  }

  function handleResultClick(result: SearchResult) {
    if (onResultSelect) {
      onResultSelect(result);
    }
  }

  async function exportResults() {
    if (!results.length) return;
    
    const exportData = {
      query,
      timestamp: new Date().toISOString(),
      engagement_id: engagementId,
      results: results.map(r => ({
        content: r.content,
        score: r.score,
        document_name: r.document_name,
        page_number: r.page_number,
      }))
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { 
      type: "application/json" 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `evidence-search-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function highlightText(text: string, query: string): string {
    if (!query.trim()) return text;
    
    const terms = query.toLowerCase().split(/\s+/);
    let highlightedText = text;
    
    terms.forEach(term => {
      if (term.length > 2) { // Only highlight terms longer than 2 chars
        const regex = new RegExp(`(${term})`, 'gi');
        highlightedText = highlightedText.replace(regex, '<mark class="bg-yellow-200">$1</mark>');
      }
    });
    
    return highlightedText;
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="rounded-xl border p-4">
        <div className="font-medium mb-3">Evidence Search</div>
        
        <form onSubmit={handleSearch} className="space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for evidence in uploaded documents..."
              className="flex-1 px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </div>
          
          {searchResponse && (
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>
                Found {searchResponse.total_results} results in {searchResponse.processing_time_ms}ms
              </span>
              {results.length > 0 && (
                <button
                  type="button"
                  onClick={exportResults}
                  className="text-blue-600 hover:text-blue-700"
                >
                  Export Results
                </button>
              )}
            </div>
          )}
        </form>

        {error && (
          <div className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
            {error}
          </div>
        )}
      </div>

      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((result, index) => (
            <div
              key={index}
              className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
              onClick={() => handleResultClick(result)}
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-blue-700 truncate">
                    {result.document_name}
                  </div>
                  <div className="text-xs text-gray-500 space-x-2">
                    <span>Score: {(result.score * 100).toFixed(1)}%</span>
                    {result.page_number && <span>• Page {result.page_number}</span>}
                    <span>• Chunk {result.chunk_index + 1}</span>
                  </div>
                </div>
                <div className="flex gap-1">
                  <a
                    href={downloadUrl(engagementId!, result.document_id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                  >
                    View
                  </a>
                </div>
              </div>
              
              <div 
                className="text-sm text-gray-700 leading-relaxed"
                dangerouslySetInnerHTML={{ 
                  __html: highlightText(result.content, query) 
                }}
              />
            </div>
          ))}
        </div>
      )}

      {query && !loading && results.length === 0 && searchResponse && (
        <div className="text-center py-8 text-gray-500">
          <div className="text-sm">No evidence found for "{query}"</div>
          <div className="text-xs mt-1">Try different keywords or check if documents are indexed</div>
        </div>
      )}
    </div>
  );
}