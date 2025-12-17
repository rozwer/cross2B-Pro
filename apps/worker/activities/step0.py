"""Step 0: Keyword Selection Activity.

Analyzes input keyword to determine optimal targeting strategy.
Uses Gemini for analysis.

REVIEW-001: LLMInterface契約に準拠
- LLMCallMetadata 必須化
- token_usage 参照を統一

ヘルパー統合:
- OutputParser: LLM出力のJSONパース
- QualityRetryLoop: 品質検証付きリトライ
- ContentMetrics: テキストメトリクス計算
- RequiredElementsValidator: 必須要素チェック
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import LLMInterface, get_llm_client
from apps.api.llm.schemas import LLMResponse
from apps.api.llm.exceptions import (
    LLMAuthenticationError,
    LLMInvalidRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from apps.api.llm.schemas import LLMCallMetadata, LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.helpers import (
    ContentMetrics,
    OutputParser,
    QualityResult,
    QualityRetryLoop,
    RequiredElementsValidator,
)

from .base import ActivityError, BaseActivity


class Step0KeywordSelection(BaseActivity):
    """Activity for keyword selection and analysis.

    ヘルパー統合:
    - OutputParser: LLM出力のJSONパース（コードブロック対応）
    - QualityRetryLoop: 品質検証付きリトライ（max_retries=1）
    - ContentMetrics: テキストメトリクス計算
    - RequiredElementsValidator: 必須要素（検索意図、難易度、推奨）チェック
    """

    # 必須要素のパターン定義
    REQUIRED_ELEMENTS = {
        "search_intent": ["検索意図", "intent", "目的", "ユーザーの意図"],
        "difficulty": ["難易度", "difficulty", "競合度", "競争"],
        "recommendation": ["推奨", "recommend", "提案", "おすすめ"],
    }

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.parser = OutputParser()
        self.metrics = ContentMetrics()
        # 1つまで欠落を許容
        self.output_validator = RequiredElementsValidator(
            required_patterns=self.REQUIRED_ELEMENTS,
            max_missing=1,
        )

    @property
    def step_id(self) -> str:
        return "step0"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute keyword selection analysis.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with keyword analysis results
        """
        config = ctx.config
        pack_id = config.get("pack_id")

        if not pack_id:
            raise ActivityError(
                "pack_id is required",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Load prompt pack
        loader = PromptPackLoader()
        prompt_pack = loader.load(pack_id)

        # Get input keyword from config
        keyword = config.get("keyword")
        if not keyword or not keyword.strip():
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Get prompt for this step
        try:
            prompt_template = prompt_pack.get_prompt("step0")
            initial_prompt = prompt_template.render(keyword=keyword)
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Gemini for step0)
        llm_provider = config.get("llm_provider", "gemini")
        llm_model = config.get("llm_model")
        llm: LLMInterface = get_llm_client(llm_provider, model=llm_model)

        # REVIEW-001: LLMCallMetadata を必須で注入（トレーサビリティ確保）
        metadata = LLMCallMetadata(
            run_id=ctx.run_id,
            step_id=self.step_id,
            attempt=ctx.attempt,
            tenant_id=ctx.tenant_id,
        )

        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 2000),
            temperature=config.get("temperature", 0.7),
        )

        # LLM call function for retry loop
        async def llm_call(prompt: str) -> LLMResponse:
            try:
                return await llm.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You are a keyword analysis assistant.",
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

        # Quality-checked retry loop
        retry_loop = QualityRetryLoop(
            max_retries=1,
            accept_on_final=True,
        )

        loop_result = await retry_loop.execute(
            llm_call=llm_call,
            initial_prompt=initial_prompt,
            validator=self.output_validator,
            enhance_prompt=self._enhance_prompt,
            extract_content=lambda r: r.content,
        )

        if loop_result.result is None:
            raise ActivityError(
                "LLM generation failed: no result",
                category=ErrorCategory.RETRYABLE,
            )
        response: LLMResponse = loop_result.result
        content = response.content

        # Parse JSON output if present
        parse_result = self.parser.parse_json(content)

        if parse_result.success and isinstance(parse_result.data, dict):
            parsed_data = parse_result.data
        else:
            # JSON parse failed - store raw analysis
            parsed_data = {}

        # Calculate text metrics
        text_metrics = self.metrics.text_metrics(content, lang="ja")

        # Build structured output
        return {
            "step": self.step_id,
            "keyword": keyword,
            "analysis": content,
            "search_intent": parsed_data.get("search_intent", ""),
            "difficulty_score": parsed_data.get("difficulty_score", 5),
            "recommended_angles": parsed_data.get("recommended_angles", []),
            "target_audience": parsed_data.get("target_audience", ""),
            "content_type_suggestion": parsed_data.get("content_type_suggestion", ""),
            "model": response.model,
            "usage": {
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
            "metrics": {
                "char_count": text_metrics.char_count,
                "word_count": text_metrics.word_count,
            },
            "quality": {
                "issues": loop_result.quality.issues if loop_result.quality else [],
                "attempts": loop_result.attempts,
            },
            "parse_result": {
                "success": parse_result.success,
                "format_detected": parse_result.format_detected,
                "fixes_applied": parse_result.fixes_applied,
            },
        }

    def _enhance_prompt(self, prompt: str, issues: list[str]) -> str:
        """Enhance prompt based on quality issues.

        Args:
            prompt: Current prompt
            issues: List of detected quality issues

        Returns:
            Enhanced prompt with additional instructions
        """
        enhancements = []

        for issue in issues:
            if "search_intent" in issue:
                enhancements.append(
                    "必ず「検索意図」または「ユーザーの目的」を明記してください。"
                )
            elif "difficulty" in issue:
                enhancements.append(
                    "必ず「難易度」または「競合度」の評価を含めてください。"
                )
            elif "recommendation" in issue:
                enhancements.append(
                    "必ず「推奨」または「提案」のセクションを含めてください。"
                )

        if enhancements:
            enhancement_text = "\n\n【追加指示】\n" + "\n".join(enhancements)
            return prompt + enhancement_text

        return prompt


# Activity function for Temporal registration
@activity.defn(name="step0_keyword_selection")
async def step0_keyword_selection(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 0."""
    step = Step0KeywordSelection()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
