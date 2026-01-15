// ============================================
// Run Status Types
// ============================================

export type RunStatus =
  | "pending"
  | "workflow_starting"  // Temporal Workflow開始処理中（競合状態対策）
  | "running"
  | "paused"  // ユーザーによる一時停止（次ステップ開始前に停止）
  | "waiting_approval"
  | "waiting_image_input"  // Step11画像生成のユーザー入力待ち
  | "completed"
  | "failed"
  | "cancelled";

export type StepStatus = "pending" | "running" | "retrying" | "completed" | "failed" | "skipped";

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

// Legacy RunInput (for backward compatibility)
export interface LegacyRunInput {
  format_type: "legacy";  // Required for discriminated union
  keyword: string;
  target_audience?: string;
  competitor_urls?: string[];
  additional_requirements?: string;
}

// Type alias for backward compatibility
export type RunInput = LegacyRunInput;

// ============================================
// Article Hearing Types (New Input Format)
// ============================================

export type TargetCV = "inquiry" | "document_request" | "free_consultation" | "other";
export type KeywordStatus = "decided" | "undecided";
export type CompetitionLevel = "high" | "medium" | "low";
export type ArticleStyle = "standalone" | "topic_cluster";
export type WordCountMode = "manual" | "ai_seo_optimized" | "ai_readability" | "ai_balanced";
export type CTAType = "single" | "staged";
export type CTAPositionMode = "fixed" | "ratio" | "ai";

export interface BusinessInput {
  description: string;
  target_cv: TargetCV;
  target_cv_other?: string;
  target_audience: string;
  company_strengths: string;
}

export interface RelatedKeyword {
  keyword: string;
  volume?: string;
}

export interface SelectedKeyword {
  keyword: string;
  estimated_volume: string;
  estimated_competition: CompetitionLevel;
  relevance_score: number;
}

export interface KeywordInput {
  status: KeywordStatus;
  main_keyword?: string;
  monthly_search_volume?: string;
  competition_level?: CompetitionLevel;
  theme_topics?: string;
  selected_keyword?: SelectedKeyword;
  related_keywords?: RelatedKeyword[];
  /** Raw text for related keywords textarea (preserves line breaks during editing) */
  related_keywords_text?: string;
}

export interface StrategyInput {
  article_style: ArticleStyle;
  child_topics?: string[];
}

export interface WordCountInput {
  mode: WordCountMode;
  target?: number;
}

export interface SingleCTA {
  url: string;
  text: string;
  description: string;
}

export interface StagedCTAItem {
  url: string;
  text: string;
  description: string;
  position?: number;
}

export interface StagedCTA {
  early: StagedCTAItem;
  mid: StagedCTAItem;
  final: StagedCTAItem;
}

export interface CTAInput {
  type: CTAType;
  position_mode: CTAPositionMode;
  single?: SingleCTA;
  staged?: StagedCTA;
}

export interface ArticleHearingInput {
  format_type: "article_hearing_v1";  // Required for discriminated union
  business: BusinessInput;
  keyword: KeywordInput;
  strategy: StrategyInput;
  word_count: WordCountInput;
  cta: CTAInput;
  confirmed: boolean;
}

// Keyword Suggestion Types
export interface KeywordSuggestion {
  keyword: string;
  estimated_volume: string;
  estimated_competition: CompetitionLevel;
  relevance_score: number;
}

export interface KeywordSuggestionRequest {
  theme_topics: string;
  business_description: string;
  target_audience: string;
}

