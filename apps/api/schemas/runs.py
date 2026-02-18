"""Run-related Pydantic models for API requests and responses."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Discriminator, Field, Tag, field_validator

from .article_hearing import ArticleHearingInput
from .enums import ErrorType, RunStatus, StepAttemptStatus, StepStatus

# Valid step IDs for workflow - shared with apps/api/services/runs.py
VALID_STEP_IDS: frozenset[str] = frozenset(
    [
        "step-1",
        "step0",
        "step1",
        "step1_5",
        "step2",
        "step3",
        "step3a",
        "step3b",
        "step3c",
        "step3_5",
        "step4",
        "step5",
        "step6",
        "step6_5",
        "step7a",
        "step7b",
        "step8",
        "step9",
        "step10",
        "step11",
        "step12",
    ]
)


class ModelConfigOptions(BaseModel):
    """Model configuration options."""

    grounding: bool | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class ModelConfig(BaseModel):
    """LLM model configuration."""

    platform: str  # gemini, openai, anthropic
    model: str
    options: ModelConfigOptions = Field(default_factory=ModelConfigOptions)


# Default model configuration for cloning runs or when no config is provided
DEFAULT_MODEL_CONFIG: dict[str, str | dict[str, str]] = {
    "platform": "gemini",
    "model": "gemini-3-pro-preview",
    "options": {},
}


class ToolConfig(BaseModel):
    """Tool configuration."""

    serp_fetch: bool = True
    page_fetch: bool = True
    url_verify: bool = True
    pdf_extract: bool = False


class LegacyRunInput(BaseModel):
    """Legacy run input data (backward compatibility).

    VULN-016: 明確な型識別のためformat_typeフィールドを追加
    """

    format_type: Literal["legacy"] = "legacy"
    keyword: str
    target_audience: str | None = None
    competitor_urls: list[str] | None = None
    additional_requirements: str | None = None


# VULN-016: Discriminated Union for type safety
# format_typeフィールドで明確に型を識別
def _get_input_discriminator(v: Any) -> str:
    """Determine input type from format_type field."""
    if isinstance(v, dict):
        return v.get("format_type", "legacy")
    return getattr(v, "format_type", "legacy")


RunInput = Annotated[
    Annotated[LegacyRunInput, Tag("legacy")] | Annotated[ArticleHearingInput, Tag("article_hearing_v1")],
    Discriminator(_get_input_discriminator),
]


class RunOptions(BaseModel):
    """Run execution options."""

    retry_limit: int = 3
    repair_enabled: bool = True
    enable_step1_approval: bool = True  # 競合取得・関連KW抽出後の承認待ちを有効化


class StepModelConfig(BaseModel):
    """Per-step model configuration - matches UI StepModelConfig."""

    step_id: str
    platform: str  # gemini, openai, anthropic
    model: str
    temperature: float = 0.7
    grounding: bool = False
    retry_limit: int = 3
    repair_enabled: bool = True


class CreateRunInput(BaseModel):
    """Request to create a new run - supports both legacy and new input formats.

    For legacy format:
        input: { format_type: "legacy", keyword: "...", target_audience: "...", ... }

    For new format (ArticleHearingInput):
        input: { format_type: "article_hearing_v1", business: {...}, keyword: {...}, ... }

    VULN-016: Discriminated Union による型安全性の向上
    format_type フィールドで明確に入力形式を識別
    """

    # VULN-016: Discriminated Union で型を識別
    input: RunInput
    model_config_data: ModelConfig = Field(alias="model_config")
    step_configs: list[StepModelConfig] | None = None
    tool_config: ToolConfig | None = None
    options: RunOptions | None = None
    # GitHub integration (Phase 2)
    github_repo_url: str | None = Field(default=None, description="GitHub repository URL for artifact storage")

    class Config:
        populate_by_name = True

    @field_validator("step_configs")
    @classmethod
    def validate_step_configs(cls, v: list[StepModelConfig] | None) -> list[StepModelConfig] | None:
        """Validate step_configs for duplicate and invalid step_ids."""
        if v is None:
            return v

        seen_step_ids: set[str] = set()
        for config in v:
            # Check for duplicate step_ids
            if config.step_id in seen_step_ids:
                raise ValueError(f"Duplicate step_id: {config.step_id}")
            seen_step_ids.add(config.step_id)

            # Check for invalid step_ids
            if config.step_id not in VALID_STEP_IDS:
                raise ValueError(f"Invalid step_id: {config.step_id}. Valid step_ids: {sorted(VALID_STEP_IDS)}")

        return v

    def get_normalized_input(self) -> dict[str, Any]:
        """Normalize input to a consistent format for storage and workflow."""
        if isinstance(self.input, ArticleHearingInput):
            # New format: store full structure and also extract legacy fields
            # Use mode="json" to ensure HttpUrl and other types are JSON serializable
            return {
                "format": "article_hearing_v1",
                "data": self.input.model_dump(mode="json"),
                # Legacy fields for backward compatibility
                "keyword": self.input.get_effective_keyword(),
                "target_audience": self.input.business.target_audience,
                "competitor_urls": None,
                "additional_requirements": self.input._build_additional_requirements(),
            }
        else:
            # Legacy format
            return {
                "format": "legacy",
                "keyword": self.input.keyword,
                "target_audience": self.input.target_audience,
                "competitor_urls": self.input.competitor_urls,
                "additional_requirements": self.input.additional_requirements,
            }

    def get_effective_keyword(self) -> str:
        """Get the effective keyword from either input format."""
        if isinstance(self.input, ArticleHearingInput):
            return self.input.get_effective_keyword()
        return self.input.keyword


class RejectRunInput(BaseModel):
    """Request body for rejecting a run.

    Supports two modes:
    1. Simple rejection: reason only → workflow terminates with failed status
    2. Rejection with retry: reason + step_instructions → step3 retries with feedback
    """

    reason: str = ""
    # Step3 指示付きリトライ用（REQ-01）
    retry_with_instructions: bool = False
    step_instructions: dict[str, str] | None = None  # {"step3a": "修正指示...", ...}


# Step3 Review Types (REQ-01 ~ REQ-05)
STEP3_VALID_STEPS: frozenset[str] = frozenset(["step3a", "step3b", "step3c"])
STEP3_RETRY_LIMIT: int = 3


class Step3ReviewItem(BaseModel):
    """Individual step review item for Step3 (3A/3B/3C).

    REQ-02: ステップ個別リトライ
    """

    step: str  # step3a, step3b, step3c
    accepted: bool
    retry: bool = False
    retry_instruction: str = ""

    @field_validator("step")
    @classmethod
    def validate_step(cls, v: str) -> str:
        """Validate step is one of step3a, step3b, step3c."""
        if v not in STEP3_VALID_STEPS:
            raise ValueError(f"Invalid step: {v}. Must be one of: {sorted(STEP3_VALID_STEPS)}")
        return v

    @field_validator("retry_instruction")
    @classmethod
    def validate_retry_instruction(cls, v: str, info: Any) -> str:
        """Ensure retry_instruction is provided when retry is True."""
        # Note: Pydantic v2 uses info.data instead of values
        data = info.data if hasattr(info, "data") else {}
        if data.get("retry") and not v:
            raise ValueError("retry_instruction is required when retry is True")
        return v


class Step3ReviewInput(BaseModel):
    """Request body for Step3 review (REQ-01 ~ REQ-05).

    Allows individual approval/retry for each step in the parallel phase (3A/3B/3C).
    Like Step11's image review, users can provide feedback for retry.
    """

    reviews: list[Step3ReviewItem]

    @field_validator("reviews")
    @classmethod
    def validate_reviews(cls, v: list[Step3ReviewItem]) -> list[Step3ReviewItem]:
        """Validate reviews list has unique steps."""
        seen_steps: set[str] = set()
        for item in v:
            if item.step in seen_steps:
                raise ValueError(f"Duplicate step in reviews: {item.step}")
            seen_steps.add(item.step)
        return v


class Step3ReviewResponse(BaseModel):
    """Response for Step3 review request."""

    success: bool
    retrying: list[str] = []  # Steps that will be retried
    approved: list[str] = []  # Steps that were approved
    next_action: str  # "waiting_retry_completion" | "proceed_to_step3_5" | "waiting_approval"
    retry_counts: dict[str, int] = {}  # Current retry count per step


class StepError(BaseModel):
    """Step error information."""

    type: ErrorType
    code: str
    message: str
    details: dict[str, Any] | None = None


class RepairLog(BaseModel):
    """Repair action log."""

    repair_type: str
    applied_at: str
    description: str


class StepAttempt(BaseModel):
    """Step attempt record."""

    id: str
    step_id: str
    attempt_num: int
    status: StepAttemptStatus
    started_at: str
    completed_at: str | None = None
    error: StepError | None = None
    repairs: list[RepairLog] | None = None


class ValidationError(BaseModel):
    """Validation error."""

    code: str
    message: str
    path: str | None = None
    line: int | None = None


class ValidationWarning(BaseModel):
    """Validation warning."""

    code: str
    message: str
    path: str | None = None
    suggestion: str | None = None


class ValidationReport(BaseModel):
    """Validation report matching UI expectations."""

    format: str  # json, csv, html, markdown
    valid: bool
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationWarning] = Field(default_factory=list)
    checked_at: str


class ArtifactRef(BaseModel):
    """Artifact reference matching UI ArtifactRef."""

    id: str
    step_id: str
    step_name: str = ""  # Human-readable step name for display
    ref_path: str
    digest: str
    content_type: str
    size_bytes: int
    created_at: str


class ArtifactContent(BaseModel):
    """Artifact content matching UI ArtifactContent."""

    ref: ArtifactRef
    content: str
    encoding: str = "utf-8"  # utf-8 or base64


class StepResponse(BaseModel):
    """Step response matching UI Step type."""

    id: str
    run_id: str
    step_name: str
    status: StepStatus
    attempts: list[StepAttempt] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    error_code: str | None = None  # ErrorCategory enum value (RETRYABLE, NON_RETRYABLE, etc.)
    error_message: str | None = None
    artifacts: list[ArtifactRef] | None = None
    validation_report: ValidationReport | None = None


class StepUpdateRequest(BaseModel):
    """Request to update step status (internal API)."""

    run_id: str
    step_name: str
    status: Literal["running", "completed", "failed"]
    error_message: str | None = None
    retry_count: int = 0
    tenant_id: str | None = None  # Optional: passed from Worker, or looked up from run


class WSBroadcastRequest(BaseModel):
    """Request to broadcast WebSocket event (internal API)."""

    run_id: str
    step: str
    event_type: str = "step_progress"
    status: str = "in_progress"
    progress: int = 0
    message: str = ""
    details: dict[str, Any] | None = None


class AuditLogRequest(BaseModel):
    """Request to write audit log (internal API)."""

    tenant_id: str
    run_id: str
    step_name: str
    action: str
    details: dict[str, Any] | None = None


class RunError(BaseModel):
    """Run error information."""

    code: str
    message: str
    step: str | None = None
    details: dict[str, Any] | None = None


class RetryRecommendation(BaseModel):
    """リトライ推奨情報。

    ステップ失敗時にどのようにリトライすべきかを推奨する。
    - retry_same: 同一ステップをリトライ（一時的障害、設定変更後）
    - retry_previous: 入力元ステップからリトライ（入力データ品質問題）
    """

    action: Literal["retry_same", "retry_previous"]
    target_step: str
    reason: str


class RunSummary(BaseModel):
    """Run summary for list view."""

    id: str
    status: RunStatus
    current_step: str | None
    keyword: str
    model_config_data: ModelConfig = Field(alias="model_config")
    created_at: str
    updated_at: str

    class Config:
        populate_by_name = True


class RunResponse(BaseModel):
    """Full run response matching UI Run type."""

    id: str
    tenant_id: str
    status: RunStatus
    current_step: str | None
    input: RunInput
    model_config_data: ModelConfig = Field(alias="model_config")
    step_configs: list[StepModelConfig] | None = None
    tool_config: ToolConfig | None = None
    options: RunOptions | None = None
    steps: list[StepResponse] = Field(default_factory=list)
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error: RunError | None = None
    # GitHub integration (Phase 3)
    github_repo_url: str | None = None
    github_dir_path: str | None = None
    # GitHub Fix Guidance: resume後に同一ステップで再失敗した場合にTrue
    needs_github_fix: bool = False
    last_resumed_step: str | None = None
    fix_issue_number: int | None = None
    # Retry Recommendation: 失敗時の推奨リトライ方法
    retry_recommendation: RetryRecommendation | None = None

    class Config:
        populate_by_name = True


class EventResponse(BaseModel):
    """Event response for audit log."""

    id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete operation."""

    deleted_count: int
    failed_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
