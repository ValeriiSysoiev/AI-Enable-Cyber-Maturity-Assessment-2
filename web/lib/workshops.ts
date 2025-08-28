import { apiFetch } from "./api";
import type {
  Workshop,
  WorkshopListResponse,
  CreateWorkshopFormData,
  ConsentRequestData,
  StartWorkshopResponse,
} from "../types/workshops";

/**
 * Create a new workshop
 */
export async function createWorkshop(
  engagementId: string,
  data: CreateWorkshopFormData
): Promise<Workshop> {
  const payload = {
    engagement_id: engagementId,
    title: data.title,
    start_ts: data.start_ts || null,
    attendees: data.attendees,
  };

  const response = await apiFetch("/api/v1/workshops", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Engagement-ID": engagementId,
    },
    body: JSON.stringify(payload),
  });

  return response;
}

/**
 * List workshops for an engagement
 */
export async function listWorkshops(
  engagementId: string,
  page: number = 1,
  pageSize: number = 50
): Promise<WorkshopListResponse> {
  const params = new URLSearchParams({
    engagement_id: engagementId,
    page: page.toString(),
    page_size: pageSize.toString(),
  });

  const response = await apiFetch(`/api/v1/workshops?${params}`, {
    headers: {
      "X-Engagement-ID": engagementId,
    },
  });

  return response;
}

/**
 * Give consent for workshop attendance
 */
export async function giveConsent(
  engagementId: string,
  workshopId: string,
  data: ConsentRequestData
): Promise<Workshop> {
  const response = await apiFetch(`/api/v1/workshops/${workshopId}/consent`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Engagement-ID": engagementId,
    },
    body: JSON.stringify(data),
  });

  return response;
}

/**
 * Start a workshop (requires lead permissions and all consent)
 */
export async function startWorkshop(
  engagementId: string,
  workshopId: string
): Promise<StartWorkshopResponse> {
  const response = await apiFetch(`/api/v1/workshops/${workshopId}/start`, {
    method: "POST",
    headers: {
      "X-Engagement-ID": engagementId,
    },
  });

  return response;
}

/**
 * Check if all attendees have given consent
 */
export function hasAllConsent(workshop: Workshop): boolean {
  return workshop.attendees.every((attendee) => attendee.consent !== undefined);
}

/**
 * Get consent status summary
 */
export function getConsentStatus(workshop: Workshop): {
  total: number;
  consented: number;
  pending: number;
  percentage: number;
} {
  const total = workshop.attendees.length;
  const consented = workshop.attendees.filter((a) => a.consent).length;
  const pending = total - consented;
  const percentage = total > 0 ? Math.round((consented / total) * 100) : 0;

  return { total, consented, pending, percentage };
}