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
  ArtifactUploadResponse,
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
  ServiceType,
  ApiSettingResponse,
  ApiSettingsListResponse,
  ApiSettingUpdateRequest,
  ConnectionTestResponse,
  LLMModel,
  LLMProviderWithModels,
  LLMProvidersListResponse,
  LLMModelCreateRequest,
  LLMModelUpdateRequest,
  TargetAudienceSuggestionRequest,
  TargetAudienceSuggestionResponse,
  RelatedKeywordSuggestionRequest,
  RelatedKeywordSuggestionResponse,
  ChildTopicSuggestionRequest,
  ChildTopicSuggestionResponse,
  ArticleListResponse,
  ArticleDetail,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL?.trim() || "http://localhost:8000";

// Warn if localhost is used in production (likely misconfiguration)
if (typeof window !== "undefined" && process.env.NODE_ENV === "production" && API_BASE.includes("localhost")) {
  console.warn("WARNING: Using localhost API in production mode - check NEXT_PUBLIC_API_URL");
}

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
      // Try to parse error response body
      let errorData: Record<string, unknown> | null = null;
      let parseError: string | null = null;
      try {
        const text = await response.text();
        if (text) {
          errorData = JSON.parse(text);
        }
      } catch (e) {
        // JSON parse failed - capture partial error info
        parseError = e instanceof Error ? e.message : "JSON parse failed";
      }

      // FastAPI の形式 { detail: string } または { error: { message: string } }
      let message: string;
      if (errorData?.detail) {
        message = String(errorData.detail);
      } else if (errorData?.error && typeof errorData.error === "object" && "message" in errorData.error) {
        message = String((errorData.error as { message: unknown }).message);
      } else if (parseError) {
        message = `HTTP ${response.status}: ${response.statusText} (response parse error: ${parseError})`;
      } else {
        message = `HTTP ${response.status}: ${response.statusText}`;
      }
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

    /**
     * Reject with retry instructions for Step3 (指示付きリトライ)
     */
    rejectWithRetry: async (
      id: string,
      reason: string,
      stepInstructions: Record<string, string>,
    ): Promise<{ success: boolean; mode: string; retrying: string[] }> => {
      return this.request<{ success: boolean; mode: string; retrying: string[] }>(
        `/api/runs/${id}/reject`,
        {
          method: "POST",
          body: JSON.stringify({
            reason,
            retry_with_instructions: true,
            step_instructions: stepInstructions,
          }),
        },
      );
    },

    /**
     * Review Step3 results with individual approval/retry per step
     * REQ-01 ~ REQ-05: 指示付きリトライ機能
     */
    step3Review: async (
      id: string,
      reviews: Array<{
        step: string;
        accepted: boolean;
        retry: boolean;
        retry_instruction: string;
      }>,
    ): Promise<{
      success: boolean;
      retrying: string[];
      approved: string[];
      next_action: string;
      retry_counts: Record<string, number>;
    }> => {
      return this.request<{
        success: boolean;
        retrying: string[];
        approved: string[];
        next_action: string;
        retry_counts: Record<string, number>;
      }>(`/api/runs/${id}/step3/review`, {
        method: "POST",
        body: JSON.stringify({ reviews }),
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

    /**
     * ワークフローを一時停止（次のステップ境界で停止）
     */
    pause: async (id: string): Promise<{ success: boolean; message: string }> => {
      return this.request<{ success: boolean; message: string }>(
        `/api/runs/${id}/pause`,
        { method: "POST" },
      );
    },

    /**
     * 停止状態のワークフローを続行
     */
    continue: async (id: string): Promise<{ success: boolean; message: string }> => {
      return this.request<{ success: boolean; message: string }>(
        `/api/runs/${id}/continue`,
        { method: "POST" },
      );
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
     * Step11 状態を取得（ウィザード復元用）
     */
    getStep11State: async (
      id: string,
    ): Promise<{
      phase: string;
      settings: { image_count: number; position_request: string } | null;
      positions: ImagePosition[];
      instructions: { index: number; instruction: string }[];
      images: GeneratedImage[];
      sections: Section[];
      analysis_summary: string;
      error: string | null;
    }> => {
      return this.request<{
        phase: string;
        settings: { image_count: number; position_request: string } | null;
        positions: ImagePosition[];
        instructions: { index: number; instruction: string }[];
        images: GeneratedImage[];
        sections: Section[];
        analysis_summary: string;
        error: string | null;
      }>(`/api/runs/${id}/step11/state`);
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
      article_markdown: string;
    }> => {
      return this.request<{
        positions: ImagePosition[];
        sections: Section[];
        analysis_summary: string;
        article_markdown: string;
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
     * ImageAdditionWorkflow を起動
     */
    addImagesToRun: async (
      id: string,
      data: {
        image_count: number;
        position_request: string;
      },
    ): Promise<{ success: boolean; message: string }> => {
      return this.request<{ success: boolean; message: string }>(
        `/api/runs/${id}/step11/add-images`,
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

    /**
     * アーティファクトをアップロード（上書き）
     */
    upload: async (
      runId: string,
      step: string,
      content: string,
      options?: { encoding?: "utf-8" | "base64"; invalidateCache?: boolean },
    ): Promise<ArtifactUploadResponse> => {
      return this.request<ArtifactUploadResponse>(
        `/api/runs/${runId}/files/${step}`,
        {
          method: "PUT",
          body: JSON.stringify({
            content,
            encoding: options?.encoding ?? "utf-8",
            invalidate_cache: options?.invalidateCache ?? false,
          }),
        },
      );
    },
  };

  // ============================================
  // Events API
  // ============================================

  events = {
    /**
     * List events for a run with optional filters
     * Returns DB-persisted events (survives page reload)
     */
    list: async (
      runId: string,
      params?: {
        step?: string;
        event_type?: string;
        since?: string;
        limit?: number;
        offset?: number;
      },
    ): Promise<
      Array<{
        id: string;
        event_type: string;
        step?: string;
        payload: Record<string, unknown>;
        details?: {
          run_id?: string;
          step?: string;
          tenant_id?: string;
          attempt?: number;
          duration_ms?: number;
          error?: string;
          error_category?: string;
          reason?: string;
          timestamp?: string;
          extra?: Record<string, unknown>;
        };
        created_at: string;
      }>
    > => {
      const searchParams = new URLSearchParams();
      if (params?.step) searchParams.set("step", params.step);
      if (params?.event_type) searchParams.set("event_type", params.event_type);
      if (params?.since) searchParams.set("since", params.since);
      if (params?.limit) searchParams.set("limit", params.limit.toString());
      if (params?.offset) searchParams.set("offset", params.offset.toString());

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
  // Suggestions API (AI-powered input assistance)
  // ============================================

  suggestions = {
    /**
     * ターゲット読者の候補を生成
     */
    targetAudience: async (request: TargetAudienceSuggestionRequest): Promise<TargetAudienceSuggestionResponse> => {
      return this.request<TargetAudienceSuggestionResponse>("/api/suggestions/target-audience", {
        method: "POST",
        body: JSON.stringify(request),
      });
    },

    /**
     * 関連キーワードの候補を生成
     */
    relatedKeywords: async (request: RelatedKeywordSuggestionRequest): Promise<RelatedKeywordSuggestionResponse> => {
      return this.request<RelatedKeywordSuggestionResponse>("/api/suggestions/related-keywords", {
        method: "POST",
        body: JSON.stringify(request),
      });
    },

    /**
     * 子記事トピックの候補を生成
     */
    childTopics: async (request: ChildTopicSuggestionRequest): Promise<ChildTopicSuggestionResponse> => {
      return this.request<ChildTopicSuggestionResponse>("/api/suggestions/child-topics", {
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
  // LLM Models Management API
  // ============================================

  models = {
    /**
     * Get all LLM providers with their models
     */
    list: async (): Promise<LLMProvidersListResponse> => {
      return this.request<LLMProvidersListResponse>("/api/models");
    },

    /**
     * Get models for a specific provider
     */
    getProvider: async (providerId: string): Promise<LLMProviderWithModels> => {
      return this.request<LLMProviderWithModels>(`/api/models/${providerId}`);
    },

    /**
     * Create a new model
     */
    create: async (data: LLMModelCreateRequest): Promise<LLMModel> => {
      return this.request<LLMModel>("/api/models", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },

    /**
     * Update an existing model
     */
    update: async (modelId: number, data: LLMModelUpdateRequest): Promise<LLMModel> => {
      return this.request<LLMModel>(`/api/models/${modelId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    },

    /**
     * Delete a model
     */
    delete: async (modelId: number): Promise<{ message: string }> => {
      return this.request<{ message: string }>(`/api/models/${modelId}`, {
        method: "DELETE",
      });
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

  // ============================================
  // GitHub API
  // ============================================

  github = {
    /**
     * リポジトリへのアクセス権限を確認
     */
    checkAccess: async (repoUrl: string): Promise<{
      accessible: boolean;
      permissions: string[];
      error?: string;
    }> => {
      return this.request<{
        accessible: boolean;
        permissions: string[];
        error?: string;
      }>("/api/github/check-access", {
        method: "POST",
        body: JSON.stringify({ repo_url: repoUrl }),
      });
    },

    /**
     * 新しいリポジトリを作成
     */
    createRepo: async (
      name: string,
      description?: string,
      isPrivate?: boolean
    ): Promise<{ repo_url: string }> => {
      return this.request<{ repo_url: string }>("/api/github/create-repo", {
        method: "POST",
        body: JSON.stringify({
          name,
          description: description || "",
          private: isPrivate ?? true,
        }),
      });
    },

    /**
     * Claude Code 用の Issue を作成
     */
    createIssue: async (
      runId: string,
      step: string,
      instruction: string
    ): Promise<{ issue_number: number; issue_url: string }> => {
      return this.request<{ issue_number: number; issue_url: string }>(
        "/api/github/create-issue",
        {
          method: "POST",
          body: JSON.stringify({ run_id: runId, step, instruction }),
        }
      );
    },

    /**
     * GitHub と MinIO の差分を取得（PR情報・ブランチ情報を含む）
     */
    getDiff: async (
      runId: string,
      step: string
    ): Promise<{
      has_diff: boolean;
      diff: string | null;
      github_sha: string | null;
      minio_digest: string | null;
      open_prs: Array<{
        number: number;
        title: string;
        url: string;
        state: string;
        head_branch: string | null;
        base_branch: string | null;
        user: string | null;
        created_at: string | null;
        updated_at: string | null;
        additions: number;
        deletions: number;
        status: string | null;
      }>;
      pending_branches: Array<{
        name: string;
        url: string;
        compare_url: string;
        last_commit_sha: string | null;
        last_commit_message: string | null;
        last_commit_date: string | null;
        author: string | null;
        additions: number;
        deletions: number;
        status: string | null;
        ahead_by: number;
        behind_by: number;
      }>;
    }> => {
      return this.request<{
        has_diff: boolean;
        diff: string | null;
        github_sha: string | null;
        minio_digest: string | null;
        open_prs: Array<{
          number: number;
          title: string;
          url: string;
          state: string;
          head_branch: string | null;
          base_branch: string | null;
          user: string | null;
          created_at: string | null;
          updated_at: string | null;
          additions: number;
          deletions: number;
          status: string | null;
        }>;
        pending_branches: Array<{
          name: string;
          url: string;
          compare_url: string;
          last_commit_sha: string | null;
          last_commit_message: string | null;
          last_commit_date: string | null;
          author: string | null;
          additions: number;
          deletions: number;
          status: string | null;
          ahead_by: number;
          behind_by: number;
        }>;
      }>(`/api/github/diff/${runId}/${step}`);
    },

    /**
     * GitHub から MinIO へ同期
     */
    sync: async (
      runId: string,
      step: string
    ): Promise<{
      synced: boolean;
      github_sha: string | null;
      minio_digest: string | null;
      message: string;
    }> => {
      return this.request<{
        synced: boolean;
        github_sha: string | null;
        minio_digest: string | null;
        message: string;
      }>(`/api/github/sync/${runId}/${step}`, {
        method: "POST",
      });
    },

    /**
     * ブランチから PR を作成
     */
    createPR: async (
      runId: string,
      branchName: string,
      title?: string,
      body?: string
    ): Promise<{
      number: number;
      title: string;
      url: string;
      state: string;
      head_branch: string | null;
      base_branch: string | null;
    }> => {
      return this.request<{
        number: number;
        title: string;
        url: string;
        state: string;
        head_branch: string | null;
        base_branch: string | null;
      }>(`/api/github/create-pr/${runId}`, {
        method: "POST",
        body: JSON.stringify({
          branch_name: branchName,
          title,
          body,
        }),
      });
    },

    /**
     * Get sync status for all steps of a run
     */
    getSyncStatus: async (
      runId: string
    ): Promise<{
      run_id: string;
      statuses: Array<{
        step: string;
        status: string;
        github_sha: string | null;
        minio_digest: string | null;
        synced_at: string | null;
      }>;
    }> => {
      return this.request<{
        run_id: string;
        statuses: Array<{
          step: string;
          status: string;
          github_sha: string | null;
          minio_digest: string | null;
          synced_at: string | null;
        }>;
      }>(`/api/github/sync-status/${runId}`);
    },

    /**
     * Create a review issue for Claude Code to review an article
     */
    createReview: async (
      runId: string,
      step: string,
      reviewType: "fact_check" | "seo" | "quality" | "all" = "all"
    ): Promise<{
      issue_number: number;
      issue_url: string;
      review_type: string;
      output_path: string;
    }> => {
      return this.request<{
        issue_number: number;
        issue_url: string;
        review_type: string;
        output_path: string;
      }>(`/api/github/review/${runId}/${step}`, {
        method: "POST",
        body: JSON.stringify({ review_type: reviewType }),
      });
    },

    /**
     * Save review result to MinIO and post comment to GitHub issue
     */
    saveReviewResult: async (
      runId: string,
      step: string,
      reviewData: Record<string, unknown>,
      issueNumber?: number
    ): Promise<{
      saved: boolean;
      path: string;
      digest: string;
      comment_posted: boolean;
    }> => {
      return this.request<{
        saved: boolean;
        path: string;
        digest: string;
        comment_posted: boolean;
      }>(`/api/github/review-result/${runId}/${step}`, {
        method: "POST",
        body: JSON.stringify({
          review_data: reviewData,
          issue_number: issueNumber,
        }),
      });
    },

    /**
     * Get review status for a step
     */
    getReviewStatus: async (
      runId: string,
      step: string
    ): Promise<{
      status: "pending" | "in_progress" | "completed" | "failed";
      issue_number: number | null;
      issue_url: string | null;
      has_result: boolean;
      result_path: string | null;
    }> => {
      return this.request<{
        status: "pending" | "in_progress" | "completed" | "failed";
        issue_number: number | null;
        issue_url: string | null;
        has_result: boolean;
        result_path: string | null;
      }>(`/api/github/review-status/${runId}/${step}`);
    },

    /**
     * Get issue status including linked PRs (for tracking Claude Code edits)
     */
    getIssueStatus: async (
      runId: string,
      issueNumber: number
    ): Promise<{
      issue_number: number;
      status: "open" | "in_progress" | "closed";
      state: string;
      issue_url: string | null;
      updated_at: string | null;
      pr_url: string | null;
      last_comment: string | null;
    }> => {
      return this.request<{
        issue_number: number;
        status: "open" | "in_progress" | "closed";
        state: string;
        issue_url: string | null;
        updated_at: string | null;
        pr_url: string | null;
        last_comment: string | null;
      }>(`/api/github/issue-status/${runId}/${issueNumber}`);
    },

    /**
     * Get pull request details
     */
    getPR: async (
      runId: string,
      prNumber: number
    ): Promise<{
      number: number;
      title: string;
      state: string;
      merged: boolean;
      mergeable: boolean | null;
      mergeable_state: string | null;
      url: string;
      head_branch: string | null;
      base_branch: string | null;
      user: string | null;
      additions: number;
      deletions: number;
      changed_files: number;
    }> => {
      return this.request<{
        number: number;
        title: string;
        state: string;
        merged: boolean;
        mergeable: boolean | null;
        mergeable_state: string | null;
        url: string;
        head_branch: string | null;
        base_branch: string | null;
        user: string | null;
        additions: number;
        deletions: number;
        changed_files: number;
      }>(`/api/github/pr/${runId}/${prNumber}`);
    },

    /**
     * Merge a pull request
     */
    mergePR: async (
      runId: string,
      prNumber: number,
      mergeMethod: "merge" | "squash" | "rebase" = "squash",
      commitTitle?: string,
      commitMessage?: string
    ): Promise<{
      merged: boolean;
      sha: string | null;
      message: string;
    }> => {
      return this.request<{
        merged: boolean;
        sha: string | null;
        message: string;
      }>(`/api/github/merge-pr/${runId}/${prNumber}`, {
        method: "POST",
        body: JSON.stringify({
          merge_method: mergeMethod,
          commit_title: commitTitle,
          commit_message: commitMessage,
        }),
      });
    },

    /**
     * List all branches in a repository
     */
    listBranches: async (
      repoUrl: string
    ): Promise<{
      branches: Array<{
        name: string;
        protected: boolean;
        commit_sha: string | null;
        commit_date: string | null;
        commit_message: string | null;
        commit_author: string | null;
        is_default: boolean;
        is_merged: boolean;
      }>;
      default_branch: string | null;
    }> => {
      return this.request<{
        branches: Array<{
          name: string;
          protected: boolean;
          commit_sha: string | null;
          commit_date: string | null;
          commit_message: string | null;
          commit_author: string | null;
          is_default: boolean;
          is_merged: boolean;
        }>;
        default_branch: string | null;
      }>("/api/github/list-branches", {
        method: "POST",
        body: JSON.stringify({ repo_url: repoUrl }),
      });
    },

    /**
     * Delete multiple branches from a repository
     * Protected branches (main, master, develop, release/*) are automatically skipped
     */
    deleteBranches: async (
      repoUrl: string,
      branches: string[]
    ): Promise<{
      deleted: string[];
      failed: Array<{ name: string; reason: string | null }>;
      skipped: Array<{ name: string; reason: string | null }>;
    }> => {
      return this.request<{
        deleted: string[];
        failed: Array<{ name: string; reason: string | null }>;
        skipped: Array<{ name: string; reason: string | null }>;
      }>("/api/github/branches", {
        method: "DELETE",
        body: JSON.stringify({ repo_url: repoUrl, branches }),
      });
    },
  };

  // ============================================
  // Settings API (API Keys & Model Configuration)
  // ============================================

  settings = {
    /**
     * 全サービスの設定一覧を取得
     */
    list: async (): Promise<ApiSettingsListResponse> => {
      return this.request<ApiSettingsListResponse>("/api/settings");
    },

    /**
     * 特定サービスの設定を取得
     */
    get: async (service: ServiceType): Promise<ApiSettingResponse> => {
      return this.request<ApiSettingResponse>(`/api/settings/${service}`);
    },

    /**
     * サービス設定を更新
     * api_key を指定しない場合は既存のキーを保持
     */
    update: async (
      service: ServiceType,
      data: ApiSettingUpdateRequest
    ): Promise<ApiSettingResponse> => {
      return this.request<ApiSettingResponse>(`/api/settings/${service}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },

    /**
     * サービス設定を削除（環境変数にフォールバック）
     */
    delete: async (service: ServiceType): Promise<{ message: string }> => {
      return this.request<{ message: string }>(`/api/settings/${service}`, {
        method: "DELETE",
      });
    },

    /**
     * サービス接続をテスト
     * api_key を指定しない場合は保存済みキーまたは環境変数を使用
     */
    test: async (
      service: ServiceType,
      apiKey?: string,
      model?: string
    ): Promise<ConnectionTestResponse> => {
      const params = new URLSearchParams();
      if (apiKey) params.set("api_key", apiKey);
      if (model) params.set("model", model);
      const query = params.toString();
      return this.request<ConnectionTestResponse>(
        `/api/settings/${service}/test${query ? `?${query}` : ""}`,
        { method: "POST" }
      );
    },
  };

  // ============================================
  // Articles API (Completed Articles Management)
  // ============================================

  articles = {
    /**
     * List completed articles with filtering and pagination
     */
    list: async (params?: {
      page?: number;
      limit?: number;
      keyword?: string;
      has_review?: boolean;
    }): Promise<ArticleListResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", params.page.toString());
      if (params?.limit) searchParams.set("limit", params.limit.toString());
      if (params?.keyword) searchParams.set("keyword", params.keyword);
      if (params?.has_review !== undefined) searchParams.set("has_review", params.has_review.toString());

      const query = searchParams.toString();
      return this.request<ArticleListResponse>(`/api/articles${query ? `?${query}` : ""}`);
    },

    /**
     * Get detailed article information
     */
    get: async (id: string): Promise<ArticleDetail> => {
      return this.request<ArticleDetail>(`/api/articles/${id}`);
    },

    /**
     * Get article content from a specific step
     */
    getContent: async (id: string, step: "step10" | "step11" | "step12"): Promise<Record<string, unknown>> => {
      return this.request<Record<string, unknown>>(`/api/articles/${id}/content/${step}`);
    },
  };
}

export const api = new ApiClient(API_BASE);
export default api;
