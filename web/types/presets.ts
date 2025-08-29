/**
 * Preset and Assessment Types
 * 
 * Shared types for assessment presets and related data structures.
 */

export interface PresetCounts {
  pillars: number;
  capabilities: number;
  questions: number;
}

export interface PresetOption {
  id: string;
  name: string;
  version: string;
  source: string;
  counts: PresetCounts;
}

export interface Question {
  id: string;
  text: string;
  weight: number;
  scale: string;
}

export interface Capability {
  id: string;
  name: string;
  questions: Question[];
}

export interface Pillar {
  id: string;
  name: string;
  capabilities: Capability[];
}

export interface AssessmentPreset {
  id: string;
  name: string;
  version: string;
  pillars: Pillar[];
}

export interface QuestionWithAnswer {
  question: Question;
  answer?: {
    pillar_id: string;
    question_id: string;
    level: number;
    notes?: string;
  };
}