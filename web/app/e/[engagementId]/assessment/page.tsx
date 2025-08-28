"use client";
import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import { getFunctions } from "../../../../lib/csf";
import { useRequireAuth } from "../../../../components/AuthProvider";
import SubcategoryDrawer from "../../../../components/SubcategoryDrawer";
import type { CSFFunction, CSFSubcategory, CSFAssessmentItem } from "../../../../types/csf";
import type { Evidence } from "../../../../types/evidence";

// CSF Grid Component
function CSFGrid({ 
  functions, 
  onSubcategorySelect, 
  selectedSubcategory 
}: {
  functions: CSFFunction[];
  onSubcategorySelect: (subcategory: CSFSubcategory) => void;
  selectedSubcategory: CSFSubcategory | null;
}) {
  const [expandedFunctions, setExpandedFunctions] = useState<Set<string>>(new Set());
  
  const toggleFunction = (functionId: string) => {
    setExpandedFunctions(prev => {
      const next = new Set(prev);
      if (next.has(functionId)) {
        next.delete(functionId);
      } else {
        next.add(functionId);
      }
      return next;
    });
  };

  return (
    <div className="space-y-4">
      {functions.map(func => (
        <div key={func.id} className="border rounded-lg">
          <button
            onClick={() => toggleFunction(func.id)}
            className="w-full px-4 py-3 text-left bg-gray-50 hover:bg-gray-100 rounded-t-lg font-medium flex items-center justify-between"
          >
            <div>
              <span className="font-semibold">{func.id}</span> - {func.title}
            </div>
            <span className="text-gray-500">
              {expandedFunctions.has(func.id) ? '−' : '+'}
            </span>
          </button>
          
          {expandedFunctions.has(func.id) && (
            <div className="p-4 space-y-3">
              <p className="text-sm text-gray-600 mb-4">{func.description}</p>
              
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {func.categories.map(category => (
                  <div key={category.id} className="border rounded-lg p-3 bg-white">
                    <div className="font-medium text-sm mb-2">
                      {category.id} - {category.title}
                    </div>
                    <p className="text-xs text-gray-600 mb-2">{category.description}</p>
                    
                    <div className="space-y-1">
                      {category.subcategories.map(subcategory => (
                        <button
                          key={subcategory.id}
                          onClick={() => onSubcategorySelect(subcategory)}
                          className={`w-full text-left px-2 py-1 rounded text-xs hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                            selectedSubcategory?.id === subcategory.id 
                              ? 'bg-blue-100 text-blue-700 font-medium' 
                              : 'text-gray-700'
                          }`}
                          aria-label={`Select subcategory ${subcategory.id}: ${subcategory.title}`}
                        >
                          {subcategory.id} - {subcategory.title}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// Details Panel Component
function DetailsPanel({ 
  subcategory 
}: { 
  subcategory: CSFSubcategory;
}) {
  return (
    <div className="bg-white border rounded-lg p-6 space-y-4">
      <div>
        <h3 className="font-semibold text-lg">{subcategory.id}</h3>
        <h4 className="text-gray-600 mb-2">{subcategory.title}</h4>
        <p className="text-sm text-gray-700">{subcategory.description}</p>
      </div>
      
      {/* Score Placeholder */}
      <div className="border-t pt-4">
        <h4 className="font-medium mb-2">Assessment Score</h4>
        <div className="bg-gray-50 p-3 rounded text-center text-gray-500">
          <div>Score: Not Assessed</div>
          <div className="text-xs mt-1">Scoring functionality coming soon</div>
        </div>
      </div>
      
      {/* Rationale Placeholder */}
      <div className="border-t pt-4">
        <h4 className="font-medium mb-2">Rationale</h4>
        <div className="bg-gray-50 p-3 rounded text-center text-gray-500">
          <div>No rationale provided</div>
          <div className="text-xs mt-1">Rationale input coming soon</div>
        </div>
      </div>
      
      {/* Evidence Placeholder */}
      <div className="border-t pt-4">
        <h4 className="font-medium mb-2">Evidence</h4>
        <div className="bg-gray-50 p-3 rounded text-center text-gray-500">
          <div>No evidence uploaded</div>
          <div className="text-xs mt-1">Evidence tray coming soon</div>
        </div>
      </div>
    </div>
  );
}

export default function AssessmentPage() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [functions, setFunctions] = useState<CSFFunction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSubcategory, setSelectedSubcategory] = useState<CSFSubcategory | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [correlationId] = useState(() => `csf-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
  
  // Require authentication
  const auth = useRequireAuth();

  useEffect(() => {
    loadCSFData();
  }, []);

  const loadCSFData = async () => {
    try {
      setLoading(true);
      console.log(`[${correlationId}] Loading CSF data for engagement: ${engagementId}`);
      const csfFunctions = await getFunctions();
      setFunctions(csfFunctions);
      console.log(`[${correlationId}] Loaded ${csfFunctions.length} CSF functions`);
      
      // Auto-expand first function for better UX
      if (csfFunctions.length > 0) {
        // This will be handled by initial state in CSFGrid component
      }
    } catch (err) {
      console.error(`[${correlationId}] Error loading CSF data:`, err);
      setError(err instanceof Error ? err.message : 'Failed to load CSF data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubcategorySelect = (subcategory: CSFSubcategory) => {
    console.log(`[${correlationId}] Subcategory selected: ${subcategory.id}`);
    setSelectedSubcategory(subcategory);
    setDrawerOpen(true);
  };

  const handleDrawerClose = () => {
    console.log(`[${correlationId}] Drawer closed`);
    setDrawerOpen(false);
  };

  const handleScoreChange = (score: number) => {
    console.log(`[${correlationId}] Score changed: ${score} for ${selectedSubcategory?.id}`);
    // TODO: Implement score persistence
  };

  const handleRationaleChange = (rationale: string) => {
    console.log(`[${correlationId}] Rationale changed for ${selectedSubcategory?.id}`);
    // TODO: Implement rationale persistence
  };

  const handleEvidenceSelect = (evidence: Evidence) => {
    console.log(`[${correlationId}] Evidence selected: ${evidence.filename}`);
    // TODO: Implement evidence linking/preview
  };

  // Memoized statistics for performance
  const stats = useMemo(() => {
    if (!functions.length) return { functions: 0, categories: 0, subcategories: 0 };
    
    return {
      functions: functions.length,
      categories: functions.reduce((sum, f) => sum + f.categories.length, 0),
      subcategories: functions.reduce((sum, f) => 
        sum + f.categories.reduce((catSum, c) => catSum + c.subcategories.length, 0), 0
      )
    };
  }, [functions]);

  if (auth.isLoading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading...</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="font-medium text-red-800">Error Loading Assessment</h3>
          <p className="text-red-600 text-sm mt-1">{error}</p>
          <button 
            onClick={loadCSFData}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="p-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-gray-900">
            CSF 2.0 Assessment Grid
          </h1>
          <p className="text-gray-600 text-sm mt-1">
            Engagement: {engagementId}
          </p>
          <div className="flex gap-4 text-sm text-gray-500 mt-2">
            <span>{stats.functions} Functions</span>
            <span>{stats.categories} Categories</span>
            <span>{stats.subcategories} Subcategories</span>
          </div>
        </div>

        {/* Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* CSF Grid - Left side (2/3 width) */}
          <div className="lg:col-span-2">
            <CSFGrid
              functions={functions}
              onSubcategorySelect={handleSubcategorySelect}
              selectedSubcategory={selectedSubcategory}
            />
          </div>

          {/* Details Panel - Right side (1/3 width) */}
          <div className="lg:col-span-1">
            {selectedSubcategory ? (
              <DetailsPanel subcategory={selectedSubcategory} />
            ) : (
              <div className="bg-white border rounded-lg p-6 text-center text-gray-500">
                <h3 className="font-medium mb-2">Select a Subcategory</h3>
                <p className="text-sm">
                  Click on any subcategory from the grid to view details and assessment options.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Enhanced Subcategory Drawer */}
        <SubcategoryDrawer
          subcategory={selectedSubcategory}
          isOpen={drawerOpen}
          onClose={handleDrawerClose}
          onScoreChange={handleScoreChange}
          onRationaleChange={handleRationaleChange}
          onEvidenceSelect={handleEvidenceSelect}
          correlationId={correlationId}
        />
      </div>
    </div>
  );
}