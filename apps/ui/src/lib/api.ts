import type {
  Run,
  RunSummary,
  CreateRunInput,
  ArtifactRef,
  ArtifactContent,
  PaginatedResponse,
  ApiError,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        error: {
          code: 'UNKNOWN_ERROR',
          message: `HTTP ${response.status}: ${response.statusText}`,
        },
      }));
      throw new Error(error.error.message);
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
      if (params?.page) searchParams.set('page', params.page.toString());
      if (params?.limit) searchParams.set('limit', params.limit.toString());
      if (params?.status) searchParams.set('status', params.status);

      const query = searchParams.toString();
      // Backend returns { runs, total, limit, offset } but we need { items, total, ... }
      const response = await this.request<{
        runs: RunSummary[];
        total: number;
        limit: number;
        offset: number;
      }>(`/api/runs${query ? `?${query}` : ''}`);

      return {
        items: response.runs ?? [],
        total: response.total ?? 0,
        page: Math.floor((response.offset ?? 0) / (response.limit ?? 50)) + 1,
        limit: response.limit ?? 50,
        has_more: (response.offset ?? 0) + (response.runs?.length ?? 0) < (response.total ?? 0),
      };
    },

    get: async (id: string): Promise<Run> => {
      return this.request<Run>(`/api/runs/${id}`);
    },

    create: async (data: CreateRunInput): Promise<Run> => {
      return this.request<Run>('/api/runs', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    approve: async (id: string): Promise<{ success: boolean }> => {
      return this.request<{ success: boolean }>(`/api/runs/${id}/approve`, {
        method: 'POST',
      });
    },

    reject: async (
      id: string,
      reason: string
    ): Promise<{ success: boolean }> => {
      return this.request<{ success: boolean }>(`/api/runs/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      });
    },

    cancel: async (id: string): Promise<{ success: boolean }> => {
      return this.request<{ success: boolean }>(`/api/runs/${id}`, {
        method: 'DELETE',
      });
    },

    retry: async (
      id: string,
      step: string
    ): Promise<{ success: boolean; new_attempt_id: string }> => {
      return this.request<{ success: boolean; new_attempt_id: string }>(
        `/api/runs/${id}/retry/${step}`,
        { method: 'POST' }
      );
    },

    resume: async (
      id: string,
      step: string
    ): Promise<{ success: boolean; new_run_id: string }> => {
      return this.request<{ success: boolean; new_run_id: string }>(
        `/api/runs/${id}/resume/${step}`,
        { method: 'POST' }
      );
    },

    clone: async (id: string, overrides?: Partial<CreateRunInput>): Promise<Run> => {
      return this.request<Run>(`/api/runs/${id}/clone`, {
        method: 'POST',
        body: JSON.stringify(overrides || {}),
      });
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
      return this.request<ArtifactContent>(
        `/api/runs/${runId}/files/${artifactId}/content`
      );
    },

    getPreviewUrl: (runId: string): string => {
      return `${this.baseUrl}/api/runs/${runId}/preview`;
    },
  };

  // ============================================
  // Events API
  // ============================================

  events = {
    list: async (
      runId: string,
      params?: { step?: string; limit?: number }
    ): Promise<
      Array<{
        id: string;
        event_type: string;
        payload: Record<string, unknown>;
        created_at: string;
      }>
    > => {
      const searchParams = new URLSearchParams();
      if (params?.step) searchParams.set('step', params.step);
      if (params?.limit) searchParams.set('limit', params.limit.toString());

      const query = searchParams.toString();
      return this.request(`/api/runs/${runId}/events${query ? `?${query}` : ''}`);
    },
  };
}

export const api = new ApiClient(API_BASE);
export default api;
