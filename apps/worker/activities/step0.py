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

blog.System Ver8.3 対応:
- 4本柱評価（神経科学/行動経済学/LLMO/KGI）
- 記事戦略（6タイプ）
- 文字数設定/CTA設計の引き継ぎ
- FourPillarsValidator/ArticleStrategyValidator の統合
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import LLMInterface
from apps.worker.helpers.model_config import get_step_llm_client, get_step_model_config
from apps.api.llm.exceptions import (
    LLMAuthenticationError,
    LLMInvalidRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from apps.api.llm.schemas import LLMCallMetadata, LLMRequestConfig, LLMResponse
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.activities.schemas.step0 import (
    ArticleStrategy,
    CTASpecification,
    FourPillarsEvaluation,
    Step0Input,
    WordCountConfig,
)
from apps.worker.helpers import (
    CTA_POSITION_EARLY,
    CTA_POSITION_FINAL_OFFSET,
    CTA_POSITION_MID,
    ArticleStrategyValidator,
    ContentMetrics,
    FourPillarsValidator,
    OutputParser,
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

    blog.System Ver8.3 対応:
    - FourPillarsValidator: 4本柱評価の検証
    - ArticleStrategyValidator: 記事戦略の検証
    - Step0Input: 拡張入力スキーマ
    - Step0Output: 拡張出力スキーマ
    """

    # 必須要素のパターン定義
    REQUIRED_ELEMENTS = {
        "search_intent": ["検索意図", "intent", "目的", "ユーザーの意図"],
        "difficulty": ["難易度", "difficulty", "競合度", "競争"],
        "recommendation": ["推奨", "recommend", "提案", "おすすめ"],
    }

    # blog.System Ver8.3: 4本柱・記事タイプの必須要素
    REQUIRED_ELEMENTS_V2 = {
        "four_pillars": ["4本柱", "神経科学", "行動経済学", "LLMO", "KGI", "four_pillars"],
        "article_type": [
            "記事タイプ",
            "article_type",
            "comprehensive_guide",
            "deep_dive",
            "case_study",
            "comparison",
            "news_analysis",
            "how_to",
        ],
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
        # blog.System Ver8.3: 追加バリデータ
        self.four_pillars_validator = FourPillarsValidator()
        self.article_strategy_validator = ArticleStrategyValidator()

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

        # Load prompt pack with unified knowledge
        loader = PromptPackLoader()
        prompt_pack = loader.get_pack_with_knowledge(pack_id)

        # Get input keyword from config
        keyword = config.get("keyword")
        if not keyword or not keyword.strip():
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # blog.System Ver8.3: 拡張入力の取得
        step0_input = self._build_step0_input(config, keyword)

        # Get prompt for this step
        try:
            prompt_template = prompt_pack.get_prompt("step0")
            # blog.System Ver8.3: 新変数を含むレンダリング
            render_vars = self._build_render_variables(step0_input)
            initial_prompt = prompt_template.render(**render_vars)
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client - uses 3-tier priority: UI per-step > step defaults > global config
        llm_provider, llm_model = get_step_model_config(self.step_id, config)
        llm: LLMInterface = await get_step_llm_client(self.step_id, config, tenant_id=ctx.tenant_id)

        # REVIEW-001: LLMCallMetadata を必須で注入（トレーサビリティ確保）
        metadata = LLMCallMetadata(
            run_id=ctx.run_id,
            step_id=self.step_id,
            attempt=ctx.attempt,
            tenant_id=ctx.tenant_id,
        )

        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 6000),
            temperature=config.get("temperature", 0.7),
        )

        # LLM call function for retry loop
        async def llm_call(prompt: str) -> LLMResponse:
            try:
                return await llm.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt=(
                        "あなたはSEO記事生成パイプラインの工程0を担当するキーワード分析・CTA設計の専門家です。"
                        "神経科学（3フェーズ: 扁桃体→前頭前野→線条体）、行動経済学（6原則）、"
                        "LLMO（AI検索最適化）、KGI（CVR目標）の4本柱フレームワークに基づき、"
                        "キーワードを多角的に分析し、記事全体の戦略を設計してください。"
                        "出力は必ず指定されたJSON形式で返してください。"
                    ),
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

        # blog.System Ver8.3: 拡張フィールドの抽出
        four_pillars_data = self._extract_four_pillars(parsed_data)
        article_strategy_data = self._extract_article_strategy(parsed_data)

        # blog.System Ver8.3: 入力からの引き継ぎ（word_count_config, cta_specification）
        word_count_config_data = step0_input.word_count_config.model_dump() if step0_input.word_count_config else None
        cta_specification_data = step0_input.cta_specification.model_dump() if step0_input.cta_specification else None

        # CTA: LLM出力の cta_design があれば CTA仕様に反映（config未設定時のフォールバック）
        cta_specification_data = self._merge_cta_from_llm(parsed_data, cta_specification_data)

        # フィールド名の互換性: suggested_topics → recommended_angles
        recommended_angles = parsed_data.get("recommended_angles", [])
        if not recommended_angles:
            recommended_angles = parsed_data.get("suggested_topics", [])

        # フィールド名の互換性: difficulty → difficulty_score (1-10)
        difficulty_score = parsed_data.get("difficulty_score", None)
        if difficulty_score is None:
            difficulty_raw = parsed_data.get("difficulty", "medium")
            difficulty_map = {"low": 3, "medium": 5, "high": 8}
            difficulty_score = difficulty_map.get(difficulty_raw, 5) if isinstance(difficulty_raw, str) else 5

        # Build structured output
        return {
            "step": self.step_id,
            "keyword": keyword,
            "analysis": content,
            # 既存フィールド（後方互換性）
            "search_intent": parsed_data.get("search_intent", ""),
            "difficulty_score": difficulty_score,
            "recommended_angles": recommended_angles,
            "target_audience": parsed_data.get("target_audience", parsed_data.get("target_persona", "")),
            "content_type_suggestion": parsed_data.get("content_type_suggestion", ""),
            # blog.System Ver8.3: 拡張フィールド
            "four_pillars_evaluation": four_pillars_data,
            "article_strategy": article_strategy_data,
            "word_count_config": word_count_config_data,
            "cta_specification": cta_specification_data,
            "search_volume": step0_input.search_volume,
            "competition": step0_input.competition,
            # モデル・使用量・メトリクス
            "model": response.model,
            "model_config": {
                "platform": llm_provider,
                "model": llm_model,
            },
            "token_usage": {
                "input": response.token_usage.input,
                "output": response.token_usage.output,
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
                enhancements.append("必ず「検索意図」または「ユーザーの目的」を明記してください。")
            elif "difficulty" in issue:
                enhancements.append("必ず「難易度」または「競合度」の評価を含めてください。")
            elif "recommendation" in issue:
                enhancements.append("必ず「推奨」または「提案」のセクションを含めてください。")

        if enhancements:
            enhancement_text = "\n\n【追加指示】\n" + "\n".join(enhancements)
            return prompt + enhancement_text

        return prompt

    # =========================================================================
    # blog.System Ver8.3: ヘルパーメソッド
    # =========================================================================

    def _build_step0_input(self, config: dict[str, Any], keyword: str) -> Step0Input:
        """Build Step0Input from config with blog.System Ver8.3 extensions.

        Args:
            config: Workflow configuration
            keyword: Main keyword

        Returns:
            Step0Input with all fields populated
        """
        # 事業コンテキスト
        business_context_data = config.get("business_context", {})

        # 文字数設定
        word_count_config_data = config.get("word_count_config", {})
        word_count_config = WordCountConfig(**word_count_config_data) if word_count_config_data else None

        # CTA設定
        cta_specification_data = config.get("cta_specification", {})
        if not cta_specification_data:
            # Fallback: extract from UI hearing input format (config.input.data.cta)
            cta_specification_data = self._extract_cta_from_hearing_input(config)
        cta_specification = CTASpecification(**cta_specification_data) if cta_specification_data else None

        return Step0Input(
            keyword=keyword,
            pack_id=config.get("pack_id", "default"),
            business_context=business_context_data,
            search_volume=config.get("search_volume"),
            competition=config.get("competition"),
            related_keywords=config.get("related_keywords", []),
            strategy=config.get("strategy", "standard"),
            cluster_topics=config.get("cluster_topics", []),
            word_count_config=word_count_config or WordCountConfig(),
            cta_specification=cta_specification or CTASpecification(),
        )

    @staticmethod
    def _extract_cta_from_hearing_input(config: dict[str, Any]) -> dict[str, Any]:
        """Extract CTA specification from UI hearing input format.

        The UI sends CTA data as config.input.data.cta with structure:
        { type: "single"|"staged", single: {url, text}, staged: {early, mid, final} }

        This maps it to CTASpecification format:
        { design_type: "staged", placements: { early: {url, text}, mid: {url, text}, final: {url, text} } }
        """
        input_data = config.get("input", {})
        hearing_data = input_data.get("data", {})
        cta_input = hearing_data.get("cta", {})
        if not cta_input:
            return {}

        cta_type = cta_input.get("type", "single")

        if cta_type == "single":
            single = cta_input.get("single", {})
            url = single.get("url", "")
            text = single.get("text", "")
            if not url:
                return {}
            # Apply same URL/text to all 3 placements
            return {
                "design_type": "staged",
                "placements": {
                    "early": {"position": CTA_POSITION_EARLY, "url": url, "text": text},
                    "mid": {"position": CTA_POSITION_MID, "url": url, "text": text},
                    "final": {"position": f"target_word_count - {CTA_POSITION_FINAL_OFFSET}", "url": url, "text": text},
                },
            }
        elif cta_type == "staged":
            staged = cta_input.get("staged", {})
            placements = {}
            positions = {"early": CTA_POSITION_EARLY, "mid": CTA_POSITION_MID, "final": f"target_word_count - {CTA_POSITION_FINAL_OFFSET}"}
            for phase in ("early", "mid", "final"):
                item = staged.get(phase, {})
                placements[phase] = {
                    "position": positions[phase],
                    "url": item.get("url", ""),
                    "text": item.get("text", ""),
                }
            return {"design_type": "staged", "placements": placements}

        return {}

    def _build_render_variables(self, step0_input: Step0Input) -> dict[str, Any]:
        """Build variables for prompt rendering.

        Args:
            step0_input: Step0Input instance

        Returns:
            dict of variables for prompt template rendering
        """
        bc = step0_input.business_context
        wc = step0_input.word_count_config
        cta = step0_input.cta_specification

        return {
            "keyword": step0_input.keyword,
            # 事業コンテキスト
            "business_description": bc.business_description if bc else "",
            "conversion_goal": bc.conversion_goal if bc else "",
            "target_persona": bc.target_persona if bc else "",
            "company_strengths": bc.company_strengths if bc else "",
            # キーワード情報
            "search_volume": step0_input.search_volume or "",
            "competition": step0_input.competition or "",
            "related_keywords": ", ".join(step0_input.related_keywords) if step0_input.related_keywords else "",
            # 記事戦略
            "strategy": step0_input.strategy,
            "cluster_topics": ", ".join(step0_input.cluster_topics) if step0_input.cluster_topics else "",
            # 文字数設定
            "word_count_mode": wc.mode if wc else "ai_balanced",
            "manual_word_count": wc.manual_word_count if wc else "",
            # CTA設定
            "cta_design_type": cta.design_type if cta else "staged",
            "cta_url": cta.placements.get("final", {}).url if cta and cta.placements else "",
            "cta_text": cta.placements.get("final", {}).text if cta and cta.placements else "",
        }

    def _extract_four_pillars(self, parsed_data: dict[str, Any]) -> dict[str, Any] | None:
        """Extract and validate 4-pillar evaluation from parsed data.

        Args:
            parsed_data: Parsed JSON data from LLM output

        Returns:
            dict with 4-pillar evaluation or None if not present
        """
        four_pillars_raw = parsed_data.get("four_pillars_evaluation")
        if not four_pillars_raw:
            return None

        # バリデーション（警告のみ、失敗しても続行）
        validation_result = self.four_pillars_validator.validate_dict(four_pillars_raw)
        if not validation_result.is_valid:
            # 警告をログに記録（activity.logger を使用）
            activity.logger.warning(f"Four pillars validation warnings: {validation_result.issues}")

        # Pydanticモデルで構造化（デフォルト値で補完）
        try:
            four_pillars = FourPillarsEvaluation(**four_pillars_raw)
            return four_pillars.model_dump()
        except Exception:
            # パースエラー時はデフォルト値を返す
            return FourPillarsEvaluation().model_dump()

    def _extract_article_strategy(self, parsed_data: dict[str, Any]) -> dict[str, Any] | None:
        """Extract and validate article strategy from parsed data.

        Args:
            parsed_data: Parsed JSON data from LLM output

        Returns:
            dict with article strategy or None if not present
        """
        article_strategy_raw = parsed_data.get("article_strategy")
        if not article_strategy_raw:
            return None

        # バリデーション（警告のみ、失敗しても続行）
        validation_result = self.article_strategy_validator.validate_dict(article_strategy_raw)
        if not validation_result.is_valid:
            activity.logger.warning(f"Article strategy validation warnings: {validation_result.issues}")

        # Pydanticモデルで構造化（デフォルト値で補完）
        try:
            article_strategy = ArticleStrategy(**article_strategy_raw)
            return article_strategy.model_dump()
        except Exception:
            # パースエラー時はデフォルト値を返す
            return ArticleStrategy().model_dump()

    def _merge_cta_from_llm(
        self, parsed_data: dict[str, Any], cta_data: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """LLM出力の cta_design を CTA仕様にマージする.

        configでCTA URL/textが未設定の場合、LLMが生成した cta_design から補完する。

        Args:
            parsed_data: LLMのパース済みJSON出力
            cta_data: 現在のCTA仕様（config由来）

        Returns:
            マージ済みのCTA仕様 dict
        """
        if cta_data is None:
            return None

        cta_design = parsed_data.get("cta_design")
        if not cta_design or not isinstance(cta_design, dict):
            return cta_data

        placements = cta_data.get("placements", {})

        # LLMの cta_design から text を補完（URL/textが空の場合のみ）
        mapping = {
            "early": "early_cta",
            "mid": "mid_cta",
            "final": "final_cta",
        }
        for placement_key, design_key in mapping.items():
            placement = placements.get(placement_key, {})
            design = cta_design.get(design_key, {})
            if isinstance(design, dict) and isinstance(placement, dict):
                if not placement.get("text") and design.get("text"):
                    placement["text"] = design["text"]
                if not placement.get("url") and cta_design.get("cta_url_placeholder"):
                    placement["url"] = cta_design["cta_url_placeholder"]
            placements[placement_key] = placement

        cta_data["placements"] = placements
        return cta_data


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
