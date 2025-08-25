import { getEmail, getEngagementId } from "./auth";

// ALWAYS use proxy routes instead of direct external API calls to avoid timeout issues
const API_BASE = "/api/proxy";

function getAuthHeaders(): Record<string, string> {
  const email = getEmail();
  const engagementId = getEngagementId();
  
  return {
    "X-User-Email": email || "",
    "X-Engagement-ID": engagementId || "",
  };
}

export async function createAssessment(name: string, framework: string = "NIST-CSF") {
  // Validate input
  const trimmedName = name.trim();
  if (!trimmedName) {
    throw new Error("createAssessment: name must be a non-empty string");
  }
  
  const res = await fetch(`${API_BASE}/domain-assessments`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      ...getAuthHeaders()
    },
    body: JSON.stringify({ name: trimmedName, framework }),
    signal: AbortSignal.timeout(15000) // 15 second timeout for assessment creation
  });
  if (!res.ok) throw new Error(`createAssessment failed: ${res.status}`);
  return res.json();
}

export async function runAnalyze(assessmentId: string, content: string) {
  const res = await fetch(`${API_BASE}/orchestrations/analyze`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      ...getAuthHeaders()
    },
    body: JSON.stringify({ assessment_id: assessmentId, content }),
    signal: AbortSignal.timeout(30000) // 30 second timeout for analysis
  });
  if (!res.ok) throw new Error(`analyze failed: ${res.status}`);
  const data = await res.json();
  return data as { findings: Array<any> };
}

export async function runRecommend(assessmentId: string) {
  const res = await fetch(`${API_BASE}/orchestrations/recommend`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      ...getAuthHeaders()
    },
    body: JSON.stringify({ assessment_id: assessmentId }),
    signal: AbortSignal.timeout(30000) // 30 second timeout for recommendations
  });
  if (!res.ok) throw new Error(`recommend failed: ${res.status}`);
  const data = await res.json();
  return data as { recommendations: Array<any> };
}
