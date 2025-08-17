"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { searchEvidence } from "@/lib/evidence";
import { downloadUrl } from "@/lib/docs";
import RAGToggle, { useRAGAvailability } from "./RAGToggle";
import CitationsList from "./CitationsList";
import type { SearchResult, EvidenceSearchResponse, RAGSearchResponse } from "@/types/evidence";

interface EnhancedEvidenceSearchProps {
  className?: string;
  onResultSelect?: (result: SearchResult) => void;
  maxResults?: number;
  showRAGToggle?: boolean;
  enableAutoSuggestions?: boolean;
}

export default function EnhancedEvidenceSearch({ 
  className = "", 
  onResultSelect,
  maxResults = 10,
  showRAGToggle = true,
  enableAutoSuggestions = true
}: EnhancedEvidenceSearchProps) {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [query, setQuery] = useState("");
  const [useRAG, setUseRAG] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [groundedAnswer, setGroundedAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchResponse, setSearchResponse] = useState<EvidenceSearchResponse | RAGSearchResponse | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  
  const searchInputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);
  const { isAvailable: ragAvailable } = useRAGAvailability();

  // Load search history from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(`search-history-${engagementId}`);
    if (saved) {
      try {
        setSearchHistory(JSON.parse(saved));
      } catch (e) {
        console.warn("Failed to load search history:", e);
      }
    }
  }, [engagementId]);

  // Save search history to localStorage
  const saveSearchHistory = useCallback((newQuery: string) => {
    if (!newQuery.trim() || !engagementId) return;
    
    const updated = [newQuery, ...searchHistory.filter(h => h !== newQuery)].slice(0, 10);
    setSearchHistory(updated);
    localStorage.setItem(`search-history-${engagementId}`, JSON.stringify(updated));
  }, [searchHistory, engagementId]);

  // Generate search suggestions
  const generateSuggestions = useCallback(async (searchQuery: string) => {
    if (!enableAutoSuggestions || !searchQuery.trim() || searchQuery.length < 3) {
      setSuggestions([]);
      return;
    }

    // Combine history-based and semantic suggestions
    const historySuggestions = searchHistory
      .filter(h => h.toLowerCase().includes(searchQuery.toLowerCase()) && h !== searchQuery)
      .slice(0, 3);

    // Add smart suggestions based on common cybersecurity terms
    const smartSuggestions = [
      `${searchQuery} policy`,
      `${searchQuery} implementation`,
      `${searchQuery} controls`,
      `${searchQuery} assessment`,
      `${searchQuery} framework`
    ].filter(s => !historySuggestions.some(h => h.toLowerCase() === s.toLowerCase()))
     .slice(0, 2);

    setSuggestions([...historySuggestions, ...smartSuggestions]);
  }, [searchHistory, enableAutoSuggestions]);

  // Debounced suggestions
  useEffect(() => {
    const timeout = setTimeout(() => {
      generateSuggestions(query);
    }, 300);
    return () => clearTimeout(timeout);
  }, [query, generateSuggestions]);

  // Handle clicking outside suggestions
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target as Node) &&
          searchInputRef.current && !searchInputRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  async function performSearch(searchQuery: string, useGrounding: boolean = false) {
    if (!searchQuery.trim() || !engagementId) return;

    try {
      setLoading(true);
      setError(null);
      setGroundedAnswer(null);
      
      let response;
      
      if (useGrounding && ragAvailable) {
        // Use RAG search endpoint
        const ragResponse = await fetch("/api/proxy/orchestrations/rag-search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: searchQuery.trim(),
            engagement_id: engagementId,
            top_k: maxResults,
            score_threshold: 0.1,
            use_grounding: true,
          }),
        });

        if (!ragResponse.ok) {
          throw new Error(`RAG search failed: ${ragResponse.status}`);
        }
        
        response = await ragResponse.json() as RAGSearchResponse;
        if ('grounded_answer' in response) {
          setGroundedAnswer(response.grounded_answer || null);
        }
      } else {
        // Use regular evidence search
        response = await searchEvidence({
          query: searchQuery.trim(),
          top_k: maxResults,
          score_threshold: 0.1,
          engagement_id: engagementId,
        });
      }

      setResults(response.results);
      setSearchResponse(response);
      saveSearchHistory(searchQuery.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
      setSearchResponse(null);
      setGroundedAnswer(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setShowSuggestions(false);
    await performSearch(query, useRAG);
  }

  function handleSuggestionClick(suggestion: string) {
    setQuery(suggestion);
    setShowSuggestions(false);
    performSearch(suggestion, useRAG);
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
      rag_enabled: useRAG,
      grounded_answer: groundedAnswer,
      processing_time_ms: searchResponse?.processing_time_ms,
      total_results: searchResponse?.total_results,
      results: results.map(r => ({
        content: r.content,
        score: r.score,
        document_name: r.document_name,
        page_number: r.page_number,
        chunk_index: r.chunk_index,
        document_url: downloadUrl(engagementId!, r.document_id)
      }))
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { 
      type: "application/json" 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `evidence-search-${useRAG ? 'rag-' : ''}${new Date().toISOString().split('T')[0]}.json`;
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
      if (term.length > 2) {
        const regex = new RegExp(`(${term})`, 'gi');
        highlightedText = highlightedText.replace(regex, '<mark class="bg-yellow-200 px-0.5 py-0.5 rounded">$1</mark>');
      }
    });
    
    return highlightedText;
  }

  function getSearchModeText() {
    if (useRAG && ragAvailable) {
      return "🔮 Grounded Search (RAG)";
    }
    return "🔍 Evidence Search";
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="rounded-xl border p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="font-medium">{getSearchModeText()}</div>
          {showRAGToggle && (
            <RAGToggle 
              enabled={useRAG}
              onToggle={setUseRAG}
              size="sm"
              className="text-sm"
            />
          )}
        </div>
        
        <form onSubmit={handleSearch} className="space-y-3">
          {/* Search Input with Suggestions */}
          <div className="relative">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  ref={searchInputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onFocus={() => setShowSuggestions(suggestions.length > 0)}
                  placeholder={useRAG && ragAvailable 
                    ? "Ask a question or search for evidence with AI assistance..." 
                    : "Search for evidence in uploaded documents..."
                  }
                  className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 pr-8"
                  disabled={loading}
                />
                {query && (
                  <button
                    type="button"
                    onClick={() => {
                      setQuery("");
                      setSuggestions([]);
                      setShowSuggestions(false);
                    }}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    ✕
                  </button>
                )}
              </div>
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed min-w-[100px]"
              >
                {loading ? "Searching..." : useRAG && ragAvailable ? "Ask AI" : "Search"}
              </button>
            </div>

            {/* Suggestions Dropdown */}
            {showSuggestions && suggestions.length > 0 && (
              <div 
                ref={suggestionsRef}
                className="absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-md mt-1 shadow-lg z-10 max-h-48 overflow-y-auto"
              >
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                  >
                    <span className="text-gray-600">🔍</span> {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Search Results Summary */}
          {searchResponse && (
            <div className="flex items-center justify-between text-xs text-gray-500">
              <div className="flex items-center gap-4">
                <span>
                  Found {searchResponse.total_results} results in {searchResponse.processing_time_ms}ms
                </span>
                {'sources_used' in searchResponse && (
                  <span className="text-green-600">
                    🔗 {searchResponse.sources_used} sources used
                  </span>
                )}
                {useRAG && ragAvailable && (
                  <span className="text-blue-600">
                    🤖 AI-Enhanced
                  </span>
                )}
              </div>
              {results.length > 0 && (
                <button
                  type="button"
                  onClick={exportResults}
                  className="text-blue-600 hover:text-blue-700 border border-blue-200 hover:border-blue-300 px-2 py-1 rounded"
                >
                  📊 Export
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

      {/* Grounded Answer (RAG) */}
      {groundedAnswer && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-blue-600">🤖</span>
            <span className="font-medium text-blue-900">AI Analysis</span>
            <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded">
              Evidence-Grounded
            </span>
          </div>
          <div className="text-sm text-blue-900 leading-relaxed">
            {groundedAnswer}
          </div>
        </div>
      )}

      {/* Search Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="font-medium text-sm">Search Results</div>
            <div className="text-xs text-gray-500">
              Sorted by relevance
            </div>
          </div>
          
          {results.map((result, index) => (
            <div
              key={`${result.document_id}-${result.chunk_index}`}
              className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
              onClick={() => handleResultClick(result)}
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-blue-700 truncate">
                    {result.document_name}
                  </div>
                  <div className="text-xs text-gray-500 flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded ${
                      result.score >= 0.8 ? 'bg-green-100 text-green-800' :
                      result.score >= 0.6 ? 'bg-blue-100 text-blue-800' :
                      result.score >= 0.4 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {(result.score * 100).toFixed(1)}% match
                    </span>
                    {result.page_number && <span>📖 Page {result.page_number}</span>}
                    <span>📍 Section {result.chunk_index + 1}</span>
                    <span className="text-blue-600">#{index + 1}</span>
                  </div>
                </div>
                <div className="flex gap-1">
                  <a
                    href={downloadUrl(engagementId!, result.document_id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
                  >
                    📄 View
                  </a>
                </div>
              </div>
              
              <div 
                className="text-sm text-gray-700 leading-relaxed border-l-2 border-gray-200 pl-3"
                dangerouslySetInnerHTML={{ 
                  __html: highlightText(result.content, query) 
                }}
              />
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {query && !loading && results.length === 0 && searchResponse && (
        <div className="text-center py-8 text-gray-500">
          <div className="text-sm">No evidence found for "{query}"</div>
          <div className="text-xs mt-2 space-y-1">
            <div>• Try different keywords or check if documents are indexed</div>
            {useRAG && ragAvailable && (
              <div>• Consider rephrasing as a question for better AI understanding</div>
            )}
            <div>• Ensure documents contain relevant content</div>
          </div>
        </div>
      )}

      {/* Search History */}
      {searchHistory.length > 0 && !query && (
        <div className="rounded-xl border p-4">
          <div className="font-medium text-sm mb-3">Recent Searches</div>
          <div className="flex flex-wrap gap-2">
            {searchHistory.slice(0, 5).map((historyQuery, index) => (
              <button
                key={index}
                onClick={() => {
                  setQuery(historyQuery);
                  performSearch(historyQuery, useRAG);
                }}
                className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-2 py-1 rounded transition-colors"
              >
                🔍 {historyQuery}
              </button>
            ))}
            {searchHistory.length > 5 && (
              <span className="text-xs text-gray-500 px-2 py-1">
                +{searchHistory.length - 5} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}