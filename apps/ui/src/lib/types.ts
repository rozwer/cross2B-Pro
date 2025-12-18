// ============================================
// Run Status Types
// ============================================

export type RunStatus =
  | "pending"
  | "running"
  | "waiting_approval"
  | "completed"
  | "failed"
  | "cancelled";

export type StepStatus = "pending" | "running" | "completed" | "failed" | "skipped";

// ============================================
// Model Configuration Types
// ============================================

export type LLMPlatform = "gemini" | "openai" | "anthropic";

export interface ModelConfig {
  platform: LLMPlatform;
  model: string;
  options: {
    grounding?: boolean;
    temperature?: number;
    max_tokens?: number;
  };
}

export interface ToolConfig {
  serp_fetch: boolean;
  page_fetch: boolean;
  url_verify: boolean;
  pdf_extract: boolean;
}

// ============================================
// Run Types
// ============================================

export interface RunInput {
  keyword: string;
  target_audience?: string;
  competitor_urls?: string[];
  additional_requirements?: string;
}

export interface StepModelConfig {
  step_id: string;
  platform: LLMPlatform;
  model: string;
  temperature: number;
  grounding: boolean;
  retry_limit: number;
  repair_enabled: boolean;
}

export interface CreateRunInput {
  input: RunInput;
  model_config: ModelConfig;
  step_configs?: StepModelConfig[];
  tool_config?: ToolConfig;
  options?: {
    retry_limit?: number;
    repair_enabled?: boolean;
  };
}

export interface RunSummary {
  id: string;
  status: RunStatus;
  current_step: string | null;
  keyword: string;
  model_config: ModelConfig;
  created_at: string;
  updated_at: string;
}

export interface Run {
  id: string;
  tenant_id: string;
  status: RunStatus;
  current_step: string | null;
  input: RunInput;
  model_config: ModelConfig;
  tool_config?: ToolConfig;
  options?: {
    retry_limit: number;
    repair_enabled: boolean;
  };
  steps: Step[];
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  error?: RunError;
}

export interface RunError {
  code: string;
  message: string;
  step?: string;
  details?: Record<string, unknown>;
}

// ============================================
// Step Types
// ============================================

export interface Step {
  id: string;
  run_id: string;
  step_name: string;
  status: StepStatus;
  attempts: StepAttempt[];
  started_at?: string;
  completed_at?: string;
  artifacts?: ArtifactRef[];
  validation_report?: ValidationReport;
}

export interface StepAttempt {
  id: string;
  step_id: string;
  attempt_num: number;
  status: "running" | "succeeded" | "failed";
  started_at: string;
  completed_at?: string;
  error?: StepError;
  repairs?: RepairLog[];
}

export interface StepError {
  type: "RETRYABLE" | "NON_RETRYABLE" | "VALIDATION_FAIL";
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface RepairLog {
  repair_type: string;
  applied_at: string;
  description: string;
}

// ============================================
// Artifact Types
// ============================================

export interface ArtifactRef {
  id: string;
  step_id: string;
  ref_path: string;
  digest: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface ArtifactContent {
  ref: ArtifactRef;
  content: string;
  encoding: "utf-8" | "base64";
}

// ============================================
// Validation Types
// ============================================

export interface ValidationReport {
  format: "json" | "csv" | "html" | "markdown";
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  checked_at: string;
}

export interface ValidationError {
  code: string;
  message: string;
  path?: string;
  line?: number;
}

export interface ValidationWarning {
  code: string;
  message: string;
  path?: string;
  suggestion?: string;
}

// ============================================
// Event Types (WebSocket)
// ============================================

export type ProgressEventType =
  | "step_started"
  | "step_completed"
  | "step_failed"
  | "step_retrying"
  | "repair_applied"
  | "approval_requested"
  | "run_completed"
  | "run_failed"
  | "error";

export interface ProgressEvent {
  type: ProgressEventType;
  run_id: string;
  step?: string;
  status?: StepStatus;
  attempt?: number;
  progress: number;
  message: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

// ============================================
// API Response Types
// ============================================

export interface ApiResponse<T> {
  data: T;
  meta?: {
    total?: number;
    page?: number;
    limit?: number;
  };
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

// ============================================
// Step Names (Workflow)
// ============================================

export const STEP_NAMES = [
  "step-1",
  "step0",
  "step1",
  "step3",
  "step2",
  "step3a",
  "step3b",
  "step3c",
  "step4",
  "step5",
  "step6",
  "step6.5",
  "step7a",
  "step7b",
  "step8",
  "step9",
  "step10",
] as const;

export type StepName = (typeof STEP_NAMES)[number];

export const STEP_LABELS: Record<string, string> = {
  "step-1": "入力",
  step0: "準備",
  step1: "分析",
  step3: "構成",
  step2: "調査",
  step3a: "並列処理A",
  step3b: "並列処理B",
  step3c: "並列処理C",
  step4: "執筆準備",
  step5: "本文生成",
  step6: "編集",
  "step6.5": "統合パッケージ",
  step7a: "HTML生成",
  step7b: "メタ情報",
  step8: "検証",
  step9: "最終調整",
  step10: "完了",
};

// ============================================
// Prompt Types (JSON file-based)
// ============================================

export interface PromptVariableInfo {
  required: boolean;
  type: string;
  description?: string;
  default?: string | number | boolean | object | unknown[];
}

/** JSON ファイルから取得するプロンプト */
export interface Prompt {
  step: string;
  version: number;
  content: string;
  variables: Record<string, PromptVariableInfo> | null;
}

export interface PromptListResponse {
  pack_id: string;
  prompts: Prompt[];
  total: number;
}

export interface UpdatePromptInput {
  content: string;
  variables?: Record<string, PromptVariableInfo>;
}

// ============================================
// Cost Types
// ============================================

export interface CostBreakdown {
  step: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost: number;
}

export interface CostResponse {
  run_id: string;
  total_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  breakdown: CostBreakdown[];
  currency: string;
}

// ============================================
// Config Types (from Backend)
// ============================================

export interface ProviderConfig {
  provider: LLMPlatform;
  default_model: string;
  available_models: string[];
  supports_grounding: boolean;
}

export interface StepDefaultConfig {
  step_id: string;
  label: string;
  description: string;
  ai_model: LLMPlatform;
  model_name: string;
  temperature: number;
  grounding: boolean;
  retry_limit: number;
  repair_enabled: boolean;
  is_configurable: boolean;
  recommended_model: LLMPlatform;
}

export interface ModelsConfigResponse {
  providers: ProviderConfig[];
  step_defaults: StepDefaultConfig[];
}

// ============================================
// Helper Functions
// ============================================

export function getStatusColor(status: RunStatus | StepStatus): string {
  switch (status) {
    case "pending":
      return "bg-gray-100 text-gray-800";
    case "running":
      return "bg-blue-100 text-blue-800";
    case "waiting_approval":
      return "bg-yellow-100 text-yellow-800";
    case "completed":
      return "bg-green-100 text-green-800";
    case "failed":
      return "bg-red-100 text-red-800";
    case "cancelled":
    case "skipped":
      return "bg-gray-100 text-gray-500";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

export function getStatusIcon(status: RunStatus | StepStatus): string {
  switch (status) {
    case "pending":
      return "○";
    case "running":
      return "◐";
    case "waiting_approval":
      return "⏸";
    case "completed":
      return "●";
    case "failed":
      return "✗";
    case "cancelled":
    case "skipped":
      return "○";
    default:
      return "○";
  }
}
