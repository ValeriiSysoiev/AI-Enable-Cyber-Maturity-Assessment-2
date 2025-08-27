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
  
  // Check if we should store this assessment locally (fallback scenario)
  const shouldStoreLocally = res.headers.get('X-Store-Locally');
  if (shouldStoreLocally === 'true') {
    console.log('Storing assessment locally for offline access');
    localStorage.setItem(`assessment_${result.id}`, JSON.stringify(result));
  }
  
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
  console.log('Saving answer:', { assessmentId, payload });
  
  // Try backend API first, fallback to local storage
  try {
    console.log('Attempting to save to backend API...');
    const res = await fetch(`${BASE}/assessments/${assessmentId}/answers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: 'no-store'
    });
    
    console.log('Backend API response:', res.status, res.statusText);
    
    if (res.ok) {
      console.log('Answer saved to backend successfully');
      return;
    } else {
      throw new Error(`Backend API failed: ${res.status}`);
    }
  } catch (backendError) {
    console.log('Backend API unavailable, saving locally:', backendError);
    
    // Fallback: Save answer to local storage
    const localAssessment = localStorage.getItem(`assessment_${assessmentId}`);
    if (localAssessment) {
      const assessment = JSON.parse(localAssessment);
      
      // Remove any existing answer for this question
      assessment.answers = assessment.answers.filter((ans: Answer) => 
        !(ans.pillar_id === payload.pillar_id && ans.question_id === payload.question_id)
      );
      
      // Add the new answer
      assessment.answers.push(payload);
      
      // Update the assessment in localStorage
      localStorage.setItem(`assessment_${assessmentId}`, JSON.stringify(assessment));
      console.log('Answer saved locally:', payload);
    } else {
      console.error('Assessment not found in local storage');
      throw new Error("Failed to save answer: Assessment not found locally");
    }
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
  console.log('Getting assessment:', assessmentId);
  
  // Try backend API first, fallback to local storage
  try {
    console.log('Attempting to fetch from backend API...');
    const res = await fetch(`${BASE}/assessments/${assessmentId}`, {
      cache: 'no-store'
    });
    
    console.log('Backend API response:', res.status, res.statusText);
    
    if (res.ok) {
      const result = await res.json();
      console.log('Backend API success:', result);
      return result;
    } else {
      throw new Error(`Backend API failed: ${res.status}`);
    }
  } catch (backendError) {
    console.log('Backend API unavailable, checking local storage:', backendError);
    
    // Fallback: Check if we have this assessment in localStorage
    const localAssessment = localStorage.getItem(`assessment_${assessmentId}`);
    if (localAssessment) {
      console.log('Found assessment in local storage');
      return JSON.parse(localAssessment);
    }
    
    // If not in localStorage, create a basic assessment structure
    console.log('Assessment not found locally, creating basic structure');
    const basicAssessment = {
      id: assessmentId,
      name: "Assessment",
      preset_id: "cyber-for-ai", // Default preset
      created_at: new Date().toISOString(),
      answers: []
    };
    
    // Store it locally for future retrieval
    localStorage.setItem(`assessment_${assessmentId}`, JSON.stringify(basicAssessment));
    console.log('Created and stored basic assessment:', basicAssessment);
    
    return basicAssessment;
  }
}














