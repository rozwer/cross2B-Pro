/**
 * API Client for SEO Article Generator
 *
 * NOTE: 開発段階では認証を無効化
 */

import type {
  Run,
  RunSummary,
  CreateRunInput,
  ArtifactRef,
  ArtifactContent,
  PaginatedResponse,
  ApiError,
  Prompt,
  PromptListResponse,
  UpdatePromptInput,
  ModelsConfigResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// 開発環境用の固定テナントID（本番では認証から取得）
const DEV_TENANT_ID = "dev-tenant-001";

/**
 * API接続エラーのカスタムクラス
 */
export class ApiConnectionError extends Error {
  constructor(
    message: string,
    public readonly baseUrl: string,
    public readonly cause?: Error
  ) {
    super(message);
    this.name = "ApiConnectionError";
  }
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  /**
   * API接続状態を確認
   */
  async checkConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: "GET",
        signal: AbortSignal.timeout(5000),
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * APIリクエスト（開発モード用X-Tenant-ID付き）
   */
  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      "X-Tenant-ID": DEV_TENANT_ID,  // 開発モード用、本番では AuthManager.getTenantId()
      ...options.headers,
    };

    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers,
      });
    } catch (error) {
      // ネットワークエラー（接続拒否、タイムアウト等）
      const cause = error instanceof Error ? error : undefined;
      throw new ApiConnectionError(
        `APIサーバーに接続できません。サーバーが起動していることを確認してください。(${this.baseUrl})`,
        this.baseUrl,
        cause
      );
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      // FastAPI の形式 { detail: string } または { error: { message: string } }
      const message =
        errorData?.detail ||
        errorData?.error?.message ||
        `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
    }

    return response.json();
  }

  // ============================================
  // Runs API
  // ============================================

  runs = {
    list: async (params?: {
      page?: number;
      limit?: number;
      status?: string;
    }): Promise<PaginatedResponse<RunSummary>> => {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", params.page.toString());
      if (params?.limit) searchParams.set("limit", params.limit.toString());
      if (params?.status) searchParams.set("status", params.status);

      const query = searchParams.toString();
      // Backend returns { runs, total, limit, offset } but we need { items, total, ... }
      const response = await this.request<{
        runs: RunSummary[];
        total: number;
        limit: number;
        offset: number;
      }>(`/api/runs${query ? `?${query}` : ""}`);

      const runs = response.runs ?? [];
      const total = response.total ?? 0;
      const limit = response.limit ?? 50;
      const offset = response.offset ?? 0;

      // Fixed: has_more is true only if there are more items AND we got a full page
      // This handles the edge case where runs.length is 0 at the end
      const has_more = runs.length === limit && (offset + runs.length) < total;

      return {
        items: runs,
        total,
        page: Math.floor(offset / limit) + 1,
        limit,
        has_more,
      };
    },

    get: async (id: string): Promise<Run> => {
      return this.request<Run>(`/api/runs/${id}`);
    },

    create: async (data: CreateRunInput): Promise<Run> => {
      return this.request<Run>("/api/runs", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },

    approve: async (id: string, comment?: string): Promise<{ success: boolean }> => {
      const params = comment ? `?comment=${encodeURIComponent(comment)}` : "";
      return this.request<{ success: boolean }>(`/api/runs/${id}/approve${params}`, {
        method: "POST",
      });
    },

    reject: async (id: string, reason: string): Promise<{ success: boolean }> => {
      return this.request<{ success: boolean }>(`/api/runs/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
    },

    cancel: async (id: string): Promise<{ success: boolean }> => {
      return this.request<{ success: boolean }>(`/api/runs/${id}`, {
        method: "DELETE",
      });
    },

    delete: async (id: string): Promise<{ success: boolean }> => {
      return this.request<{ success: boolean }>(`/api/runs/${id}/delete`, {
        method: "DELETE",
      });
    },

    retry: async (
      id: string,
      step: string,
    ): Promise<{ success: boolean; new_attempt_id: string }> => {
      return this.request<{ success: boolean; new_attempt_id: string }>(
        `/api/runs/${id}/retry/${step}`,
        { method: "POST" },
      );
    },

    resume: async (id: string, step: string): Promise<{
      success: boolean;
      new_run_id: string;
      resume_from: string;
      workflow_id?: string;
      loaded_steps?: string[];
    }> => {
      return this.request<{
        success: boolean;
        new_run_id: string;
        resume_from: string;
        workflow_id?: string;
        loaded_steps?: string[];
      }>(
        `/api/runs/${id}/resume/${step}`,
        { method: "POST" },
      );
    },

    clone: async (id: string, overrides?: Partial<CreateRunInput>): Promise<Run> => {
      return this.request<Run>(`/api/runs/${id}/clone`, {
        method: "POST",
        body: JSON.stringify(overrides || {}),
      });
    },

    bulkDelete: async (
      ids: string[],
    ): Promise<{ deleted: string[]; failed: Array<{ id: string; error: string }> }> => {
      return this.request<{ deleted: string[]; failed: Array<{ id: string; error: string }> }>(
        "/api/runs/bulk-delete",
        {
          method: "POST",
          body: JSON.stringify({ run_ids: ids }),
        },
      );
    },
  };

  // ============================================
  // Artifacts API
  // ============================================

  artifacts = {
    list: async (runId: string): Promise<ArtifactRef[]> => {
      return this.request<ArtifactRef[]>(`/api/runs/${runId}/files`);
    },

    get: async (runId: string, step: string): Promise<ArtifactRef[]> => {
      return this.request<ArtifactRef[]>(`/api/runs/${runId}/files/${step}`);
    },

    download: async (runId: string, artifactId: string): Promise<ArtifactContent> => {
      // URL encode artifactId as it may contain colons (e.g., "run_id:step:filename")
      return this.request<ArtifactContent>(`/api/runs/${runId}/files/${encodeURIComponent(artifactId)}/content`);
    },

    getPreviewUrl: (runId: string): string => {
      return `${this.baseUrl}/api/runs/${runId}/preview`;
    },

    /**
     * HTMLプレビューを取得（認証ヘッダー付き）
     */
    getPreview: async (runId: string): Promise<string> => {
      const url = `${this.baseUrl}/api/runs/${runId}/preview`;
      const response = await fetch(url, {
        method: "GET",
        headers: {
          "X-Tenant-ID": DEV_TENANT_ID,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `HTTP ${response.status}`);
      }

      return response.text();
    },
  };

  // ============================================
  // Events API
  // ============================================

  events = {
    list: async (
      runId: string,
      params?: { step?: string; limit?: number },
    ): Promise<
      Array<{
        id: string;
        event_type: string;
        payload: Record<string, unknown>;
        created_at: string;
      }>
    > => {
      const searchParams = new URLSearchParams();
      if (params?.step) searchParams.set("step", params.step);
      if (params?.limit) searchParams.set("limit", params.limit.toString());

      const query = searchParams.toString();
      return this.request(`/api/runs/${runId}/events${query ? `?${query}` : ""}`);
    },
  };

  // ============================================
  // Prompts API (JSON file-based)
  // ============================================

  // ============================================
  // Config API
  // ============================================

  config = {
    /**
     * モデル設定とワークフローステップデフォルトを取得
     * BEが一元管理する設定をFEで利用
     */
    getModels: async (): Promise<ModelsConfigResponse> => {
      return this.request<ModelsConfigResponse>("/api/config/models");
    },
  };

  // ============================================
  // Prompts API (JSON file-based)
  // ============================================

  prompts = {
    /**
     * プロンプト一覧を取得（JSON ファイルから読み込み）
     */
    list: async (params?: {
      pack_id?: string;
      step?: string;
    }): Promise<PromptListResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.pack_id) searchParams.set("pack_id", params.pack_id);
      if (params?.step) searchParams.set("step", params.step);

      const query = searchParams.toString();
      return this.request<PromptListResponse>(`/api/prompts${query ? `?${query}` : ""}`);
    },

    /**
     * 特定ステップのプロンプトを取得
     */
    getByStep: async (step: string, packId: string = "default"): Promise<Prompt> => {
      const searchParams = new URLSearchParams();
      searchParams.set("pack_id", packId);
      return this.request<Prompt>(`/api/prompts/step/${step}?${searchParams.toString()}`);
    },

    /**
     * 特定ステップのプロンプトを更新（JSON ファイルに書き込み）
     */
    updateByStep: async (
      step: string,
      data: UpdatePromptInput,
      packId: string = "default"
    ): Promise<Prompt> => {
      const searchParams = new URLSearchParams();
      searchParams.set("pack_id", packId);
      return this.request<Prompt>(`/api/prompts/step/${step}?${searchParams.toString()}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },
  };
}

export const api = new ApiClient(API_BASE);
export default api;
