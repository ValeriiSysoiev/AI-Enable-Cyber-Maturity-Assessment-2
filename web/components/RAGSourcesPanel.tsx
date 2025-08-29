"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import EnhancedEvidenceSearch from "./EnhancedEvidenceSearch";
import CitationsList from "./CitationsList";
import RAGStatusPanel from "./RAGStatusPanel";
import { useRAGAvailability } from "./RAGToggle";
import type { SearchResult } from "../types/evidence";
import type { Citation } from "../types/evidence";

interface RAGSourcesPanelProps {
  className?: string;
  defaultQuery?: string;
  onSourceSelect?: (source: SearchResult | Citation) => void;
  showSearchHistory?: boolean;
  maxSearchResults?: number;
  maxCitations?: number;
  compactMode?: boolean;
}

interface AnalysisSession {
  id: string;
  timestamp: Date;
  query: string;
  results: SearchResult[];
  citations: Citation[];
  evidenceUsed: boolean;
  searchBackend?: string;
  evidenceSummary?: string;
}

interface SearchResponse {
  evidence_used?: boolean;
  search_backend?: string;
  evidence_summary?: string;
}

export default function RAGSourcesPanel({
  className = "",
  defaultQuery = "",
  onSourceSelect,
  showSearchHistory = true,
  maxSearchResults = 10,
  maxCitations = 5,
  compactMode = false
}: RAGSourcesPanelProps) {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [activeTab, setActiveTab] = useState<'search' | 'citations' | 'status'>('search');
  const [savedCitations, setSavedCitations] = useState<Citation[]>([]);
  const [analysisHistory, setAnalysisHistory] = useState<AnalysisSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const { isAvailable: ragAvailable, status: ragStatus } = useRAGAvailability();

  // Load saved citations and analysis history from localStorage
  useEffect(() => {
    if (!engagementId) return;

    // Load saved citations
    const savedCitationsKey = `rag-citations-${engagementId}`;
    const stored = localStorage.getItem(savedCitationsKey);
    if (stored) {
      try {
        setSavedCitations(JSON.parse(stored));
      } catch (e) {
        console.warn("Failed to load saved citations:", e);
      }
    }

    // Load analysis history
    const historyKey = `rag-analysis-history-${engagementId}`;
    const historyStored = localStorage.getItem(historyKey);
    if (historyStored) {
      try {
        const parsed = JSON.parse(historyStored);
        const sessions = parsed.map((s: Omit<AnalysisSession, 'timestamp'> & { timestamp: string }) => ({
          ...s,
          timestamp: new Date(s.timestamp)
        }));
        setAnalysisHistory(sessions);
      } catch (e) {
        console.warn("Failed to load analysis history:", e);
      }
    }
  }, [engagementId]);

  // Save citations to localStorage
  const saveCitations = (citations: Citation[]) => {
    if (!engagementId) return;
    
    const savedCitationsKey = `rag-citations-${engagementId}`;
    localStorage.setItem(savedCitationsKey, JSON.stringify(citations));
    setSavedCitations(citations);
  };

  // Add new analysis session to history
  const addAnalysisSession = (query: string, results: SearchResult[], options?: {
    evidenceUsed?: boolean;
    searchBackend?: string;
    evidenceSummary?: string;
  }) => {
    if (!engagementId || !query.trim()) return;

    const session: AnalysisSession = {
      id: Date.now().toString(),
      timestamp: new Date(),
      query: query.trim(),
      results,
      citations: convertResultsToCitations(results),
      evidenceUsed: options?.evidenceUsed || false,
      searchBackend: options?.searchBackend,
      evidenceSummary: options?.evidenceSummary
    };

    const updated = [session, ...analysisHistory].slice(0, 20); // Keep last 20 sessions
    setAnalysisHistory(updated);

    // Save to localStorage
    const historyKey = `rag-analysis-history-${engagementId}`;
    localStorage.setItem(historyKey, JSON.stringify(updated));

    // Auto-save citations from this session
    if (results.length > 0) {
      const citations = convertResultsToCitations(results);
      saveCitations([...citations, ...savedCitations].slice(0, 50)); // Keep max 50 citations
    }
  };

  // Convert search results to citations format
  const convertResultsToCitations = (results: SearchResult[]): Citation[] => {
    return results.map(result => ({
      document_id: result.document_id,
      document_name: result.document_name,
      excerpt: result.content,
      relevance_score: result.score,
      page_number: result.page_number,
      chunk_index: result.chunk_index,
      metadata: {
        source: 'rag_search',
        backend: 'enhanced_search'
      },
      url: result.url
    }));
  };

  const handleSearchResults = (results: SearchResult[], query: string, response?: SearchResponse) => {
    addAnalysisSession(query, results, {
      evidenceUsed: response?.evidence_used,
      searchBackend: response?.search_backend,
      evidenceSummary: response?.evidence_summary
    });
  };

  const handleSourceSelect = (source: SearchResult | Citation) => {
    if (onSourceSelect) {
      onSourceSelect(source);
    }
  };

  const clearCitations = () => {
    if (!engagementId) return;
    setSavedCitations([]);
    localStorage.removeItem(`rag-citations-${engagementId}`);
  };

  const clearHistory = () => {
    if (!engagementId) return;
    setAnalysisHistory([]);
    setSelectedSession(null);
    localStorage.removeItem(`rag-analysis-history-${engagementId}`);
  };

  const loadSessionCitations = (sessionId: string) => {
    const session = analysisHistory.find(s => s.id === sessionId);
    if (session) {
      setSavedCitations(session.citations);
      setSelectedSession(sessionId);
      setActiveTab('citations');
    }
  };

  const exportAllData = () => {
    if (!engagementId) return;

    const exportData = {
      engagement_id: engagementId,
      timestamp: new Date().toISOString(),
      rag_status: ragStatus,
      citations: savedCitations,
      analysis_sessions: analysisHistory.map(session => ({
        ...session,
        timestamp: session.timestamp.toISOString()
      })),
      statistics: {
        total_sessions: analysisHistory.length,
        total_citations: savedCitations.length,
        average_results_per_session: analysisHistory.length > 0 
          ? analysisHistory.reduce((sum, s) => sum + s.results.length, 0) / analysisHistory.length 
          : 0,
        backends_used: [...new Set(analysisHistory.map(s => s.searchBackend).filter(Boolean))]
      }
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { 
      type: "application/json" 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rag-sources-${engagementId}-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getTabCount = (tab: string) => {
    switch (tab) {
      case 'citations': return savedCitations.length;
      case 'search': return analysisHistory.length;
      default: return 0;
    }
  };

  const getTabIcon = (tab: string) => {
    switch (tab) {
      case 'search': return '🔍';
      case 'citations': return '📚';
      case 'status': return '📊';
      default: return '';
    }
  };

  return (
    <div className={`bg-white rounded-xl border ${compactMode ? 'p-3' : 'p-4'} ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className={`font-semibold ${compactMode ? 'text-base' : 'text-lg'} text-gray-900`}>
            RAG Sources
          </h3>
          {ragAvailable && (
            <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
              ✓ Active
            </span>
          )}
          {!ragAvailable && (
            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
              Inactive
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {(savedCitations.length > 0 || analysisHistory.length > 0) && (
            <button
              onClick={exportAllData}
              className="text-xs text-blue-600 hover:text-blue-700 border border-blue-200 hover:border-blue-300 px-2 py-1 rounded transition-colors"
            >
              📊 Export All
            </button>
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-1 mb-4 bg-gray-100 rounded-lg p-1">
        {[
          { id: 'search', label: 'Search' },
          { id: 'citations', label: 'Citations' },
          { id: 'status', label: 'Status' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <div className="flex items-center justify-center gap-1">
              <span>{getTabIcon(tab.id)}</span>
              <span>{tab.label}</span>
              {getTabCount(tab.id) > 0 && (
                <span className="ml-1 text-xs bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded-full">
                  {getTabCount(tab.id)}
                </span>
              )}
            </div>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="space-y-4">
        {/* Search Tab */}
        {activeTab === 'search' && (
          <div className="space-y-4">
            <EnhancedEvidenceSearch

              maxResults={maxSearchResults}
              showRAGToggle={true}
              enableAutoSuggestions={true}
              onResultSelect={handleSourceSelect}
              className="border-0 bg-transparent p-0"
            />

            {/* Analysis History */}
            {showSearchHistory && analysisHistory.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="font-medium text-sm">Recent Analysis</div>
                  <button
                    onClick={clearHistory}
                    className="text-xs text-gray-500 hover:text-gray-700"
                  >
                    Clear All
                  </button>
                </div>
                
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {analysisHistory.slice(0, 10).map(session => (
                    <div
                      key={session.id}
                      className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                        selectedSession === session.id 
                          ? 'border-blue-200 bg-blue-50' 
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                      onClick={() => loadSessionCitations(session.id)}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate">
                            {session.query}
                          </div>
                          <div className="text-xs text-gray-500 mt-1 flex items-center gap-2">
                            <span>{session.timestamp.toLocaleDateString()}</span>
                            <span>•</span>
                            <span>{session.results.length} results</span>
                            {session.searchBackend && (
                              <>
                                <span>•</span>
                                <span className="text-blue-600">{session.searchBackend}</span>
                              </>
                            )}
                          </div>
                          {session.evidenceSummary && (
                            <div className="text-xs text-gray-600 mt-1 italic">
                              {session.evidenceSummary}
                            </div>
                          )}
                        </div>
                        <div className="text-xs text-gray-400">
                          {session.results.length > 0 ? '📚' : '🔍'}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Citations Tab */}
        {activeTab === 'citations' && (
          <div className="space-y-4">
            {savedCitations.length > 0 ? (
              <>
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-600">
                    {selectedSession ? 'Session Citations' : 'Saved Citations'}
                  </div>
                  <div className="flex gap-2">
                    {selectedSession && (
                      <button
                        onClick={() => {
                          setSelectedSession(null);
                          // Reload all saved citations
                          const savedCitationsKey = `rag-citations-${engagementId}`;
                          const stored = localStorage.getItem(savedCitationsKey);
                          if (stored) {
                            try {
                              setSavedCitations(JSON.parse(stored));
                            } catch (e) {
                              setSavedCitations([]);
                            }
                          }
                        }}
                        className="text-xs text-blue-600 hover:text-blue-700"
                      >
                        ← Back to All
                      </button>
                    )}
                    <button
                      onClick={clearCitations}
                      className="text-xs text-gray-500 hover:text-gray-700"
                    >
                      Clear
                    </button>
                  </div>
                </div>
                
                <CitationsList
                  citations={savedCitations}
                  engagementId={engagementId!}
                  maxVisible={maxCitations}
                  showScore={true}
                  allowExpansion={!compactMode}
                />
              </>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <div className="text-sm">No citations saved yet</div>
                <div className="text-xs mt-2">
                  Perform searches to automatically save relevant sources
                </div>
              </div>
            )}
          </div>
        )}

        {/* Status Tab */}
        {activeTab === 'status' && (
          <div className="space-y-4">
            <RAGStatusPanel 
              className="border-0 bg-transparent p-0"

            />
            
            {analysisHistory.length > 0 && (
              <div className="space-y-3">
                <div className="font-medium text-sm">Usage Statistics</div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-lg font-semibold text-blue-600">
                      {analysisHistory.length}
                    </div>
                    <div className="text-xs text-gray-600">Search Sessions</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-lg font-semibold text-green-600">
                      {savedCitations.length}
                    </div>
                    <div className="text-xs text-gray-600">Sources Found</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-lg font-semibold text-purple-600">
                      {analysisHistory.filter(s => s.evidenceUsed).length}
                    </div>
                    <div className="text-xs text-gray-600">Enhanced Analysis</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-lg font-semibold text-orange-600">
                      {savedCitations.length > 0 
                        ? ((savedCitations.reduce((sum, c) => sum + c.relevance_score, 0) / savedCitations.length) * 100).toFixed(0)
                        : 0}%
                    </div>
                    <div className="text-xs text-gray-600">Avg Relevance</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}