import type { ProgressEvent } from './types';
import { AuthManager } from './auth';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error' | 'authenticating';

export interface WebSocketOptions {
  onMessage?: (event: ProgressEvent) => void;
  onStatusChange?: (status: WebSocketStatus) => void;
  onError?: (error: Event) => void;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export class RunProgressWebSocket {
  private ws: WebSocket | null = null;
  private runId: string;
  private options: Required<WebSocketOptions>;
  private reconnectCount = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private status: WebSocketStatus = 'disconnected';
  private authenticated = false;

  constructor(runId: string, options: WebSocketOptions = {}) {
    this.runId = runId;
    this.options = {
      onMessage: options.onMessage || (() => {}),
      onStatusChange: options.onStatusChange || (() => {}),
      onError: options.onError || (() => {}),
      reconnectAttempts: options.reconnectAttempts ?? 5,
      reconnectDelay: options.reconnectDelay ?? 3000,
    };
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    // Check for authentication token
    const token = AuthManager.getToken();
    if (!token) {
      console.error('No authentication token available for WebSocket');
      this.setStatus('error');
      AuthManager.redirectToLogin();
      return;
    }

    this.setStatus('connecting');
    const url = `${WS_BASE}/ws/runs/${this.runId}`;

    try {
      this.ws = new WebSocket(url);
      this.authenticated = false;
      this.setupEventHandlers(token);
    } catch (error) {
      this.setStatus('error');
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers(token: string): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      // Send authentication message after connection
      this.setStatus('authenticating');
      this.ws?.send(JSON.stringify({ type: 'auth', token }));
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Handle authentication response
        if (data.type === 'auth_error') {
          console.error('WebSocket authentication failed:', data.reason);
          this.setStatus('error');
          this.disconnect();
          AuthManager.clearToken();
          AuthManager.redirectToLogin();
          return;
        }

        if (data.type === 'auth_success') {
          this.authenticated = true;
          this.reconnectCount = 0;
          this.setStatus('connected');
          return;
        }

        // Only process messages if authenticated
        if (this.authenticated) {
          this.options.onMessage(data as ProgressEvent);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onerror = (event) => {
      this.setStatus('error');
      this.options.onError(event);
    };

    this.ws.onclose = (event) => {
      this.authenticated = false;
      this.setStatus('disconnected');

      // Code 1008 = Policy Violation (auth failure)
      if (event.code === 1008) {
        console.error('WebSocket closed due to auth failure');
        AuthManager.clearToken();
        AuthManager.redirectToLogin();
        return;
      }

      this.scheduleReconnect();
    };
  }

  private setStatus(status: WebSocketStatus): void {
    if (this.status !== status) {
      this.status = status;
      this.options.onStatusChange(status);
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectCount >= this.options.reconnectAttempts) {
      console.warn('Max reconnect attempts reached');
      return;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectTimer = setTimeout(() => {
      this.reconnectCount++;
      console.log(`Reconnecting... (attempt ${this.reconnectCount})`);
      this.connect();
    }, this.options.reconnectDelay);
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.setStatus('disconnected');
  }

  getStatus(): WebSocketStatus {
    return this.status;
  }
}

export function createRunProgressWebSocket(
  runId: string,
  options?: WebSocketOptions
): RunProgressWebSocket {
  return new RunProgressWebSocket(runId, options);
}
