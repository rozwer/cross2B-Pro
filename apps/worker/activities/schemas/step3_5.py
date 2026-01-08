"""Step 3.5: Human Touch Generation output schemas.

Generates emotional analysis, human-like expressions, and experience episodes
to make content more relatable and engaging.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.worker.helpers.schemas import StepOutputBase


class EmotionalAnalysis(BaseModel):
    """Emotional analysis of the target audience."""

    primary_emotion: str = Field(
        default="",
        description="Primary emotion the content should evoke",
    )
    secondary_emotions: list[str] = Field(
        default_factory=list,
        description="Secondary emotions to address",
    )
    pain_points: list[str] = Field(
        default_factory=list,
        description="User pain points and frustrations",
    )
    desires: list[str] = Field(
        default_factory=list,
        description="User desires and aspirations",
    )


class HumanTouchPattern(BaseModel):
    """A pattern for adding human touch to content."""

    type: Literal["experience", "emotion", "empathy"] = Field(
        default="experience",
        description="Type: experience, emotion, empathy",
    )
    content: str = Field(
        default="",
        description="The actual human-touch content",
    )
    placement_suggestion: str = Field(
        default="",
        description="Where in the article this should be placed",
    )


class ExperienceEpisode(BaseModel):
    """A relatable experience episode."""

    scenario: str = Field(
        default="",
        description="The situation or context",
    )
    narrative: str = Field(
        default="",
        description="The story or experience narrative",
    )
    lesson: str = Field(
        default="",
        description="The takeaway or lesson learned",
    )


class PhaseEmotionalData(BaseModel):
    """Phase-specific emotional data for blog.System integration.

    Each phase (認知/検討/行動) has distinct emotional characteristics.
    """

    dominant_emotion: str = Field(
        default="",
        description="Dominant emotion for this phase (e.g., 不安/焦り/危機感 for phase1)",
    )
    empathy_statements: list[str] = Field(
        default_factory=list,
        description="Empathy statements for this phase (target: 3 statements)",
    )
    experience_episodes: list[ExperienceEpisode] = Field(
        default_factory=list,
        description="Experience episodes for this phase (target: 2-3 episodes)",
    )


class PhaseEmotionalMap(BaseModel):
    """Three-phase emotional mapping for blog.System integration.

    Maps emotional content to the three user journey phases:
    - phase1 (認知): Awareness - 不安/焦り/危機感
    - phase2 (検討): Consideration - 冷静/分析的
    - phase3 (行動): Action - 期待/決意
    """

    phase1: PhaseEmotionalData = Field(
        default_factory=PhaseEmotionalData,
        description="Phase 1 (認知/Awareness) emotional data",
    )
    phase2: PhaseEmotionalData = Field(
        default_factory=PhaseEmotionalData,
        description="Phase 2 (検討/Consideration) emotional data",
    )
    phase3: PhaseEmotionalData = Field(
        default_factory=PhaseEmotionalData,
        description="Phase 3 (行動/Action) emotional data",
    )


class BehavioralEconomicsHooks(BaseModel):
    """Behavioral economics hooks based on the 6 principles.

    Generates persuasive content hooks using behavioral economics:
    - Loss aversion (損失回避)
    - Social proof (社会的証明)
    - Authority (権威)
    - Scarcity (希少性)
    """

    loss_aversion_hook: str = Field(
        default="",
        description="Hook leveraging loss aversion principle (損失回避)",
    )
    social_proof_hook: str = Field(
        default="",
        description="Hook leveraging social proof principle (社会的証明)",
    )
    authority_hook: str = Field(
        default="",
        description="Hook leveraging authority principle (権威)",
    )
    scarcity_hook: str = Field(
        default="",
        description="Hook leveraging scarcity principle (希少性)",
    )


class PlacementInstruction(BaseModel):
    """Content placement instruction for article sections.

    Specifies where to place emotional content (empathy, episode, hook)
    within the article structure.
    """

    content_type: Literal["empathy", "episode", "hook"] = Field(
        ...,
        description="Type of content to place",
    )
    target_section: str = Field(
        default="",
        description="Target section (H2 title or position like 'intro', 'conclusion')",
    )
    content: str = Field(
        default="",
        description="The actual content to place",
    )


class HumanTouchMetadata(BaseModel):
    """Metadata for human touch generation."""

    generated_at: datetime = Field(default_factory=datetime.now)
    model: str = ""
    input_files: list[str] = Field(default_factory=list)


class Step3_5Output(StepOutputBase):
    """Step 3.5 output schema.

    Extended for blog.System Ver8.3 integration with:
    - Phase-specific emotional mapping
    - Behavioral economics hooks
    - Content placement instructions
    """

    step: str = "step3_5"
    emotional_analysis: EmotionalAnalysis = Field(default_factory=EmotionalAnalysis)
    human_touch_patterns: list[HumanTouchPattern] = Field(default_factory=list)
    experience_episodes: list[ExperienceEpisode] = Field(default_factory=list)
    emotional_hooks: list[str] = Field(
        default_factory=list,
        description="Compelling emotional hooks for the content",
    )
    # blog.System Ver8.3 extensions
    phase_emotional_map: PhaseEmotionalMap = Field(
        default_factory=PhaseEmotionalMap,
        description="Three-phase emotional mapping (認知/検討/行動)",
    )
    behavioral_economics_hooks: BehavioralEconomicsHooks = Field(
        default_factory=BehavioralEconomicsHooks,
        description="Behavioral economics-based persuasion hooks",
    )
    placement_instructions: list[PlacementInstruction] = Field(
        default_factory=list,
        description="Content placement instructions for article sections",
    )
    raw_output: str = Field(default="", description="Raw LLM output for debugging")
    parsed_data: dict[str, Any] | None = Field(
        default=None,
        description="Parsed JSON data if available",
    )
    metadata: HumanTouchMetadata = Field(default_factory=HumanTouchMetadata)
    quality: dict[str, Any] = Field(
        default_factory=dict,
        description="Quality validation results",
    )
    token_usage: dict[str, int] = Field(
        default_factory=dict,
        description="Token usage (input/output tokens)",
    )
    output_path: str | None = Field(default=None, description="Storage上の出力パス")
    output_digest: str | None = Field(default=None, description="出力内容のSHA256ダイジェスト")
