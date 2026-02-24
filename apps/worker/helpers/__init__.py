"""Helper utilities for worker activities."""

# CTA placement positions (word count offsets)
CTA_POSITION_EARLY = 650
CTA_POSITION_MID = 2800
CTA_POSITION_FINAL_OFFSET = 500
CTA_SPEC_KEY = "cta_specification"

from apps.worker.helpers.checkpoint_manager import CheckpointManager
from apps.worker.helpers.content_metrics import ContentMetrics
from apps.worker.helpers.input_validator import InputValidator
from apps.worker.helpers.output_parser import OutputParser
from apps.worker.helpers.quality_retry_loop import QualityRetryLoop, RetryLoopResult
from apps.worker.helpers.quality_validator import (
    ArticleStrategyValidator,
    CompletenessValidator,
    CompositeValidator,
    FourPillarsValidator,
    KeywordValidator,
    QualityValidator,
    RequiredElementsValidator,
    StructureValidator,
)
from apps.worker.helpers.schemas import (
    CheckpointMetadata,
    CompletenessResult,
    InputValidationResult,
    MarkdownMetrics,
    ParseResult,
    QualityResult,
    StepOutputBase,
    TextMetrics,
)

__all__ = [
    # Validators
    "InputValidator",
    "OutputParser",
    "QualityValidator",
    "RequiredElementsValidator",
    "StructureValidator",
    "CompletenessValidator",
    "KeywordValidator",
    "CompositeValidator",
    # blog.System Ver8.3 バリデータ
    "FourPillarsValidator",
    "ArticleStrategyValidator",
    # Metrics & Checkpoint
    "ContentMetrics",
    "CheckpointManager",
    # Retry Loop
    "QualityRetryLoop",
    "RetryLoopResult",
    # Schemas - Quality
    "QualityResult",
    "InputValidationResult",
    "CompletenessResult",
    # Schemas - Parse
    "ParseResult",
    # Schemas - Metrics
    "TextMetrics",
    "MarkdownMetrics",
    # Schemas - Checkpoint
    "CheckpointMetadata",
    # Schemas - Output
    "StepOutputBase",
    # CTA Constants
    "CTA_POSITION_EARLY",
    "CTA_POSITION_MID",
    "CTA_POSITION_FINAL_OFFSET",
    "CTA_SPEC_KEY",
]
