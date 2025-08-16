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

// Default timeout for API requests (30 seconds)
const DEFAULT_TIMEOUT = 30000;

// Extended RequestInit interface with timeout support
interface RequestInitWithTimeout extends RequestInit {
  timeout?: number;
}

// Authenticated fetch wrapper with timeout support
export async function apiFetch(url: string, options: RequestInitWithTimeout = {}) {
  const authHeaders = getAuthHeaders();
  
  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options.timeout || DEFAULT_TIMEOUT);
  
  try {
    const response = await fetch(`${BASE}${url}`, {
      ...options,
      signal: controller.signal,
      headers: {
        ...authHeaders,
        ...options.headers,
      },
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(error.detail || `Request failed: ${response.status}`);
    }
    
    return response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    
    if (error.name === 'AbortError') {
      throw new Error('Request timeout - please try again');
    }
    
    throw error;
  }
}

export async function fetchPreset(id: string) {
  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT);
  
  try {
    const res = await fetch(`${BASE}/presets/${id}`, { 
      cache: "no-store",
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (!res.ok) {
      throw new Error(`Preset ${id} not found`);
    }
    return res.json();
  } catch (error) {
    clearTimeout(timeoutId);
    
    if (error.name === 'AbortError') {
      console.error("Preset fetch timeout:", id);
      throw new Error('Request timeout - please try again');
    }
    
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
