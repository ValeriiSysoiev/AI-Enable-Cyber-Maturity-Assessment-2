import { getEmail, getEngagementId } from "./auth";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// Helper to add auth headers
function getAuthHeaders(): Record<string, string> {
  const email = getEmail();
  const engagementId = getEngagementId();
  
  const headers: Record<string, string> = {};
  if (email) headers["X-User-Email"] = email;
  if (engagementId) headers["X-Engagement-ID"] = engagementId;
  
  return headers;
}

// Authenticated fetch wrapper
export async function apiFetch(url: string, options: RequestInit = {}) {
  const authHeaders = getAuthHeaders();
  
  const response = await fetch(`${BASE}${url}`, {
    ...options,
    headers: {
      ...authHeaders,
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }
  
  return response.json();
}

export async function fetchPreset(id: string) {
  try {
    const res = await fetch(`${BASE}/presets/${id}`, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`Preset ${id} not found`);
    }
    return res.json();
  } catch (error) {
    console.error("Error fetching preset:", error);
    throw error;
  }
}

// Export API_BASE and authHeaders for other modules
export const API_BASE = BASE;
export function authHeaders(skipContentType: boolean = false): Record<string, string> {
  const headers = getAuthHeaders();
  if (!skipContentType) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}
