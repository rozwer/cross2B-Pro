/**
 * WebSocket Client for SEO Article Generator
 *
 * NOTE: 開発段階では認証を無効化
 */

import type { ProgressEvent } from "./types";

export type WebSocketStatus = "connecting" | "connected" | "disconnected" | "error";

export interface WebSocketOptions {
  onMessage?: (event: ProgressEvent) => void;
  onStatusChange?: (status: WebSocketStatus) => void;
  onError?: (error: Event) => void;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

// 開発環境用の固定テナントID（本番では認証から取得）
const DEV_TENANT_ID = "dev-tenant-001";

export class RunProgressWebSocket {
  private ws: WebSocket | null = null;
  private runId: string;
  private options: Required<Omit<WebSocketOptions, "onAuthError">>;
  private reconnectCount = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private status: WebSocketStatus = "disconnected";

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

  /**
   * WebSocket接続を開始（開発モード用tenant_id付き）
   */
  connect(): void {
    // Check both OPEN and CONNECTING states to prevent duplicate connections
    if (this.ws?.readyState === WebSocket.OPEN ||
        this.ws?.readyState === WebSocket.CONNECTING) {
      return;
    }

    this.setStatus("connecting");
    // 開発モード: tenant_id をクエリパラメータで送信
    // 本番では AuthManager.getTenantId() を使用
    const url = `${WS_BASE}/ws/runs/${this.runId}?tenant_id=${DEV_TENANT_ID}`;

    try {
      this.ws = new WebSocket(url);
      this.setupEventHandlers();
    } catch {
      this.setStatus("error");
      this.scheduleReconnect();
    }
  }

  /**
   * イベントハンドラーを設定（認証なし - 開発モード）
   */
  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      this.reconnectCount = 0;
      this.setStatus("connected");
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.options.onMessage(data as ProgressEvent);
      } catch (error) {
        console.error("WebSocket: Failed to parse message:", error);
      }
    };

    this.ws.onerror = (event) => {
      this.setStatus("error");
      this.options.onError(event);
    };

    this.ws.onclose = () => {
      this.setStatus("disconnected");
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
      console.warn("Max reconnect attempts reached");
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

    this.setStatus("disconnected");
  }

  getStatus(): WebSocketStatus {
    return this.status;
  }

  getRunId(): string {
    return this.runId;
  }

  /**
   * runIdを変更して再接続する
   * 古い接続を閉じて新しいrunIdで接続を確立
   */
  changeRunId(newRunId: string): void {
    if (this.runId === newRunId) {
      return; // Same runId, no change needed
    }

    // Close existing connection
    this.disconnect();

    // Update runId and reconnect
    this.runId = newRunId;
    this.reconnectCount = 0; // Reset reconnect counter for new connection
    this.connect();
  }
}

export function createRunProgressWebSocket(
  runId: string,
  options?: WebSocketOptions,
): RunProgressWebSocket {
  return new RunProgressWebSocket(runId, options);
}
