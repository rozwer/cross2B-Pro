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
  Prompt,
  PromptListResponse,
  UpdatePromptInput,
  ModelsConfigResponse,
  ImagePosition,
  Section,
  GeneratedImage,
  KeywordSuggestionRequest,
  KeywordSuggestionResponse,
  HearingTemplate,
  HearingTemplateCreate,
  HearingTemplateUpdate,
  HearingTemplateList,
  Step12StatusResponse,
  Step12PreviewResponse,
  WordPressArticleResponse,
  Step12GenerateResponse,
  CostResponse,
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

    /**
     * Step11 画像生成を開始
     */
    startImageGeneration: async (
      id: string,
      config: {
        enabled: boolean;
        image_count?: number;
        position_request?: string;
      },
    ): Promise<{ success: boolean; message?: string }> => {
      return this.request<{ success: boolean; message?: string }>(
        `/api/runs/${id}/step11/start`,
        {
          method: "POST",
          body: JSON.stringify(config),
        },
      );
    },

    /**
     * Step11 画像生成をスキップ
     */
    skipImageGeneration: async (id: string): Promise<{ success: boolean }> => {
      return this.request<{ success: boolean }>(
        `/api/runs/${id}/step11/skip`,
        { method: "POST" },
      );
    },

    /**
     * Step11を完了済みとしてマーク（既存runのstep11スキップ用）
     */
    completeStep11: async (id: string): Promise<{ success: boolean }> => {
      return this.request<{ success: boolean }>(
        `/api/runs/${id}/step11/complete`,
        { method: "POST" },
      );
    },

    // ========== Step11 Multi-phase API ==========

    /**
     * Step11 設定を送信 (Phase 11A)
     * 設定保存後、位置分析を実行して11Bフェーズへ遷移
     */
    submitStep11Settings: async (
      id: string,
      settings: {
        image_count: number;
        position_request: string;
      },
    ): Promise<{
      success: boolean;
      phase: string;
      positions: ImagePosition[];
      sections: Section[];
      analysis_summary: string;
    }> => {
      return this.request<{
        success: boolean;
        phase: string;
        positions: ImagePosition[];
        sections: Section[];
        analysis_summary: string;
      }>(
        `/api/runs/${id}/step11/settings`,
        {
          method: "POST",
          body: JSON.stringify(settings),
        },
      );
    },

    /**
     * Step11 位置情報を取得 (Phase 11B)
     */
    getStep11Positions: async (
      id: string,
    ): Promise<{
      positions: ImagePosition[];
      sections: Section[];
      analysis_summary: string;
    }> => {
      return this.request<{
        positions: ImagePosition[];
        sections: Section[];
        analysis_summary: string;
      }>(`/api/runs/${id}/step11/positions`);
    },

    /**
     * Step11 位置確認を送信 (Phase 11B)
     * 承認時は11Cへ遷移、再分析時は11Bのまま
     */
    submitPositionReview: async (
      id: string,
      review: {
        approved: boolean;
        modified_positions?: ImagePosition[];
        reanalyze?: boolean;
        reanalyze_request?: string;
      },
    ): Promise<{
      success: boolean;
      phase: string;
      positions: ImagePosition[];
    }> => {
      return this.request<{
        success: boolean;
        phase: string;
        positions: ImagePosition[];
      }>(
        `/api/runs/${id}/step11/positions`,
        {
          method: "POST",
          body: JSON.stringify(review),
        },
      );
    },

    /**
     * Step11 画像指示を送信 (Phase 11C)
     * 指示送信後、画像生成を実行して11Dへ遷移
     */
    submitImageInstructions: async (
      id: string,
      data: {
        instructions: Array<{ index: number; instruction: string }>;
      },
    ): Promise<{
      success: boolean;
      phase: string;
      images: GeneratedImage[];
    }> => {
      return this.request<{
        success: boolean;
        phase: string;
        images: GeneratedImage[];
      }>(
        `/api/runs/${id}/step11/instructions`,
        {
          method: "POST",
          body: JSON.stringify(data),
        },
      );
    },

    /**
     * Step11 生成画像を取得 (Phase 11D)
     */
    getStep11Images: async (
      id: string,
    ): Promise<{
      images: GeneratedImage[];
      warnings: string[];
    }> => {
      return this.request<{
        images: GeneratedImage[];
        warnings: string[];
      }>(`/api/runs/${id}/step11/images`);
    },

    /**
     * Step11 画像レビューを送信 (Phase 11D)
     * リトライがあれば11Dのまま、なければ11Eへ遷移
     */
    submitImageReview: async (
      id: string,
      data: {
        reviews: Array<{
          index: number;
          accepted: boolean;
          retry?: boolean;
          retry_instruction?: string;
        }>;
      },
    ): Promise<{
      success: boolean;
      has_retries: boolean;
      phase: string;
    }> => {
      return this.request<{
        success: boolean;
        has_retries: boolean;
        phase: string;
      }>(
        `/api/runs/${id}/step11/images/review`,
        {
          method: "POST",
          body: JSON.stringify(data),
        },
      );
    },

    /**
     * Step11 プレビューを取得 (Phase 11E)
     */
    getStep11Preview: async (
      id: string,
    ): Promise<{
      preview_html: string;
      preview_available: boolean;
    }> => {
      return this.request<{
        preview_html: string;
        preview_available: boolean;
      }>(`/api/runs/${id}/step11/preview`);
    },

    /**
     * Step11 完了確認を送信 (Phase 11E)
     * confirmed=true で完了、restart_from で特定フェーズから再開
     */
    finalizeStep11: async (
      id: string,
      data: {
        confirmed: boolean;
        restart_from?: string;
      },
    ): Promise<{
      success: boolean;
      phase: string;
      output_path?: string;
      restarted_from?: string;
    }> => {
      return this.request<{
        success: boolean;
        phase: string;
        output_path?: string;
        restarted_from?: string;
      }>(
        `/api/runs/${id}/step11/finalize`,
        {
          method: "POST",
          body: JSON.stringify(data),
        },
      );
    },

    /**
     * 完了済みRunに画像を追加（Phase 11A開始）
     * 新API: /step11/settings を使用（Temporal不要）
     */
    addImagesToRun: async (
      id: string,
      data: {
        image_count: number;
        position_request: string;
      },
    ): Promise<{ success: boolean; message: string }> => {
      return this.request<{ success: boolean; message: string }>(
        `/api/runs/${id}/step11/settings`,
        {
          method: "POST",
          body: JSON.stringify(data),
        },
      );
    },
  };

  // ============================================
  // Step12 WordPress HTML API
  // ============================================

  step12 = {
    /**
     * Step12のステータスを取得
     */
    getStatus: async (runId: string): Promise<Step12StatusResponse> => {
      return this.request<Step12StatusResponse>(`/api/runs/${runId}/step12/status`);
    },

    /**
     * Step12のプレビューを取得（全記事または指定記事）
     */
    getPreview: async (runId: string, article?: number): Promise<Step12PreviewResponse> => {
      const query = article ? `?article=${article}` : "";
      return this.request<Step12PreviewResponse>(`/api/runs/${runId}/step12/preview${query}`);
    },

    /**
     * 特定の記事のプレビューを取得
     */
    getArticlePreview: async (
      runId: string,
      articleNumber: number,
    ): Promise<WordPressArticleResponse> => {
      return this.request<WordPressArticleResponse>(
        `/api/runs/${runId}/step12/preview/${articleNumber}`,
      );
    },

    /**
     * WordPress用HTMLを生成
     */
    generate: async (runId: string): Promise<Step12GenerateResponse> => {
      return this.request<Step12GenerateResponse>(`/api/runs/${runId}/step12/generate`, {
        method: "POST",
      });
    },

    /**
     * 全記事のZIPダウンロードURL
     */
    getDownloadAllUrl: (runId: string): string => {
      return `${this.baseUrl}/api/runs/${runId}/step12/download`;
    },

    /**
     * 特定記事のダウンロードURL
     */
    getDownloadArticleUrl: (runId: string, articleNumber: number): string => {
      return `${this.baseUrl}/api/runs/${runId}/step12/download/${articleNumber}`;
    },
  };

  // ============================================
  // Cost API
  // ============================================

  cost = {
    /**
     * Run のコスト情報を取得
     */
    get: async (runId: string): Promise<CostResponse> => {
      return this.request<CostResponse>(`/api/runs/${runId}/cost`);
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

    getPreviewUrl: (runId: string, article?: number): string => {
      const url = new URL(`${this.baseUrl}/api/runs/${runId}/preview`);
      if (article) {
        url.searchParams.set("article", article.toString());
      }
      return url.toString();
    },

    /**
     * HTMLプレビューを取得（認証ヘッダー付き）
     */
    getPreview: async (runId: string, article?: number): Promise<string> => {
      const url = this.artifacts.getPreviewUrl(runId, article);
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
  // Keywords API
  // ============================================

  keywords = {
    /**
     * テーマに基づいてキーワード候補を生成
     */
    suggest: async (request: KeywordSuggestionRequest): Promise<KeywordSuggestionResponse> => {
      return this.request<KeywordSuggestionResponse>("/api/keywords/suggest", {
        method: "POST",
        body: JSON.stringify(request),
      });
    },
  };

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

  // ============================================
  // Hearing Templates API
  // ============================================

  hearingTemplates = {
    /**
     * テンプレート一覧を取得
     */
    list: async (params?: {
      limit?: number;
      offset?: number;
    }): Promise<HearingTemplateList> => {
      const searchParams = new URLSearchParams();
      if (params?.limit) searchParams.set("limit", params.limit.toString());
      if (params?.offset) searchParams.set("offset", params.offset.toString());

      const query = searchParams.toString();
      return this.request<HearingTemplateList>(`/api/hearing/templates${query ? `?${query}` : ""}`);
    },

    /**
     * テンプレートを取得
     */
    get: async (id: string): Promise<HearingTemplate> => {
      return this.request<HearingTemplate>(`/api/hearing/templates/${id}`);
    },

    /**
     * テンプレートを作成
     */
    create: async (data: HearingTemplateCreate): Promise<HearingTemplate> => {
      return this.request<HearingTemplate>("/api/hearing/templates", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },

    /**
     * テンプレートを更新
     */
    update: async (id: string, data: HearingTemplateUpdate): Promise<HearingTemplate> => {
      return this.request<HearingTemplate>(`/api/hearing/templates/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },

    /**
     * テンプレートを削除
     */
    delete: async (id: string): Promise<{ success: boolean; message: string }> => {
      return this.request<{ success: boolean; message: string }>(`/api/hearing/templates/${id}`, {
        method: "DELETE",
      });
    },
  };
}

export const api = new ApiClient(API_BASE);
export default api;
