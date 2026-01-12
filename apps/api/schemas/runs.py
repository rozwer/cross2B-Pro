"""Run-related Pydantic models for API requests and responses."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

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
    "model": "gemini-2.0-flash",
    "options": {},
}


class ToolConfig(BaseModel):
    """Tool configuration."""

    serp_fetch: bool = True
    page_fetch: bool = True
    url_verify: bool = True
    pdf_extract: bool = False


class LegacyRunInput(BaseModel):
    """Legacy run input data (backward compatibility)."""

    keyword: str
    target_audience: str | None = None
    competitor_urls: list[str] | None = None
    additional_requirements: str | None = None


# Type alias for backward compatibility
RunInput = LegacyRunInput | ArticleHearingInput


class RunOptions(BaseModel):
    """Run execution options."""

    retry_limit: int = 3
    repair_enabled: bool = True


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
        input: { keyword: "...", target_audience: "...", ... }

    For new format (ArticleHearingInput):
        input: { business: {...}, keyword: {...}, strategy: {...}, ... }
    """

    # Accept either LegacyRunInput or ArticleHearingInput
    input: LegacyRunInput | ArticleHearingInput
    model_config_data: ModelConfig = Field(alias="model_config")
    step_configs: list[StepModelConfig] | None = None
    tool_config: ToolConfig | None = None
    options: RunOptions | None = None

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
    """Request body for rejecting a run."""

    reason: str = ""


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
