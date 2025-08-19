// Workshop types matching backend API schemas

export interface WorkshopAttendee {
  id: string;
  user_id: string;
  email: string;
  role: string;
  consent?: ConsentRecord;
}

export interface ConsentRecord {
  by: string;
  user_id: string;
  timestamp: string; // ISO string
}

export interface Workshop {
  id: string;
  engagement_id: string;
  title: string;
  start_ts?: string; // ISO string
  attendees: WorkshopAttendee[];
  created_by: string;
  created_at: string; // ISO string
  started: boolean;
  started_at?: string; // ISO string
}

export interface WorkshopListResponse {
  workshops: Workshop[];
  total_count: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// Form types for UI
export interface CreateWorkshopFormData {
  title: string;
  start_ts?: string;
  attendees: {
    user_id: string;
    email: string;
    role: string;
  }[];
}

export interface ConsentRequestData {
  attendee_id: string;
  consent: boolean;
}

export interface StartWorkshopResponse {
  workshop: Workshop;
  message: string;
}