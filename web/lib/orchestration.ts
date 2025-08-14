import { getEmail, getEngagementId } from "./auth";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

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
    body: JSON.stringify({ name: trimmedName, framework })
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
    body: JSON.stringify({ assessment_id: assessmentId, content })
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
    body: JSON.stringify({ assessment_id: assessmentId })
  });
  if (!res.ok) throw new Error(`recommend failed: ${res.status}`);
  const data = await res.json();
  return data as { recommendations: Array<any> };
}
