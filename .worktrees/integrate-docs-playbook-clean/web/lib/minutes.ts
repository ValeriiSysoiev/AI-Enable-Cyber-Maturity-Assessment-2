import { apiFetch } from './api';
import { Minutes, GenerateMinutesRequest, UpdateMinutesRequest, MinutesError } from '../types/minutes';

export class MinutesConflictError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'MinutesConflictError';
  }
}

export async function generateDraftMinutes(
  workshopId: string, 
  request: GenerateMinutesRequest = {}
): Promise<Minutes> {
  try {
    return await apiFetch(`/workshops/${workshopId}/minutes/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
  } catch (error) {
    throw new Error(`Failed to generate minutes: ${error}`);
  }
}

export async function updateMinutes(
  minutesId: string, 
  request: UpdateMinutesRequest
): Promise<Minutes> {
  try {
    return await apiFetch(`/minutes/${minutesId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
  } catch (error) {
    if (error instanceof Error && error.message.includes('409')) {
      throw new MinutesConflictError('Cannot modify published minutes. Create a new version instead.');
    }
    throw new Error(`Failed to update minutes: ${error}`);
  }
}

export async function publishMinutes(minutesId: string): Promise<Minutes> {
  try {
    return await apiFetch(`/minutes/${minutesId}/publish`, {
      method: 'POST',
    });
  } catch (error) {
    if (error instanceof Error && error.message.includes('409')) {
      throw new MinutesConflictError('Minutes are already published and cannot be modified.');
    }
    throw new Error(`Failed to publish minutes: ${error}`);
  }
}

export async function createNewVersion(minutesId: string): Promise<Minutes> {
  try {
    return await apiFetch(`/minutes/${minutesId}/new-version`, {
      method: 'POST',
    });
  } catch (error) {
    throw new Error(`Failed to create new version: ${error}`);
  }
}

export async function getMinutes(minutesId: string): Promise<Minutes> {
  try {
    return await apiFetch(`/minutes/${minutesId}`);
  } catch (error) {
    throw new Error(`Failed to get minutes: ${error}`);
  }
}

export async function getWorkshopMinutes(workshopId: string): Promise<Minutes[]> {
  try {
    return await apiFetch(`/workshops/${workshopId}/minutes`);
  } catch (error) {
    throw new Error(`Failed to get workshop minutes: ${error}`);
  }
}