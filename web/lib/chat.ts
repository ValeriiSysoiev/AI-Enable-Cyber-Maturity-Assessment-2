import { apiFetch } from './api';
import { 
  ChatMessage, 
  RunCard, 
  ChatMessageCreate, 
  ChatHistoryResponse, 
  RunCardHistoryResponse,
  CommandSuggestion 
} from '../types/chat';

/**
 * Send a chat message and potentially create a RunCard if command is detected
 */
export async function sendMessage(
  engagementId: string, 
  message: string, 
  correlationId?: string
): Promise<ChatMessage> {
  const payload: ChatMessageCreate = {
    message,
    correlation_id: correlationId
  };

  return apiFetch(`/chat/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Engagement-ID': engagementId,
    },
    body: JSON.stringify(payload),
  });
}

/**
 * Get chat message history for engagement
 */
export async function getChatMessages(
  engagementId: string,
  page: number = 1,
  pageSize: number = 50
): Promise<ChatHistoryResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString()
  });

  return apiFetch(`/chat/messages?${params}`, {
    method: 'GET',
    headers: {
      'X-Engagement-ID': engagementId,
    },
  });
}

/**
 * Get RunCard history for engagement
 */
export async function getRunCards(
  engagementId: string,
  page: number = 1,
  pageSize: number = 50,
  status?: 'queued' | 'running' | 'done' | 'error'
): Promise<RunCardHistoryResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString()
  });

  if (status) {
    params.append('status', status);
  }

  return apiFetch(`/chat/run-cards?${params}`, {
    method: 'GET',
    headers: {
      'X-Engagement-ID': engagementId,
    },
  });
}

/**
 * Parse message for command detection
 */
export function parseCommand(message: string): { command: string; args: string } | null {
  const trimmed = message.trim();
  if (!trimmed.startsWith('/')) return null;

  const spaceIndex = trimmed.indexOf(' ');
  if (spaceIndex === -1) {
    return { command: trimmed, args: '' };
  }

  return {
    command: trimmed.substring(0, spaceIndex),
    args: trimmed.substring(spaceIndex + 1).trim()
  };
}

/**
 * Get command suggestions for autocomplete
 */
export function getCommandSuggestions(): CommandSuggestion[] {
  return [
    {
      command: '/ingest',
      description: 'Ingest and process documents',
      example: '/ingest docs'
    },
    {
      command: '/minutes',
      description: 'Generate meeting minutes from audio',
      example: '/minutes recording.mp3'
    },
    {
      command: '/score',
      description: 'Calculate assessment scores',
      example: '/score assessment-id'
    }
  ];
}

/**
 * Real-time polling for RunCard status updates
 */
export class RunCardPoller {
  private intervalId: number | null = null;
  private callbacks: Array<(runCards: RunCard[]) => void> = [];

  constructor(
    private engagementId: string,
    private pollIntervalMs: number = 3000
  ) {}

  /**
   * Start polling for RunCard updates
   */
  start() {
    if (this.intervalId) return; // Already running

    this.intervalId = window.setInterval(async () => {
      try {
        const response = await getRunCards(this.engagementId, 1, 20);
        this.callbacks.forEach(callback => callback(response.run_cards));
      } catch (error) {
        console.error('RunCard polling error:', error);
      }
    }, this.pollIntervalMs);
  }

  /**
   * Stop polling
   */
  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  /**
   * Add callback for RunCard updates
   */
  onUpdate(callback: (runCards: RunCard[]) => void) {
    this.callbacks.push(callback);
  }

  /**
   * Remove callback
   */
  removeCallback(callback: (runCards: RunCard[]) => void) {
    const index = this.callbacks.indexOf(callback);
    if (index > -1) {
      this.callbacks.splice(index, 1);
    }
  }
}