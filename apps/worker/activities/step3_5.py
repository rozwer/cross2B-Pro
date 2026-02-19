"""Step 3.5: Human Touch Generation Activity.

Generates emotional analysis, human-like expressions, and experience episodes
based on previous step outputs. Runs after approval as the first post-approval step.
Uses Gemini for natural, creative expression generation.
"""

import hashlib
import json
import logging
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.worker.helpers.model_config import get_step_llm_client, get_step_model_config
from apps.api.llm.exceptions import (
    LLMAuthenticationError,
    LLMInvalidRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from apps.api.llm.schemas import LLMCallMetadata, LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.helpers import (
    CheckpointManager,
    ContentMetrics,
    InputValidator,
    OutputParser,
    QualityRetryLoop,
    RequiredElementsValidator,
)

from .base import ActivityError, BaseActivity, load_step_data

logger = logging.getLogger(__name__)


class Step3_5HumanTouchGeneration(BaseActivity):
    """Activity for generating human touch elements.

    Takes outputs from step0, step1, step1_5 (optional), step3a, step3b, step3c
    and generates emotional analysis, human-touch patterns, and experience episodes.
    """

    REQUIRED_ELEMENTS = {
        "emotional_analysis": ["感情", "emotion", "心情"],
        "human_touch": ["人間味", "human", "体験"],
        "experience": ["エピソード", "episode", "体験談"],
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.parser = OutputParser()
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()
        self.input_validator = InputValidator()
        self.quality_validator = RequiredElementsValidator(
            required_patterns=self.REQUIRED_ELEMENTS,
            max_missing=1,
        )

    @property
    def step_id(self) -> str:
        return "step3_5"

    def _extract_phase_emotional_data(self, phase_data: dict[str, Any] | None) -> dict[str, Any]:
        """Extract phase emotional data from parsed output.

        Args:
            phase_data: Raw phase data from LLM output

        Returns:
            Structured PhaseEmotionalData dict
        """
        if not isinstance(phase_data, dict):
            return {
                "dominant_emotion": "",
                "empathy_statements": [],
                "experience_episodes": [],
            }

        # Extract experience episodes for this phase
        episodes = []
        raw_episodes = phase_data.get("experience_episodes", phase_data.get("episodes", []))
        for ep in raw_episodes if isinstance(raw_episodes, list) else []:
            if isinstance(ep, dict):
                episodes.append(
                    {
                        "scenario": ep.get("scenario", ""),
                        "narrative": ep.get("narrative", ""),
                        "lesson": ep.get("lesson", ""),
                    }
                )

        return {
            "dominant_emotion": phase_data.get("dominant_emotion", ""),
            "empathy_statements": phase_data.get("empathy_statements", [])
            if isinstance(phase_data.get("empathy_statements"), list)
            else [],
            "experience_episodes": episodes,
        }

    def _extract_phase_emotional_map(self, parsed_data: dict[str, Any]) -> dict[str, Any]:
        """Extract three-phase emotional map from parsed output.

        Args:
            parsed_data: Full parsed LLM output

        Returns:
            Structured PhaseEmotionalMap dict
        """
        raw_map = parsed_data.get("phase_emotional_map", {})
        if not isinstance(raw_map, dict):
            raw_map = {}

        return {
            "phase1": self._extract_phase_emotional_data(raw_map.get("phase1")),
            "phase2": self._extract_phase_emotional_data(raw_map.get("phase2")),
            "phase3": self._extract_phase_emotional_data(raw_map.get("phase3")),
        }

    def _extract_behavioral_economics_hooks(self, parsed_data: dict[str, Any]) -> dict[str, Any]:
        """Extract behavioral economics hooks from parsed output.

        Args:
            parsed_data: Full parsed LLM output

        Returns:
            Structured BehavioralEconomicsHooks dict
        """
        raw_hooks = parsed_data.get("behavioral_economics_hooks", {})
        if not isinstance(raw_hooks, dict):
            raw_hooks = {}

        return {
            "loss_aversion_hook": raw_hooks.get("loss_aversion", raw_hooks.get("loss_aversion_hook", "")),
            "social_proof_hook": raw_hooks.get("social_proof", raw_hooks.get("social_proof_hook", "")),
            "authority_hook": raw_hooks.get("authority", raw_hooks.get("authority_hook", "")),
            "scarcity_hook": raw_hooks.get("scarcity", raw_hooks.get("scarcity_hook", "")),
            "consistency_hook": raw_hooks.get("consistency", raw_hooks.get("consistency_hook", "")),
            "liking_hook": raw_hooks.get("liking", raw_hooks.get("liking_hook", "")),
        }

    def _extract_placement_instructions(self, parsed_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract placement instructions from parsed output.

        Args:
            parsed_data: Full parsed LLM output

        Returns:
            List of PlacementInstruction dicts
        """
        raw_instructions = parsed_data.get("placement_instructions", [])
        if not isinstance(raw_instructions, list):
            return []

        instructions = []
        valid_types = {"empathy", "episode", "hook"}

        for inst in raw_instructions:
            if isinstance(inst, dict):
                content_type = inst.get("content_type", "")
                # Validate content_type
                if content_type not in valid_types:
                    logger.warning(f"Invalid placement content_type: {content_type}, skipping")
                    continue

                instructions.append(
                    {
                        "content_type": content_type,
                        "target_section": inst.get("target_section", ""),
                        "content": inst.get("content", ""),
                    }
                )

        return instructions

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute human touch generation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with human touch elements
        """
        config = ctx.config
        pack_id = config.get("pack_id")

        if not pack_id:
            raise ActivityError(
                "pack_id is required",
                category=ErrorCategory.NON_RETRYABLE,
            )

        loader = PromptPackLoader()
        prompt_pack = loader.load(pack_id)

        keyword = config.get("keyword")
        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Load previous step outputs from storage
        step0_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step0") or {}
        step1_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step1") or {}
        step1_5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step1_5")  # Optional, may be None
        step3a_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3a") or {}
        step3b_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3b") or {}
        step3c_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3c") or {}

        # Track which input files were available
        input_files = ["step0", "step1", "step3a", "step3b", "step3c"]
        if step1_5_data:
            input_files.append("step1_5")

        # Input validation - require step0, step1, step3a/3b/3c; step1_5 is optional
        validation = self.input_validator.validate(
            data={
                "step0": step0_data,
                "step1": step1_data,
                "step3a": step3a_data,
                "step3b": step3b_data,
                "step3c": step3c_data,
            },
            required=["step0", "step1", "step3a", "step3b", "step3c"],
            recommended=[],
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if validation.missing_recommended:
            logger.warning(f"Missing recommended fields: {validation.missing_recommended}")

        # Checkpoint: input data loaded
        input_checkpoint = await self.checkpoint.load(ctx.tenant_id, ctx.run_id, self.step_id, "inputs_loaded")

        if not input_checkpoint:
            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "inputs_loaded",
                {
                    "input_files": input_files,
                    "step0_keys": list(step0_data.keys()),
                    "step3a_keys": list(step3a_data.keys()),
                },
            )

        # Extract relevant data for prompt
        persona_info = step3a_data.get("query_analysis", "")
        if isinstance(persona_info, dict):
            persona_info = json.dumps(persona_info, ensure_ascii=False, indent=2)

        cooccurrence_keywords = step3b_data.get("cooccurrence_analysis", "")
        if isinstance(cooccurrence_keywords, dict):
            cooccurrence_keywords = json.dumps(cooccurrence_keywords, ensure_ascii=False, indent=2)

        competitor_insights = step3c_data.get("competitor_analysis", "")
        if isinstance(competitor_insights, dict):
            competitor_insights = json.dumps(competitor_insights, ensure_ascii=False, indent=2)

        # Extract three_phase_mapping from step3a (blog.System Ver8.3)
        three_phase_mapping = step3a_data.get("three_phase_mapping", "")
        if isinstance(three_phase_mapping, dict):
            three_phase_mapping = json.dumps(three_phase_mapping, ensure_ascii=False, indent=2)

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step3_5")
            initial_prompt = prompt_template.render(
                keyword=keyword,
                persona=persona_info,
                competitor_insights=competitor_insights,
                cooccurrence_keywords=cooccurrence_keywords,
                three_phase_mapping=three_phase_mapping,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client - uses 3-tier priority: UI per-step > step defaults > global config
        llm_provider, llm_model = get_step_model_config(self.step_id, config)
        llm = await get_step_llm_client(self.step_id, config, tenant_id=ctx.tenant_id)

        # LLM config - slightly higher temperature for creativity
        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 4000),
            temperature=config.get("temperature", 0.7),
        )
        metadata = LLMCallMetadata(
            run_id=ctx.run_id,
            step_id=self.step_id,
            attempt=ctx.attempt,
            tenant_id=ctx.tenant_id,
        )

        async def llm_call(prompt: str) -> Any:
            try:
                return await llm.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You are an expert at creating emotionally resonant, human-centered content.",
                    config=llm_config,
                    metadata=metadata,
                )
            except (LLMRateLimitError, LLMTimeoutError) as e:
                raise ActivityError(
                    f"LLM temporary failure: {e}",
                    category=ErrorCategory.RETRYABLE,
                    details={"llm_error": str(e)},
                ) from e
            except (LLMAuthenticationError, LLMInvalidRequestError) as e:
                raise ActivityError(
                    f"LLM permanent failure: {e}",
                    category=ErrorCategory.NON_RETRYABLE,
                    details={"llm_error": str(e)},
                ) from e
            except Exception as e:
                raise ActivityError(
                    f"LLM call failed: {e}",
                    category=ErrorCategory.RETRYABLE,
                ) from e

        def enhance_prompt(prompt: str, issues: list[str]) -> str:
            enhancement = "\n\n【追加指示】以下の要素を必ず含めてください：\n"
            for issue in issues:
                if issue == "missing_emotional_analysis":
                    enhancement += "- 感情分析（読者の心情・感情の傾向）\n"
                elif issue == "missing_human_touch":
                    enhancement += "- 人間味のある表現パターン（体験談、感情表現、共感フレーズ）\n"
                elif issue == "missing_experience":
                    enhancement += "- 具体的な体験エピソード（シナリオ、ナラティブ、教訓）\n"
            return prompt + enhancement

        # Quality retry loop
        retry_loop = QualityRetryLoop(max_retries=1, accept_on_final=True)

        loop_result = await retry_loop.execute(
            llm_call=llm_call,
            initial_prompt=initial_prompt,
            validator=self.quality_validator,
            enhance_prompt=enhance_prompt,
            extract_content=lambda r: r.content,
        )

        if not loop_result.success or loop_result.result is None:
            quality_issues = loop_result.quality.issues if loop_result.quality else "unknown"
            raise ActivityError(
                f"Quality validation failed after retries: {quality_issues}",
                category=ErrorCategory.RETRYABLE,
            )

        response = loop_result.result
        content: str = response.content

        # Parse output (attempt JSON extraction)
        parse_result = self.parser.parse_json(content)

        if parse_result.success and isinstance(parse_result.data, dict):
            logger.info(f"Parsed JSON output: {list(parse_result.data.keys())}")

        # Calculate content metrics (for potential future use)
        _ = self.metrics.text_metrics(content)

        # Build structured output conforming to Step3_5Output schema
        parsed_data = parse_result.data if parse_result.success and isinstance(parse_result.data, dict) else {}

        # Extract emotional_analysis with robust parsing
        # Initialize with default values
        emotional_analysis = {
            "primary_emotion": "",
            "secondary_emotions": [],
            "pain_points": [],
            "desires": [],
        }

        # Try nested structure first, then flat structure as fallback
        raw_emotional = parsed_data.get("emotional_analysis")
        if isinstance(raw_emotional, dict):
            emotional_analysis.update(
                {
                    "primary_emotion": raw_emotional.get("primary_emotion", ""),
                    "secondary_emotions": raw_emotional.get("secondary_emotions", []),
                    "pain_points": raw_emotional.get("pain_points", []),
                    "desires": raw_emotional.get("desires", []),
                }
            )
        else:
            # Fallback to flat structure
            if raw_emotional is not None:
                logger.warning(f"emotional_analysis is not a dict: {type(raw_emotional)}, using flat structure")
            emotional_analysis.update(
                {
                    "primary_emotion": parsed_data.get("primary_emotion", ""),
                    "secondary_emotions": parsed_data.get("secondary_emotions", []),
                    "pain_points": parsed_data.get("pain_points", []),
                    "desires": parsed_data.get("desires", []),
                }
            )

        # Validate array fields (ensure they are lists)
        for field in ["secondary_emotions", "pain_points", "desires"]:
            if not isinstance(emotional_analysis[field], list):
                logger.warning(f"emotional_analysis.{field} is not a list: {type(emotional_analysis[field])}")
                emotional_analysis[field] = []

        # Extract human touch patterns
        human_touch_patterns = []
        raw_patterns = parsed_data.get("human_touch_patterns", parsed_data.get("patterns", []))
        for p in raw_patterns if isinstance(raw_patterns, list) else []:
            if isinstance(p, dict):
                human_touch_patterns.append(
                    {
                        "type": p.get("type", "experience"),
                        "content": p.get("content", ""),
                        "placement_suggestion": p.get("placement_suggestion", p.get("placement", "")),
                    }
                )

        # Extract experience episodes
        experience_episodes = []
        raw_episodes = parsed_data.get("experience_episodes", parsed_data.get("episodes", []))
        for ep in raw_episodes if isinstance(raw_episodes, list) else []:
            if isinstance(ep, dict):
                experience_episodes.append(
                    {
                        "scenario": ep.get("scenario", ""),
                        "narrative": ep.get("narrative", ""),
                        "lesson": ep.get("lesson", ""),
                    }
                )

        # Extract emotional hooks
        emotional_hooks = parsed_data.get("emotional_hooks", parsed_data.get("hooks", []))
        if not isinstance(emotional_hooks, list):
            emotional_hooks = []

        # ============================================================
        # blog.System Ver8.3 Extensions
        # ============================================================

        # Extract phase_emotional_map (3フェーズ別感情マップ)
        phase_emotional_map = self._extract_phase_emotional_map(parsed_data)

        # Extract behavioral_economics_hooks (行動経済学フック)
        behavioral_economics_hooks = self._extract_behavioral_economics_hooks(parsed_data)

        # Extract placement_instructions (配置指示)
        placement_instructions = self._extract_placement_instructions(parsed_data)

        output_data = {
            "step": self.step_id,
            "keyword": keyword,
            # Structured fields conforming to Step3_5Output schema
            "emotional_analysis": emotional_analysis,
            "human_touch_patterns": human_touch_patterns,
            "experience_episodes": experience_episodes,
            "emotional_hooks": emotional_hooks,
            # blog.System Ver8.3 extensions
            "phase_emotional_map": phase_emotional_map,
            "behavioral_economics_hooks": behavioral_economics_hooks,
            "placement_instructions": placement_instructions,
            # Raw output for debugging and fallback
            "raw_output": content,
            "parsed_data": parsed_data if parsed_data else None,
            # Metadata
            "metadata": {
                "generated_at": ctx.started_at.isoformat(),
                "model": response.model,
                "model_config": {
                    "platform": llm_provider,
                    "model": llm_model,
                },
                "input_files": input_files,
            },
            "quality": {
                "attempts": loop_result.attempts,
                "issues": loop_result.quality.issues if loop_result.quality else [],
            },
            # Token usage
            "token_usage": {
                "input": response.token_usage.input,
                "output": response.token_usage.output,
            },
        }
        output_data["output_path"] = self.store.build_path(ctx.tenant_id, ctx.run_id, self.step_id)
        output_data["output_digest"] = hashlib.sha256(json.dumps(output_data, ensure_ascii=False, indent=2).encode("utf-8")).hexdigest()[
            :16
        ]
        return output_data


@activity.defn(name="step3_5_human_touch_generation")
async def step3_5_human_touch_generation(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 3.5."""
    step = Step3_5HumanTouchGeneration()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
