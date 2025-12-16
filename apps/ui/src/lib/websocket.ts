/**
 * WebSocket Client for SEO Article Generator
 *
 * VULN-006: WebSocket認証対応
 * - 接続後に認証メッセージを送信（URLパラメータはログに残るリスク）
 * - 認証失敗時は code=1008 で切断
 * - テナント越境チェック対応
 */

import type { ProgressEvent } from './types';
import { AuthManager } from './auth';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error' | 'authenticating';

export interface WebSocketOptions {
  onMessage?: (event: ProgressEvent) => void;
  onStatusChange?: (status: WebSocketStatus) => void;
  onError?: (error: Event) => void;
  onAuthError?: (reason: string) => void;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

/** WebSocket認証メッセージ */
interface AuthMessage {
  type: 'auth';
  token: string;
}

/** WebSocket認証レスポンス */
interface AuthResponse {
  type: 'auth_success' | 'auth_error';
  reason?: string;
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
      onAuthError: options.onAuthError || (() => {}),
      reconnectAttempts: options.reconnectAttempts ?? 5,
      reconnectDelay: options.reconnectDelay ?? 3000,
    };
  }

  /**
   * WebSocket接続を開始
   *
   * セキュリティ要件:
   * - 認証トークンが必須
   * - 接続後に認証メッセージを送信
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    // 認証トークンチェック
    const token = AuthManager.getToken();
    if (!token) {
      console.error('WebSocket: No authentication token available');
      this.setStatus('error');
      this.options.onAuthError('No authentication token');
      AuthManager.handleUnauthorized();
      return;
    }

    this.setStatus('connecting');
    this.authenticated = false;
    const url = `${WS_BASE}/ws/runs/${this.runId}`;

    try {
      this.ws = new WebSocket(url);
      this.setupEventHandlers(token);
    } catch {
      this.setStatus('error');
      this.scheduleReconnect();
    }
  }

  /**
   * イベントハンドラーを設定
   *
   * セキュリティ要件:
   * - 接続後に認証メッセージを送信
   * - 認証成功まではメッセージを処理しない
   * - 認証失敗 (code=1008) は再接続しない
   */
  private setupEventHandlers(token: string): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      this.setStatus('authenticating');

      // 接続後に認証メッセージを送信
      const authMessage: AuthMessage = { type: 'auth', token };
      this.ws?.send(JSON.stringify(authMessage));
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // 認証レスポンスの処理
        if (data.type === 'auth_error') {
          console.error('WebSocket: Authentication failed:', data.reason);
          this.setStatus('error');
          this.options.onAuthError(data.reason || 'Authentication failed');
          this.disconnect();
          AuthManager.clearToken();
          AuthManager.handleUnauthorized();
          return;
        }

        if (data.type === 'auth_success') {
          this.authenticated = true;
          this.reconnectCount = 0;
          this.setStatus('connected');
          return;
        }

        // 認証済みの場合のみメッセージを処理
        if (this.authenticated) {
          this.options.onMessage(data as ProgressEvent);
        }
      } catch (error) {
        console.error('WebSocket: Failed to parse message:', error);
      }
    };

    this.ws.onerror = (event) => {
      this.setStatus('error');
      this.options.onError(event);
    };

    this.ws.onclose = (event) => {
      this.setStatus('disconnected');

      // 認証エラー (code=1008) は再接続しない
      if (event.code === 1008) {
        console.warn('WebSocket: Authentication failed, not reconnecting');
        AuthManager.clearToken();
        AuthManager.handleUnauthorized();
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
