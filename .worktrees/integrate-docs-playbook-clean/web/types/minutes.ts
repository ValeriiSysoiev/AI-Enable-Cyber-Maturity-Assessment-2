// Minutes-related TypeScript types matching backend models

export interface MinutesSection {
  attendees: string[];
  decisions: string[];
  actions: string[];
  questions: string[];
}

export interface Minutes {
  id: string;
  workshop_id: string;
  status: 'draft' | 'published';
  sections: MinutesSection;
  generated_by: 'agent' | 'human';
  published_at?: string;
  content_hash?: string;
  parent_id?: string;
  created_at: string;
  updated_by: string;
}

export interface GenerateMinutesRequest {
  workshop_type?: string;
  attendees?: string[];
  additional_context?: Record<string, any>;
}

export interface UpdateMinutesRequest {
  sections: MinutesSection;
}

export interface MinutesError {
  detail: string;
  status_code: number;
}