const BASE = "/api/proxy";

export interface Assessment {
  id: string;
  name: string;
  preset_id: string;
  created_at: string;
  answers: Answer[];
}

export interface Answer {
  pillar_id: string;
  question_id: string;
  level: number;
  notes?: string;
}

export interface ScoreData {
  assessment_id: string;
  pillar_scores: {
    pillar_id: string;
    score: number | null;
    weight: number;
    questions_answered: number;
    total_questions: number;
  }[];
  overall_score: number | null;
  gates_applied: string[];
}

export async function createAssessment(name: string, presetId: string): Promise<Assessment> {
  // Get auth headers (includes X-User-Email)
  const authHeaders = getAuthHeaders();
  
  console.log('Creating assessment with:', { name, presetId, authHeaders });
  
  const res = await fetch(`${BASE}/assessments`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      ...authHeaders
    },
    body: JSON.stringify({ name, preset_id: presetId }),
    cache: 'no-store'
  });
  
  console.log('Assessment creation response:', res.status, res.statusText);
  
  if (!res.ok) {
    const errorText = await res.text();
    console.error('Assessment creation failed:', {
      status: res.status,
      statusText: res.statusText,
      errorText,
      headers: Object.fromEntries(res.headers.entries())
    });
    throw new Error(`Failed to create assessment: ${res.status} ${errorText}`);
  }
  
  const result = await res.json();
  console.log('Assessment created successfully:', result);
  return result;
}

// Helper function to get auth headers
function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  
  const headers: Record<string, string> = {};
  
  // Always try to get email from localStorage first (works for both modes)
  const email = localStorage.getItem('email');
  if (email) {
    headers['X-User-Email'] = email;
  }
  
  const engagementId = localStorage.getItem('engagementId');
  if (engagementId) {
    headers['X-Engagement-ID'] = engagementId;
  }
  
  return headers;
}

export async function saveAnswer(assessmentId: string, payload: Answer): Promise<void> {
  const res = await fetch(`${BASE}/assessments/${assessmentId}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: 'no-store'
  });
  if (!res.ok) {
    throw new Error("Failed to save answer");
  }
}

export async function getScores(assessmentId: string): Promise<ScoreData> {
  const res = await fetch(`${BASE}/assessments/${assessmentId}/scores`, {
    cache: 'no-store'
  });
  if (!res.ok) {
    throw new Error("Failed to get scores");
  }
  return res.json();
}

export async function getAssessment(assessmentId: string): Promise<Assessment> {
  const res = await fetch(`${BASE}/assessments/${assessmentId}`, {
    cache: 'no-store'
  });
  if (!res.ok) {
    throw new Error("Failed to get assessment");
  }
  return res.json();
}














