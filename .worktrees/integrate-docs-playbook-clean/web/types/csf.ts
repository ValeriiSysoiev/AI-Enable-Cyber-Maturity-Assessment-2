/**
 * CSF 2.0 Type Definitions
 * 
 * TypeScript interfaces for NIST Cybersecurity Framework 2.0
 * matching backend domain models for assessment grid interfaces.
 */

export interface CSFSubcategory {
  id: string;
  function_id: string;
  category_id: string;
  title: string;
  description: string;
}

export interface CSFCategory {
  id: string;
  function_id: string;
  title: string;
  description: string;
  subcategories: CSFSubcategory[];
}

export interface CSFFunction {
  id: string;
  title: string;
  description: string;
  categories: CSFCategory[];
}

export interface CSFTaxonomyResponse {
  version: string;
  functions: CSFFunction[];
  metadata: Record<string, any>;
}

export interface CSFErrorResponse {
  error: string;
  details?: string;
}

// Assessment-specific types for grid interface
export interface CSFAssessmentItem {
  subcategory_id: string;
  score?: number;
  rationale?: string;
  evidence?: string[];
}

export interface CSFGridProps {
  functions: CSFFunction[];
  onSubcategorySelect: (subcategory: CSFSubcategory) => void;
  selectedSubcategory?: CSFSubcategory;
  assessmentItems?: CSFAssessmentItem[];
}

export interface CSFDetailsPanel {
  subcategory: CSFSubcategory;
  assessmentItem?: CSFAssessmentItem;
  onScoreChange?: (score: number) => void;
  onRationaleChange?: (rationale: string) => void;
  onEvidenceAdd?: (evidence: string) => void;
}