"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { analyzeWithEvidence, getCitations } from "@/lib/evidence";
import RAGToggle, { useRAGAvailability } from "./RAGToggle";
import CitationsList from "./CitationsList";
import type { Citation, RAGAnalysisResponse } from "@/types/evidence";

interface AnalysisWithEvidenceProps {
  initialContent?: string;
  onAnalysisComplete?: (result: any) => void;
  className?: string;
}

export default function AnalysisWithEvidence({ 
  initialContent = "",
  onAnalysisComplete,
  className = ""
}: AnalysisWithEvidenceProps) {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [content, setContent] = useState(initialContent);
  const [useEvidence, setUseEvidence] = useState(false);
  const [useRAG, setUseRAG] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RAGAnalysisResponse | null>(null);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { isAvailable: ragAvailable } = useRAGAvailability();

  async function handleAnalyze() {
    if (!content.trim() || !engagementId) return;

    try {
      setLoading(true);
      setError(null);
      setResult(null);
      setCitations([]);

      let analysisResult: RAGAnalysisResponse;

      if (useRAG && ragAvailable) {
        // Use enhanced RAG analysis
        const response = await fetch("/api/proxy/orchestrations/rag-analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            engagement_id: engagementId,
            content: content.trim(),
            use_evidence: useEvidence,
            use_rag: true,
            analysis_type: 'analyze'
          }),
        });

        if (!response.ok) {
          throw new Error(`RAG analysis failed: ${response.status}`);
        }
        
        analysisResult = await response.json();
      } else {
        // Use standard evidence analysis
        analysisResult = await analyzeWithEvidence(
          engagementId,
          content.trim(),
          useEvidence
        );
      }

      setResult(analysisResult);

      // Handle citations from analysis response or fetch them separately
      if (analysisResult.citations && analysisResult.citations.length > 0) {
        setCitations(analysisResult.citations);
      } else if ((useEvidence || useRAG) && analysisResult.id) {
        try {
          const citationsList = await getCitations(analysisResult.id);
          setCitations(citationsList);
        } catch (citationError) {
          console.warn("Failed to load citations:", citationError);
        }
      }

      if (onAnalysisComplete) {
        onAnalysisComplete(analysisResult);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  function formatAnalysisResult(result: any): string {
    if (typeof result === "string") return result;
    if (result.content) return result.content;
    if (result.analysis) return result.analysis;
    return JSON.stringify(result, null, 2);
  }

  function getAnalysisMode() {
    if (useRAG && ragAvailable) return "🤖 RAG-Enhanced Analysis";
    if (useEvidence) return "📚 Evidence-Based Analysis";
    return "🔍 Standard Analysis";
  }

  async function exportAnalysis() {
    if (!result) return;
    
    const exportData = {
      timestamp: new Date().toISOString(),
      engagement_id: engagementId,
      analysis_mode: {
        use_evidence: useEvidence,
        use_rag: useRAG,
        rag_available: ragAvailable
      },
      input_content: content,
      analysis_result: {
        content: formatAnalysisResult(result),
        confidence_score: result.confidence_score,
        evidence_used: result.evidence_used,
        rag_grounding: result.rag_grounding,
        grounded_insights: result.grounded_insights,
        processing_time_ms: result.processing_time_ms
      },
      citations: citations.map((citation, index) => ({
        citation_number: index + 1,
        document_name: citation.document_name,
        relevance_score: citation.relevance_score,
        page_number: citation.page_number,
        section: citation.chunk_index + 1,
        excerpt: citation.excerpt
      }))
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { 
      type: "application/json" 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `analysis-${useRAG ? 'rag-' : ''}${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="rounded-xl border p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="font-medium">{getAnalysisMode()}</div>
          <div className="flex items-center gap-2">
            {result && (
              <button
                onClick={exportAnalysis}
                className="text-xs text-blue-600 hover:text-blue-700 border border-blue-200 hover:border-blue-300 px-2 py-1 rounded"
              >
                📊 Export
              </button>
            )}
          </div>
        </div>
        
        <div className="space-y-4">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={useRAG && ragAvailable 
              ? "Ask a question or describe what you want to analyze..." 
              : "Enter content to analyze..."
            }
            className="w-full h-32 px-3 py-2 border rounded-md text-sm resize-vertical focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          
          <div className="space-y-3">
            {/* Analysis Options */}
            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={useEvidence}
                  onChange={(e) => setUseEvidence(e.target.checked)}
                  disabled={loading}
                  className="rounded"
                />
                <span>Use Evidence from Documents</span>
                <span className="text-xs text-gray-500">
                  (Search uploaded documents for relevant content)
                </span>
              </label>

              <RAGToggle 
                enabled={useRAG}
                onToggle={setUseRAG}
                disabled={loading}
                size="sm"
                className="ml-6"
              />
            </div>

            {/* Action Button */}
            <div className="flex justify-end">
              <button
                onClick={handleAnalyze}
                disabled={loading || !content.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed min-w-[120px]"
              >
                {loading ? "Analyzing..." : useRAG && ragAvailable ? "Analyze with AI" : "Analyze"}
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
            {error}
          </div>
        )}
      </div>

      {result && (
        <div className="rounded-xl border p-4 space-y-4">
          {/* Analysis Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="font-medium">Analysis Result</div>
              {result.confidence_score && (
                <span className={`text-xs px-2 py-0.5 rounded ${
                  result.confidence_score >= 0.8 ? 'bg-green-100 text-green-800' :
                  result.confidence_score >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {(result.confidence_score * 100).toFixed(0)}% confidence
                </span>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              {result.evidence_used && (
                <div className="flex items-center gap-1 text-xs text-green-700 bg-green-50 px-2 py-1 rounded">
                  <span>📚</span>
                  <span>Evidence Used</span>
                </div>
              )}
              {result.use_rag && ragAvailable && (
                <div className="flex items-center gap-1 text-xs text-blue-700 bg-blue-50 px-2 py-1 rounded">
                  <span>🤖</span>
                  <span>RAG Enhanced</span>
                </div>
              )}
            </div>
          </div>

          {/* RAG Grounding */}
          {result.rag_grounding && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="font-medium text-sm text-blue-900 mb-2">
                🤖 AI Grounding Summary
              </div>
              <div className="text-sm text-blue-800">
                {result.rag_grounding}
              </div>
            </div>
          )}
          
          {/* Main Analysis Content */}
          <div className="prose prose-sm max-w-none">
            <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">
              {formatAnalysisResult(result)}
            </div>
          </div>

          {/* Grounded Insights */}
          {result.grounded_insights && result.grounded_insights.length > 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <div className="font-medium text-sm text-green-900 mb-2">
                💡 Key Insights from Evidence
              </div>
              <ul className="text-sm text-green-800 space-y-1">
                {result.grounded_insights.map((insight, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-green-600 mt-0.5">•</span>
                    <span>{insight}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Citations */}
          {citations.length > 0 && (
            <CitationsList 
              citations={citations}
              engagementId={engagementId!}
              showScore={true}
              allowExpansion={true}
            />
          )}

          {/* Analysis Metadata */}
          <div className="text-xs text-gray-500 pt-2 border-t space-y-1">
            <div className="flex justify-between">
              <span>Analysis completed at {new Date().toLocaleString()}</span>
              {result.processing_time_ms && (
                <span>Processing time: {result.processing_time_ms}ms</span>
              )}
            </div>
            
            {(result.evidence_used || result.use_rag) && (
              <div className="flex justify-between">
                {citations.length > 0 && (
                  <span>Evidence sources: {citations.length}</span>
                )}
                {result.evidence_quality_score && (
                  <span>Evidence quality: {(result.evidence_quality_score * 100).toFixed(1)}%</span>
                )}
              </div>
            )}

            {result.recommendations_count && (
              <div>Recommendations generated: {result.recommendations_count}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}