"""Activity output schemas."""

from apps.worker.activities.schemas.step0 import Step0Output
from apps.worker.activities.schemas.step1 import (
    CompetitorPage,
    FailedUrl,
    FetchStats,
    Step1Output,
)
from apps.worker.activities.schemas.step2 import (
    RejectedRecord,
    Step2Output,
    ValidatedCompetitor,
    ValidationIssue,
    ValidationSummary,
)
from apps.worker.activities.schemas.step3a import (
    SearchIntent,
    Step3aOutput,
    UserPersona,
)
from apps.worker.activities.schemas.step3b import (
    KeywordCluster,
    KeywordItem,
    Step3bOutput,
)
from apps.worker.activities.schemas.step3c import (
    CompetitorProfile,
    DifferentiationStrategy,
    GapOpportunity,
    Step3cOutput,
)
from apps.worker.activities.schemas.step4 import (
    OutlineMetrics,
    OutlineQuality,
    OutlineSection,
    Step4Output,
)
from apps.worker.activities.schemas.step5 import (
    CollectionStats,
    PrimarySource,
    Step5Output,
)
from apps.worker.activities.schemas.step6 import (
    EnhancedOutlineMetrics,
    EnhancedOutlineQuality,
    EnhancedSection,
    EnhancementSummary,
    Step6Output,
)
from apps.worker.activities.schemas.step6_5 import (
    ComprehensiveBlueprint,
    FourPillarsFinalCheck,
    InputSummary,
    PackageQuality,
    ReferenceData,
    SectionBlueprint,
    SectionExecutionInstruction,
    Step6_5Output,
    VisualElementInstruction,
)
from apps.worker.activities.schemas.step7a import (
    DraftQuality,
    DraftQualityMetrics,
    DraftSection,
    GenerationStats,
    Step7aOutput,
)
from apps.worker.activities.schemas.step7b import (
    PolishChange,
    PolishMetrics,
    Step7bOutput,
)
from apps.worker.activities.schemas.step8 import (
    Claim,
    FAQItem,
    Step8Output,
    VerificationResult,
    VerificationSummary,
)
from apps.worker.activities.schemas.step9 import (
    RewriteChange,
    RewriteMetrics,
    Step9Output,
)
from apps.worker.activities.schemas.step10 import (
    ARTICLE_WORD_COUNT_TARGETS,
    ArticleStats,
    ArticleVariation,
    ArticleVariationType,
    FourPillarsChecklist,
    HTMLValidationResult,
    PublicationChecklistDetailed,
    PublicationReadiness,
    SectionWordCount,
    SEOChecklist,
    Step10Metadata,
    Step10Output,
    StructuredData,
    TechnicalChecklist,
    WordCountReport,
)
from apps.worker.activities.schemas.step11 import (
    GeneratedImage,
    ImageGenerationRequest,
    ImageInsertionPosition,
    PositionAnalysisResult,
    Step11Config,
    Step11Output,
    Step11State,
    Step11SubStep,
)

__all__ = [
    # Step0
    "Step0Output",
    # Step1
    "CompetitorPage",
    "FetchStats",
    "FailedUrl",
    "Step1Output",
    # Step2
    "ValidatedCompetitor",
    "ValidationIssue",
    "RejectedRecord",
    "ValidationSummary",
    "Step2Output",
    # Step3a
    "SearchIntent",
    "UserPersona",
    "Step3aOutput",
    # Step3b
    "KeywordItem",
    "KeywordCluster",
    "Step3bOutput",
    # Step3c
    "CompetitorProfile",
    "DifferentiationStrategy",
    "GapOpportunity",
    "Step3cOutput",
    # Step4
    "OutlineSection",
    "OutlineQuality",
    "OutlineMetrics",
    "Step4Output",
    # Step5
    "PrimarySource",
    "CollectionStats",
    "Step5Output",
    # Step6
    "EnhancedSection",
    "EnhancementSummary",
    "EnhancedOutlineMetrics",
    "EnhancedOutlineQuality",
    "Step6Output",
    # Step6.5
    "InputSummary",
    "SectionBlueprint",
    "PackageQuality",
    "Step6_5Output",
    "ReferenceData",
    "ComprehensiveBlueprint",
    "SectionExecutionInstruction",
    "VisualElementInstruction",
    "FourPillarsFinalCheck",
    # Step7a
    "DraftSection",
    "DraftQualityMetrics",
    "DraftQuality",
    "GenerationStats",
    "Step7aOutput",
    # Step7b
    "PolishChange",
    "PolishMetrics",
    "Step7bOutput",
    # Step8
    "Claim",
    "VerificationResult",
    "VerificationSummary",
    "FAQItem",
    "Step8Output",
    # Step9
    "RewriteChange",
    "RewriteMetrics",
    "Step9Output",
    # Step10
    "ARTICLE_WORD_COUNT_TARGETS",
    "ArticleStats",
    "ArticleVariation",
    "ArticleVariationType",
    "FourPillarsChecklist",
    "HTMLValidationResult",
    "PublicationChecklistDetailed",
    "PublicationReadiness",
    "SEOChecklist",
    "SectionWordCount",
    "Step10Metadata",
    "Step10Output",
    "StructuredData",
    "TechnicalChecklist",
    "WordCountReport",
    # Step11
    "GeneratedImage",
    "ImageGenerationRequest",
    "ImageInsertionPosition",
    "PositionAnalysisResult",
    "Step11Config",
    "Step11Output",
    "Step11State",
    "Step11SubStep",
]
