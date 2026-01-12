"""Step 3A: Query Analysis & Persona Activity.

Analyzes search query intent and builds user personas.
Runs in parallel with step3b and step3c.
Uses Gemini for analysis.

blog.System Ver8.3 対応:
- 核心的疑問（CoreQuestion）の抽出
- 行動経済学6原則のプロファイリング
- 3フェーズ心理マッピング
- 拡張ペルソナの生成
"""

import logging
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
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


class Step3AQueryAnalysis(BaseActivity):
    """Activity for query analysis and persona building.

    blog.System Ver8.3 対応:
    - 核心的疑問の抽出
    - 行動経済学6原則の分析
    - 3フェーズ心理マッピング
    """

    # Required elements for quality validation (既存 + 新規)
    REQUIRED_ELEMENTS = {
        # 既存要素
        "search_intent": ["検索意図", "search intent", "intent", "search_intent"],
        "persona": ["ペルソナ", "persona", "ユーザー像", "detailed_persona"],
        "pain_points": ["課題", "pain point", "悩み", "pain_points"],
        # 新規要素（blog.System Ver8.3）
        "core_question": [
            "核心的",
            "メインQuestion",
            "main_question",
            "core_question",
            "primary",
        ],
        "behavioral_economics": [
            "損失回避",
            "社会的証明",
            "loss_aversion",
            "social_proof",
            "behavioral_economics",
        ],
        "three_phase": [
            "Phase 1",
            "Phase 2",
            "phase1",
            "phase2",
            "three_phase",
            "フェーズ",
        ],
    }

    # V2モード時の追加必須パターン
    V2_REQUIRED_PATTERNS = {
        "authority": ["権威性", "authority", "専門家"],
        "scarcity": ["希少性", "scarcity", "緊急性"],
        "cvr_targets": ["CVR", "cvr", "コンバージョン"],
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.parser = OutputParser()
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()
        self.input_validator = InputValidator()
        # デフォルトはV1互換（max_missing=1で既存要素のみ必須）
        self.quality_validator = RequiredElementsValidator(
            required_patterns=self.REQUIRED_ELEMENTS,
            max_missing=3,  # 新規要素は欠落許容
        )

    @property
    def step_id(self) -> str:
        return "step3a"

    def _is_v2_mode(self, pack_id: str) -> bool:
        """V2モード（blog.System対応）かどうかを判定."""
        return pack_id.startswith("v2_") or "blog_system" in pack_id.lower()

    def _create_v2_validator(self) -> RequiredElementsValidator:
        """V2モード用のより厳格なバリデータを作成."""
        all_patterns = {**self.REQUIRED_ELEMENTS, **self.V2_REQUIRED_PATTERNS}
        return RequiredElementsValidator(
            required_patterns=all_patterns,
            max_missing=1,  # V2では1つまでしか欠落を許容しない
        )

    def _extract_v2_fields(self, parsed_data: dict[str, Any]) -> dict[str, Any]:
        """パース済みデータからV2フィールドを抽出."""
        v2_fields: dict[str, Any] = {}

        # core_question の抽出
        if "core_question" in parsed_data:
            v2_fields["core_question"] = parsed_data["core_question"]
        elif "primary" in parsed_data and isinstance(parsed_data.get("primary"), str):
            # フラット構造の場合
            v2_fields["core_question"] = {
                "primary": parsed_data.get("primary", ""),
                "underlying_concern": parsed_data.get("underlying_concern", ""),
                "time_sensitivity": parsed_data.get("time_sensitivity", "medium"),
                "sub_questions": parsed_data.get("sub_questions", []),
            }

        # question_hierarchy の抽出
        if "question_hierarchy" in parsed_data:
            v2_fields["question_hierarchy"] = parsed_data["question_hierarchy"]
        elif "level_1_primary" in parsed_data:
            v2_fields["question_hierarchy"] = {
                "level_1_primary": parsed_data.get("level_1_primary", []),
                "level_2_secondary": parsed_data.get("level_2_secondary", {}),
            }

        # behavioral_economics_profile の抽出
        if "behavioral_economics_profile" in parsed_data:
            v2_fields["behavioral_economics_profile"] = parsed_data["behavioral_economics_profile"]
        elif "persona_deep_dive" in parsed_data:
            # blog.System形式からの抽出
            persona_data = parsed_data["persona_deep_dive"]
            if "behavioral_economics_profile" in persona_data:
                v2_fields["behavioral_economics_profile"] = persona_data["behavioral_economics_profile"]

        # three_phase_mapping の抽出
        if "three_phase_mapping" in parsed_data:
            v2_fields["three_phase_mapping"] = parsed_data["three_phase_mapping"]
        elif "three_phase_psychological_mapping" in parsed_data:
            # blog.System形式
            v2_fields["three_phase_mapping"] = parsed_data["three_phase_psychological_mapping"]

        # detailed_persona の抽出
        if "detailed_persona" in parsed_data:
            v2_fields["detailed_persona"] = parsed_data["detailed_persona"]
        elif "persona_deep_dive" in parsed_data:
            persona_data = parsed_data["persona_deep_dive"]
            v2_fields["detailed_persona"] = {
                "name": persona_data.get("detailed_profile", {}).get("name", ""),
                "age": persona_data.get("detailed_profile", {}).get("age", 35),
                "job_title": persona_data.get("detailed_profile", {}).get("job_title", ""),
                "company_size": persona_data.get("detailed_profile", {}).get("company_size", ""),
                "pain_points": persona_data.get("detailed_profile", {}).get("pain_points", []),
                "goals": persona_data.get("detailed_profile", {}).get("goals", []),
                "search_scenario": persona_data.get("search_scenario", {}),
                "emotional_state": persona_data.get("emotional_state", {}),
            }

        return v2_fields

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute query analysis.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with query analysis and personas
        """
        config = ctx.config
        pack_id = config.get("pack_id")

        if not pack_id:
            raise ActivityError(
                "pack_id is required",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # V2モード判定
        is_v2 = self._is_v2_mode(pack_id)
        if is_v2:
            self.quality_validator = self._create_v2_validator()
            logger.info("Step3A running in V2 mode (blog.System)")

        # Load prompt pack
        loader = PromptPackLoader()
        prompt_pack = loader.load(pack_id)

        # Get inputs
        keyword = config.get("keyword")

        # Load step data from storage (not from config to avoid gRPC size limits)
        step0_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step0") or {}
        step1_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step1") or {}
        step2_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step2") or {}

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Input validation
        required_fields = ["step0.analysis"]
        recommended_fields = ["step1.competitors"]
        if is_v2:
            recommended_fields.append("step2.validated_data")

        validation = self.input_validator.validate(
            data={"step0": step0_data, "step1": step1_data, "step2": step2_data},
            required=required_fields,
            recommended=recommended_fields,
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
                    "step0_data": step0_data,
                    "step1_data": step1_data,
                    "step2_data": step2_data,
                },
            )

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step3a")
            # V2モードでは追加の変数を渡す
            render_vars = {
                "keyword": keyword,
                "keyword_analysis": step0_data.get("analysis", ""),
                "competitor_count": len(step1_data.get("competitors", [])),
            }
            if is_v2:
                # step2のvalidated_dataを追加
                render_vars["competitor_data"] = step2_data.get("validated_data", [])
                render_vars["four_pillars_evaluation"] = step0_data.get("four_pillars_evaluation", {})
            initial_prompt = prompt_template.render(**render_vars)
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Gemini for step3a)
        llm_provider = config.get("llm_provider", "gemini")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # LLM config (V2モードでは出力が長くなるため、max_tokensを増加)
        default_max_tokens = 6000 if is_v2 else 3000
        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", default_max_tokens),
            temperature=config.get("temperature", 0.7),
        )
        metadata = LLMCallMetadata(
            run_id=ctx.run_id,
            step_id=self.step_id,
            attempt=ctx.attempt,
            tenant_id=ctx.tenant_id,
        )

        # Define LLM call function for retry loop
        async def llm_call(prompt: str) -> Any:
            system_prompt = (
                "You are an expert in search query analysis, behavioral economics, "
                "and user psychology. Analyze the search query and build detailed "
                "user personas with psychological profiles."
                if is_v2
                else "You are a search query analysis expert."
            )
            try:
                return await llm.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt=system_prompt,
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

        # Define prompt enhancement function
        def enhance_prompt(prompt: str, issues: list[str]) -> str:
            enhancement = "\n\n【追加指示】以下の要素を必ず含めてください：\n"
            for issue in issues:
                if issue == "missing_search_intent":
                    enhancement += "- 検索意図（informational/navigational/transactional/commercialのいずれか）\n"
                elif issue == "missing_persona":
                    enhancement += "- ユーザーペルソナ（具体的な人物像）\n"
                elif issue == "missing_pain_points":
                    enhancement += "- ユーザーの課題・悩み\n"
                elif issue == "missing_core_question":
                    enhancement += "- 核心的な疑問（メインQuestion、50字以内）\n"
                elif issue == "missing_behavioral_economics":
                    enhancement += "- 行動経済学6原則（損失回避、社会的証明、権威性、一貫性、好意、希少性）の分析\n"
                elif issue == "missing_three_phase":
                    enhancement += "- 3フェーズ心理マッピング（Phase 1: 不安・課題認識、Phase 2: 理解・納得、Phase 3: 行動決定）\n"
                elif issue == "missing_authority":
                    enhancement += "- 権威性の分析（信頼する専門家・機関）\n"
                elif issue == "missing_scarcity":
                    enhancement += "- 希少性の分析（緊急性を感じる要素）\n"
                elif issue == "missing_cvr_targets":
                    enhancement += "- CVR目標（Early CTA: 3%, Mid CTA: 4%, Final CTA: 5%）\n"
            return prompt + enhancement

        # Quality retry loop
        retry_loop = QualityRetryLoop(max_retries=2 if is_v2 else 1, accept_on_final=True)

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

        # Calculate content metrics
        text_metrics = self.metrics.text_metrics(content)

        # Build result
        result: dict[str, Any] = {
            "step": self.step_id,
            "keyword": keyword,
            "query_analysis": content,
            "parsed_data": parse_result.data if parse_result.success else None,
            "format_detected": parse_result.format_detected,
            "model": response.model,
            "token_usage": {
                "input": response.token_usage.input,
                "output": response.token_usage.output,
            },
            "metrics": {
                "char_count": text_metrics.char_count,
                "word_count": text_metrics.word_count,
            },
            "quality": {
                "attempts": loop_result.attempts,
                "issues": loop_result.quality.issues if loop_result.quality else [],
            },
            "is_v2": is_v2,
        }

        # V2モードの場合、追加フィールドを抽出
        if is_v2 and parse_result.success and isinstance(parse_result.data, dict):
            v2_fields = self._extract_v2_fields(parse_result.data)
            result["v2_fields"] = v2_fields
            logger.info(f"Extracted V2 fields: {list(v2_fields.keys())}")

        return result


@activity.defn(name="step3a_query_analysis")
async def step3a_query_analysis(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 3A."""
    step = Step3AQueryAnalysis()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
