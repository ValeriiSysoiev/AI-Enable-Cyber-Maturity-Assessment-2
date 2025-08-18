// Chat types matching backend API models

export interface ChatMessage {
  id: string;
  engagement_id: string;
  message: string;
  sender: 'user' | 'agent';
  timestamp: string;
  correlation_id?: string;
}

export interface RunCard {
  id: string;
  engagement_id: string;
  command: string;
  inputs: Record<string, any>;
  outputs?: Record<string, any> | null;
  status: 'queued' | 'running' | 'done' | 'error';
  created_at: string;
  created_by: string;
  citations?: string[] | null;
}

// API Request/Response types
export interface ChatMessageCreate {
  message: string;
  correlation_id?: string;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface RunCardHistoryResponse {
  run_cards: RunCard[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

// Command parsing types
export interface Command {
  type: '/ingest' | '/minutes' | '/score';
  args: string;
  raw: string;
}

export interface CommandSuggestion {
  command: string;
  description: string;
  example: string;
}