export interface KeywordSuggestionResponse {
  suggestions: KeywordSuggestion[];
  model_used: string;
  generated_at: string;
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

// Supports both legacy RunInput and new ArticleHearingInput
export interface CreateRunInput {
  input: RunInput | ArticleHearingInput;
  model_config: ModelConfig;
  step_configs?: StepModelConfig[];
  tool_config?: ToolConfig;
  options?: {
    retry_limit?: number;
    repair_enabled?: boolean;
  };
  // GitHub integration (Phase 2)
  github_repo_url?: string;
}

// Helper to check if input is ArticleHearingInput
export function isArticleHearingInput(
  input: RunInput | ArticleHearingInput
): input is ArticleHearingInput {
  return "business" in input && "keyword" in input && "strategy" in input;
}

// Helper to get keyword string from either input type
export function getKeywordFromInput(input: RunInput | ArticleHearingInput): string {
  if (isArticleHearingInput(input)) {
    // ArticleHearingInput: keyword is in keyword.main_keyword or keyword.selected_keyword
    const keywordInput = input.keyword;
    if (keywordInput.main_keyword) {
      return keywordInput.main_keyword;
    }
    if (keywordInput.selected_keyword?.keyword) {
      return keywordInput.selected_keyword.keyword;
    }
    return keywordInput.theme_topics || "";
  }
  // LegacyRunInput: keyword is a direct string
  return input.keyword;
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
  input: RunInput | ArticleHearingInput;
  model_config: ModelConfig;
  step_configs?: StepModelConfig[];
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
  // GitHub integration (Phase 3)
  github_repo_url?: string;
  github_dir_path?: string;
}

// ============================================
// GitHub Sync Status Types (Phase 5)
// ============================================

export type GitHubSyncStatus = "synced" | "diverged" | "unknown" | "github_only" | "minio_only";

export interface GitHubSyncStatusItem {
  step: string;
  status: GitHubSyncStatus;
  github_sha: string | null;
  minio_digest: string | null;
  synced_at: string | null;
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
  error_code?: string;  // ErrorCategory enum value (RETRYABLE, NON_RETRYABLE, etc.)
  error_message?: string;
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
  step_name: string;  // Human-readable step name (e.g., "step1", "step5")
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

export interface ArtifactUploadResponse {
  success: boolean;
  artifact_ref: ArtifactRef;
  backup_path: string | null;
  cache_invalidated: boolean;
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
  // Step-level events
  | "step_started"
  | "step_completed"
  | "step_failed"
  | "step_retrying"
  | "repair_applied"
  // Run-level events (from BE broadcast_run_update)
  | "run.started"
  | "run.approved"
  | "run.rejected"
  | "run.cancelled"
  | "run.image_generation_started"
  | "run.add_images_initiated"
  // Legacy run events (for backward compatibility)
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
// Event Log Types (DB Persisted)
// ============================================

export interface EventDetails {
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
}

export interface EventLogEntry {
  id: string;
  event_type: string;
  step?: string;
  payload: Record<string, unknown>;
  details?: EventDetails;
  created_at: string;
}

export interface EventLogFilter {
  step?: string;
  event_type?: string;
  since?: string;
  limit?: number;
  offset?: number;
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
  "step1.5",
  "step2",
  "step3",
  "step3a",
  "step3b",
  "step3c",
  "step3.5",
  "step4",
  "step5",
  "step6",
  "step6.5",
  "step7a",
  "step7b",
  "step8",
  "step9",
  "step10",
  "step11",
  "step12",
] as const;

export type StepName = (typeof STEP_NAMES)[number];

export const STEP_LABELS: Record<string, string> = {
  "step-1": "入力",
  step0: "準備",
  step1: "競合取得",
  "step1.5": "関連KW抽出",
  step1_5: "関連KW抽出",
  step2: "検証",
  step3: "構成",
  step3a: "3-A",
  step3b: "3-B",
  step3c: "3-C",
  "step3.5": "人間味生成",
  step3_5: "人間味生成",
  step4: "執筆準備",
  step5: "一次情報",
  step6: "強化",
  "step6.5": "統合",
  step6_5: "統合",
  step7a: "本文生成",
  step7b: "ブラッシュアップ",
  step8: "検証",
  step9: "最終調整",
  step10: "記事出力",
  step11: "画像生成",
  step12: "WP HTML",
};

// Helper to normalize step names (step6_5 -> step6.5)
export function normalizeStepName(stepName: string): string {
  return stepName.replace("_", ".");
}

// Get label for step name (handles both step6_5 and step6.5)
export function getStepLabel(stepName: string): string {
  const normalized = normalizeStepName(stepName);
  return STEP_LABELS[normalized] || STEP_LABELS[stepName] || stepName;
}

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
// Step11 Image Generation Types
// ============================================

export interface ImagePosition {
  article_number?: number | null;
  section_title: string;
  section_index: number;
  position: "before" | "after";
  source_text: string;
  description: string;
}

export interface Section {
  level: number | string;  // Backend returns number (2, 3), but may be string in some contexts
  title: string;
  start_pos?: number;  // Optional: not always returned by analyze_positions
  section_index?: number;
  section_key?: string;
  article_number?: number;
  display_title?: string;
}

export interface GeneratedImage {
  index: number;
  position: ImagePosition;
  user_instruction: string;
  generated_prompt: string;
  image_path: string;
  image_digest: string;
  image_base64: string;
  alt_text: string;
  mime_type: string;
  file_size: number;
  retry_count: number;
  accepted: boolean;
  article_number?: number | null;
}

export type Step11Phase =
  | "waiting_11A"  // 設定入力待ち
  | "11B_analyzing"  // 位置分析中
  | "waiting_11B"  // 位置確認待ち
  | "waiting_11C"  // 画像指示待ち
  | "11D_generating"  // 画像生成中
  | "waiting_11D"  // 画像確認待ち
  | "11E_inserting"  // 挿入中
  | "waiting_11E"  // プレビュー確認待ち
  | "completed"
  | "skipped";

// Helper to determine current step11 phase from current_step
export function getStep11Phase(currentStep: string | null): Step11Phase | null {
  if (!currentStep) return null;

  const phaseMap: Record<string, Step11Phase> = {
    waiting_image_generation: "waiting_11A",
    step11_analyzing: "11B_analyzing",
    step11_position_review: "waiting_11B",
    step11_image_instructions: "waiting_11C",
    step11_generating: "11D_generating",
    step11_image_review: "waiting_11D",
    step11_inserting: "11E_inserting",
    step11_preview: "waiting_11E",
  };

  return phaseMap[currentStep] || null;
}

// ============================================
// Step12 WordPress HTML Generation Types
// ============================================

export interface ArticleMetadata {
  title: string;
  meta_description: string;
  focus_keyword: string;
  word_count: number;
  slug: string;
}

export interface WordPressArticleResponse {
  article_number: number;
  filename: string;
  gutenberg_blocks: string;
  metadata?: ArticleMetadata;
}

export interface Step12PreviewResponse {
  articles: WordPressArticleResponse[];
  common_assets: Record<string, unknown>;
  generation_metadata: Record<string, unknown>;
  preview_available: boolean;
}

export interface Step12StatusResponse {
  status: "pending" | "completed" | "not_ready";
  phase: "ready_to_generate" | "completed" | "waiting_for_step10";
  articles_count: number;
  generated_at: string | null;
}

export interface Step12GenerateResponse {
  success: boolean;
  output_path: string;
  articles_count: number;
  message: string;
}

// ============================================
// Helper Functions
// ============================================

export function getStatusColor(status: RunStatus | StepStatus): string {
  switch (status) {
    case "pending":
    case "workflow_starting":
      return "bg-gray-100 text-gray-800";
    case "running":
      return "bg-blue-100 text-blue-800";
    case "retrying":
      return "bg-orange-100 text-orange-800";
    case "paused":
      return "bg-amber-100 text-amber-800";
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
    case "workflow_starting":
      return "○";
    case "running":
      return "◐";
    case "retrying":
      return "↻";
    case "paused":
      return "⏸";
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

// ============================================
// Hearing Template Types
// ============================================

export interface HearingTemplateData {
  business: BusinessInput;
  keyword: KeywordInput;
  strategy: StrategyInput;
  word_count: WordCountInput;
  cta: CTAInput;
}

export interface HearingTemplate {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  data: HearingTemplateData;
  created_at: string;
  updated_at: string;
}

export interface HearingTemplateCreate {
  name: string;
  description?: string;
  data: HearingTemplateData;
}

export interface HearingTemplateUpdate {
  name?: string;
  description?: string;
  data?: HearingTemplateData;
}

export interface HearingTemplateList {
  items: HearingTemplate[];
  total: number;
  limit: number;
  offset: number;
}

// ============================================
// Step3 Review Types (REQ-01 ~ REQ-05)
// ============================================

/** Valid Step3 step names */
export type Step3StepName = "step3a" | "step3b" | "step3c";

/** Individual step review item */
export interface Step3ReviewItem {
  step: Step3StepName;
  accepted: boolean;
  retry: boolean;
  retry_instruction: string;
}

/** Request body for Step3 review */
export interface Step3ReviewInput {
  reviews: Step3ReviewItem[];
}

/** Response from Step3 review endpoint */
export interface Step3ReviewResponse {
  success: boolean;
  retrying: string[];
  approved: string[];
  next_action: "waiting_retry_completion" | "proceed_to_step3_5" | "waiting_approval";
  retry_counts: Record<string, number>;
}

/** Extended reject input with retry instructions */
export interface RejectWithRetryInput {
  reason: string;
  retry_with_instructions: boolean;
  step_instructions: Record<Step3StepName, string>;
}

// ============================================
// API Settings Types
// ============================================

/** Supported external services */
export type ServiceType = "gemini" | "openai" | "anthropic" | "serp" | "google_ads" | "github";

/** LLM provider services */
export type LLMServiceType = "gemini" | "openai" | "anthropic";

/** Service-specific configuration */
export interface ServiceConfig {
  grounding?: boolean;
  temperature?: number;
}

/** API setting response */
export interface ApiSettingResponse {
  service: ServiceType;
  api_key_masked: string | null;
  default_model: string | null;
  config: ServiceConfig | null;
  is_active: boolean;
  verified_at: string | null;
  env_fallback: boolean;
}

/** API settings list response */
export interface ApiSettingsListResponse {
  settings: ApiSettingResponse[];
}

/** API setting update request */
export interface ApiSettingUpdateRequest {
  api_key?: string;
  default_model?: string;
  config?: ServiceConfig;
  is_active?: boolean;
}

/** Connection test response */
export interface ConnectionTestResponse {
  success: boolean;
  service: string;
  latency_ms: number | null;
  error_message: string | null;
  details: Record<string, unknown> | null;
}
