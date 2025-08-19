import { API_BASE, authHeaders } from "@/lib/api";

export type CountSummary = {
  assessments: number; documents: number; findings: number; recommendations: number; runlogs: number;
};
export type ActivityItem = { type: string; id: string; ts?: string; title?: string | null; extra?: any };
export type EngagementSummary = {
  engagement_id: string;
  counts: CountSummary;
  last_activity?: string | null;
  recent_activity: ActivityItem[];
  recent_runlog_excerpt?: string | null;
};

export async function getSummary(eid: string): Promise<EngagementSummary> {
  try {
    const r = await fetch(`${API_BASE}/engagements/${eid}/summary`, { headers: authHeaders() });
    
    if (!r.ok) {
      let errorBody = "";
      try {
        errorBody = await r.text();
      } catch {
        errorBody = "Unable to read response body";
      }
      throw new Error(`getSummary failed for engagement ${eid}: HTTP ${r.status} ${r.statusText}. Response: ${errorBody}`);
    }

    let data: any;
    try {
      data = await r.json();
    } catch (parseError) {
      throw new Error(`getSummary failed to parse JSON for engagement ${eid}: ${parseError}`);
    }

    // Validate the response shape
    if (!data || typeof data !== 'object') {
      throw new Error(`getSummary received invalid response for engagement ${eid}: not an object`);
    }
    
    if (typeof data.engagement_id !== 'string') {
      throw new Error(`getSummary received invalid response for engagement ${eid}: missing or invalid engagement_id`);
    }
    
    if (!data.counts || typeof data.counts !== 'object') {
      throw new Error(`getSummary received invalid response for engagement ${eid}: missing or invalid counts object`);
    }
    
    if (!Array.isArray(data.recent_activity)) {
      throw new Error(`getSummary received invalid response for engagement ${eid}: recent_activity is not an array`);
    }

    return data as EngagementSummary;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`getSummary unexpected error for engagement ${eid}: ${error}`);
  }
}

export function reportMdUrl(eid: string) {
  return `${API_BASE}/engagements/${eid}/exports/report.md`;
}
