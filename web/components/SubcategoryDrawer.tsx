"use client";
import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { FixedSizeList as List } from "react-window";
import type { CSFSubcategory, Citation } from "@/types/csf";
import type { Evidence } from "@/types/evidence";
import { listEvidence } from "@/lib/evidence";
import { useParams } from "next/navigation";

interface SubcategoryDrawerProps {
  subcategory: CSFSubcategory | null;
  isOpen: boolean;
  onClose: () => void;
  onScoreChange?: (score: number) => void;
  onRationaleChange?: (rationale: string) => void;
  onEvidenceSelect?: (evidence: Evidence) => void;
  correlationId?: string;
}

interface EvidenceRowProps {
  index: number;
  style: React.CSSProperties;
  data: Evidence[];
}

const EvidenceRow: React.FC<EvidenceRowProps> = ({ index, style, data }) => {
  const evidence = data[index];
  
  return (
    <div style={style} className="px-4 py-2 border-b border-gray-100 hover:bg-blue-50 cursor-pointer">
      <div className="flex items-start gap-3">
        <span className="text-sm mt-1">📄</span>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">
            {evidence.filename}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Uploaded {new Date(evidence.uploaded_at).toLocaleDateString()}
          </div>
          {evidence.linked_items.length > 0 && (
            <div className="flex gap-1 mt-1">
              {evidence.linked_items.map((link, idx) => (
                <span 
                  key={idx} 
                  className="inline-flex items-center px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded"
                >
                  {link.item_type}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default function SubcategoryDrawer({
  subcategory,
  isOpen,
  onClose,
  onScoreChange,
  onRationaleChange,
  onEvidenceSelect,
  correlationId
}: SubcategoryDrawerProps) {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [score, setScore] = useState<number>(0);
  const [rationale, setRationale] = useState<string>("");
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"assessment" | "evidence">("assessment");
  
  const drawerRef = useRef<HTMLDivElement>(null);
  const scoreInputRef = useRef<HTMLInputElement>(null);
  const rationaleTextareaRef = useRef<HTMLTextAreaElement>(null);
  const evidenceListRef = useRef<HTMLDivElement>(null);

  // Load evidence for this engagement
  const loadEvidence = useCallback(async () => {
    if (!engagementId || !isOpen) return;
    
    setEvidenceLoading(true);
    setEvidenceError(null);
    
    try {
      console.log(`[${correlationId}] Loading evidence for engagement: ${engagementId}`);
      const response = await listEvidence(engagementId, 1, 100);
      setEvidenceList(response.data);
      console.log(`[${correlationId}] Loaded ${response.data.length} evidence items`);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to load evidence';
      console.error(`[${correlationId}] Evidence loading error:`, error);
      setEvidenceError(errorMsg);
    } finally {
      setEvidenceLoading(false);
    }
  }, [engagementId, isOpen, correlationId]);

  useEffect(() => {
    loadEvidence();
  }, [loadEvidence]);

  // Reset form when subcategory changes
  useEffect(() => {
    if (subcategory) {
      console.log(`[${correlationId}] Opening drawer for subcategory: ${subcategory.id}`);
      setScore(0);
      setRationale("");
      setActiveTab("assessment");
    }
  }, [subcategory, correlationId]);

  // Focus management for accessibility
  useEffect(() => {
    if (isOpen && scoreInputRef.current) {
      scoreInputRef.current.focus();
    }
  }, [isOpen]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!isOpen) return;

      switch (event.key) {
        case "Escape":
          event.preventDefault();
          onClose();
          break;
        case "Tab":
          // Handle tab navigation within drawer
          if (event.shiftKey) {
            // Shift+Tab logic can be enhanced for complex navigation
          }
          break;
        case "1":
        case "2":
        case "3":
        case "4":
        case "5":
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault();
            const scoreValue = parseInt(event.key);
            handleScoreChange(scoreValue);
          }
          break;
        case "ArrowUp":
        case "ArrowDown":
          if (activeTab === "evidence" && evidenceList.length > 0) {
            event.preventDefault();
            // Enhanced keyboard navigation for evidence list
          }
          break;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, activeTab, evidenceList.length, onClose]);

  const handleScoreChange = (newScore: number) => {
    console.log(`[${correlationId}] Score changed to: ${newScore} for subcategory: ${subcategory?.id}`);
    setScore(newScore);
    onScoreChange?.(newScore);
  };

  const handleRationaleChange = (newRationale: string) => {
    setRationale(newRationale);
    onRationaleChange?.(newRationale);
  };

  const handleEvidenceSelect = (evidence: Evidence) => {
    console.log(`[${correlationId}] Evidence selected: ${evidence.id} (${evidence.filename})`);
    onEvidenceSelect?.(evidence);
  };

  // Memoized evidence list for performance
  const memoizedEvidenceList = useMemo(() => evidenceList, [evidenceList]);

  const renderEvidenceContent = () => {
    if (evidenceLoading) {
      return (
        <div className="flex items-center justify-center py-8" role="status" aria-live="polite">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
            <span className="text-gray-600">Loading evidence...</span>
          </div>
        </div>
      );
    }

    if (evidenceError) {
      return (
        <div className="p-4" role="alert" aria-live="assertive">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center gap-2 text-red-800">
              <span role="img" aria-label="Error">⚠️</span>
              <span className="font-medium">Failed to load evidence</span>
            </div>
            <p className="text-red-600 text-sm mt-1">{evidenceError}</p>
            <button 
              onClick={loadEvidence}
              className="mt-2 px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }

    if (memoizedEvidenceList.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-12" role="status">
          <div className="text-4xl mb-4" role="img" aria-label="Empty folder">📂</div>
          <div className="text-gray-600 mb-2">No evidence files found</div>
          <div className="text-sm text-gray-500">Upload files to link them to this subcategory</div>
        </div>
      );
    }

    // Use react-window for virtualization with large evidence lists
    return (
      <div className="h-96" ref={evidenceListRef}>
        <List
          height={384}
          itemCount={memoizedEvidenceList.length}
          itemSize={80}
          itemData={memoizedEvidenceList}
          role="listbox"
          aria-label="Evidence files"
        >
          {EvidenceRow}
        </List>
      </div>
    );
  };

  if (!isOpen || !subcategory) {
    return null;
  }

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-end"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div 
        ref={drawerRef}
        className="w-full max-w-2xl h-full bg-white shadow-xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h2 id="drawer-title" className="text-xl font-semibold text-gray-900">
                {subcategory.id}
              </h2>
              <h3 className="text-lg text-gray-700 mt-1">{subcategory.title}</h3>
              <p className="text-sm text-gray-600 mt-2">{subcategory.description}</p>
            </div>
            <button
              onClick={onClose}
              className="ml-4 p-2 hover:bg-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Close drawer"
            >
              <span className="text-xl">×</span>
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200">
          <nav className="flex" role="tablist">
            <button
              role="tab"
              aria-selected={activeTab === "assessment"}
              aria-controls="assessment-panel"
              className={`px-6 py-3 text-sm font-medium border-b-2 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                activeTab === "assessment"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
              onClick={() => setActiveTab("assessment")}
            >
              Assessment
            </button>
            <button
              role="tab"
              aria-selected={activeTab === "evidence"}
              aria-controls="evidence-panel"
              className={`px-6 py-3 text-sm font-medium border-b-2 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                activeTab === "evidence"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
              onClick={() => setActiveTab("evidence")}
            >
              Evidence ({memoizedEvidenceList.length})
            </button>
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === "assessment" && (
            <div id="assessment-panel" role="tabpanel" className="p-6 space-y-6">
              {/* Score Section */}
              <div>
                <label htmlFor="score-input" className="block text-sm font-medium text-gray-700 mb-2">
                  Implementation Score (1-5)
                </label>
                <div className="flex gap-2 mb-3">
                  {[1, 2, 3, 4, 5].map((value) => (
                    <button
                      key={value}
                      onClick={() => handleScoreChange(value)}
                      className={`px-4 py-2 text-sm rounded border focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                        score === value
                          ? "bg-blue-600 text-white border-blue-600"
                          : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                      }`}
                      aria-pressed={score === value}
                    >
                      {value}
                    </button>
                  ))}
                </div>
                <input
                  ref={scoreInputRef}
                  id="score-input"
                  type="range"
                  min="0"
                  max="5"
                  step="1"
                  value={score}
                  onChange={(e) => handleScoreChange(parseInt(e.target.value))}
                  className="w-full"
                  aria-describedby="score-help"
                />
                <div id="score-help" className="text-xs text-gray-500 mt-1">
                  Use Ctrl/Cmd + 1-5 for quick scoring
                </div>
              </div>

              {/* Rationale Section */}
              <div>
                <label htmlFor="rationale-textarea" className="block text-sm font-medium text-gray-700 mb-2">
                  Assessment Rationale
                </label>
                <textarea
                  ref={rationaleTextareaRef}
                  id="rationale-textarea"
                  value={rationale}
                  onChange={(e) => handleRationaleChange(e.target.value)}
                  rows={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Explain the reasoning behind your assessment score..."
                  aria-describedby="rationale-help"
                />
                <div id="rationale-help" className="text-xs text-gray-500 mt-1">
                  Provide detailed justification for the score assigned
                </div>
              </div>
            </div>
          )}

          {activeTab === "evidence" && (
            <div id="evidence-panel" role="tabpanel">
              {renderEvidenceContent()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}