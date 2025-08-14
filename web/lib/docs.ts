import { API_BASE, authHeaders } from "@/lib/api";

export type Doc = {
  id: string;
  engagement_id: string;
  filename: string;
  content_type?: string;
  size: number;
  uploaded_by: string;
  uploaded_at: string;
};

export async function listDocs(eid: string): Promise<Doc[]> {
  const r = await fetch(`${API_BASE}/engagements/${eid}/docs`, { headers: authHeaders() });
  if (!r.ok) throw new Error(`listDocs ${r.status}`);
  return r.json();
}

export async function uploadDocs(eid: string, files: File[]): Promise<Doc[]> {
  const fd = new FormData();
  files.forEach(f => fd.append("files", f));
  
  // Construct properly typed RequestInit object
  const init: RequestInit = {
    method: "POST",
    headers: authHeaders(true) as HeadersInit, // skip Content-Type for multipart
    body: fd,
  };
  
  const r = await fetch(`${API_BASE}/engagements/${eid}/docs`, init);
  
  if (!r.ok) {
    // Enhanced error handling with response details
    let errorMessage = `uploadDocs failed with status ${r.status}`;
    try {
      const errorBody = await r.text();
      if (errorBody) {
        errorMessage += `: ${errorBody}`;
      }
    } catch (parseError) {
      // If we can't read the response body, just use the status
      errorMessage += ` (unable to read error details)`;
    }
    throw new Error(errorMessage);
  }
  
  return r.json();
}

export function downloadUrl(eid: string, docId: string) {
  return `${API_BASE}/engagements/${eid}/docs/${docId}`;
}

export async function deleteDoc(eid: string, docId: string) {
  const r = await fetch(`${API_BASE}/engagements/${eid}/docs/${docId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!r.ok) throw new Error(`deleteDoc ${r.status}`);
  return r.json();
}

export async function analyzeDoc(eid: string, docId: string) {
  const r = await fetch(`${API_BASE}/orchestrations/analyze-doc`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ doc_id: docId }),
  });
  if (!r.ok) throw new Error(`analyzeDoc ${r.status}`);
  return r.json();
}
