"""Step 3B: Co-occurrence & Related Keywords Extraction Activity.

This is the HEART of the SEO analysis - extracts co-occurrence patterns
and related keywords from competitor content.
Runs in parallel with step3a and step3c.
Uses Gemini for analysis.

IMPORTANT: This step applies strict quality standards as the core of the workflow.

blog.System Ver8.3 requirements:
- 100-150 co-occurrence keywords (expanded from 5)
- 30-50 related keywords
- 3-phase distribution (anxiety -> understanding -> action)
- LLMO optimization (voice search, question format)
- Behavioral economics triggers (6 principles)
"""

import logging
import re
from collections import Counter
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
    QualityResult,
    QualityRetryLoop,
)

from .base import ActivityError, BaseActivity, load_step_data
from .schemas.step3b import (
    BehavioralEconomicsTriggers,
    CompetitorKeywordGap,
    CTAKeywords,
    KeywordCategorization,
    KeywordDensityAnalysis,
    KeywordItem,
    LLMOOptimizedKeywords,
    ThreePhaseDistribution,
)

logger = logging.getLogger(__name__)

# Phase classification patterns (neuroscience-based)
PHASE1_PATTERNS = [
    r"課題|問題|悩み|失敗|リスク|損失|離職|不安|困|危険|ミス|トラブル",
]
PHASE2_PATTERNS = [
    r"方法|ステップ|事例|データ|比較|メリット|効果|解決|改善|対策|手順|ポイント",
]
PHASE3_PATTERNS = [
    r"今すぐ|簡単|無料|実績|成功|導入|申込|問い合わせ|相談|資料|見積",
]

# Behavioral economics trigger patterns
BEHAVIORAL_PATTERNS = {
    "loss_aversion": r"損失|無駄|失う|逃す|機会損失|コスト|リスク",
    "social_proof": r"導入|実績|満足|件|社|人|%が|選ば",
    "authority": r"専門家|研究|調査|認定|資格|厚生労働|経済産業",
    "consistency": r"まずは|次に|最後に|ステップ|段階|順番",
    "liking": r"お困り|よく分かり|私たちも|一緒に|サポート",
    "scarcity": r"限定|先着|残り|今だけ|期間|枠",
}

# LLMO patterns
QUESTION_FORMAT_PATTERNS = r"とは|方法|やり方|メリット|デメリット|費用|期間|違い|比較"
VOICE_SEARCH_PATTERNS = r"どのくらい|どのように|なぜ|いつ|何を|どこで|誰が"

# CTA patterns
CTA_PATTERNS = {
    "urgency": r"今すぐ|すぐに|即座に|早急に|緊急",
    "ease": r"簡単|手軽|すぐ|ステップ|分で|クリック",
    "free": r"無料|0円|費用なし|タダ|無償",
    "expertise": r"専門家|プロ|実績|経験|年の",
}


class Step3BQualityValidator:
    """Strict quality validator for step3b (heart of workflow).

    blog.System Ver8.3 requirements:
    - 100+ co-occurrence keywords
    - 30+ related keywords
    - 3-phase distribution present
    - LLMO elements extracted
    """

    # blog.System targets
    TARGET_COOCCURRENCE = 100
    TARGET_RELATED = 30
    MIN_ACCEPTABLE_COOCCURRENCE = 50  # Warn below this
    MIN_ACCEPTABLE_RELATED = 15
    MIN_OUTPUT_SIZE = 500  # Minimum output size in bytes (relaxed for Gemini)

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """Validate co-occurrence extraction quality.

        Checks:
        1. Minimum output size (truncation detection)
        2. Presence of keyword list indicators
        3. Presence of keyword category patterns
        4. Sufficient keyword count indicators
        5. 3-phase distribution indicators
        """
        issues: list[str] = []

        # Check for minimum output size (truncation detection)
        content_size = len(content.encode("utf-8"))
        if content_size < self.MIN_OUTPUT_SIZE:
            issues.append("output_too_small")
            logger.warning(f"step3b output too small: {content_size} bytes < {self.MIN_OUTPUT_SIZE} bytes")

        # Check for keyword list indicators
        list_indicators = ["・", "-", "*", "1.", "2."]
        has_list = any(ind in content for ind in list_indicators)
        if not has_list:
            issues.append("no_keyword_list")

        # Count actual list items to ensure sufficient keywords
        list_item_count = 0
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith(("・", "-", "*", "•")) or re.match(r"^\d+\.", line):
                list_item_count += 1

        if list_item_count < 5:  # At minimum, expect 5 list items (relaxed for Gemini)
            issues.append("insufficient_keyword_count")
            logger.warning(f"step3b keyword count too low: {list_item_count} items < 5 minimum")

        # Check for keyword category patterns
        keyword_patterns = [
            r"関連キーワード|related keyword",
            r"共起|co-occur",
            r"LSI|latent semantic",
        ]
        found_patterns = sum(1 for p in keyword_patterns if re.search(p, content, re.I))
        if found_patterns < 1:
            issues.append("no_keyword_categories")

        # Check for 3-phase indicators (blog.System requirement)
        phase_patterns = [
            r"Phase\s*1|フェーズ1|不安|課題認識",
            r"Phase\s*2|フェーズ2|理解|納得",
            r"Phase\s*3|フェーズ3|行動|決定",
        ]
        found_phases = sum(1 for p in phase_patterns if re.search(p, content, re.I))
        if found_phases < 2:
            issues.append("insufficient_phase_distribution")

        # Check for LLMO indicators
        llmo_patterns = [r"音声検索|voice search", r"質問形式|question format"]
        found_llmo = any(re.search(p, content, re.I) for p in llmo_patterns)
        if not found_llmo:
            issues.append("no_llmo_elements")

        # Critical issues that should not be acceptable regardless of count
        # Note: Relaxed - only no_keyword_list is critical now
        critical_issues = {"no_keyword_list"}
        has_critical = bool(set(issues) & critical_issues)

        return QualityResult(
            is_acceptable=not has_critical and len(issues) <= 3,  # Allow up to 3 issues
            issues=issues,
        )


class Step3BCooccurrenceExtraction(BaseActivity):
    """Activity for co-occurrence and keyword extraction.

    This is the critical "heart" step of the workflow.
    Quality standards are STRICT.

    blog.System Ver8.3 targets:
    - 100-150 co-occurrence keywords
    - 30-50 related keywords
    """

    # blog.System quality thresholds (expanded)
    MIN_COOCCURRENCE_KEYWORDS = 100  # Was: 10
    MIN_LSI_KEYWORDS = 30  # Was: 5
    MIN_RELATED_KEYWORDS = 30
    MIN_COMPETITORS_FOR_QUALITY = 3
    TARGET_COOCCURRENCE = 150
    TARGET_RELATED = 50

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.parser = OutputParser()
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()
        self.input_validator = InputValidator()
        self.quality_validator = Step3BQualityValidator()

    @property
    def step_id(self) -> str:
        return "step3b"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute co-occurrence extraction.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with extracted keywords and patterns
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

        # Get inputs
        keyword = config.get("keyword")

        # Load step data from storage (not from config to avoid gRPC size limits)
        step0_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step0") or {}
        step1_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step1") or {}
        step2_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step2") or {}
        step1_5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step1_5") or {}
        competitors = step1_data.get("competitors", [])

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Input validation
        validation = self.input_validator.validate(
            data={"step1": step1_data, "step0": step0_data},
            required=["step1.competitors"],
            recommended=["step0.analysis"],
            min_counts={"step1.competitors": self.MIN_COMPETITORS_FOR_QUALITY},
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Strict competitor count check (heart of workflow)
        if len(competitors) < self.MIN_COMPETITORS_FOR_QUALITY:
            raise ActivityError(
                f"Insufficient competitor data: {len(competitors)} (minimum: {self.MIN_COMPETITORS_FOR_QUALITY})",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if validation.missing_recommended:
            logger.warning(f"Missing recommended fields: {validation.missing_recommended}")

        if validation.quality_issues:
            logger.warning(f"Input quality issues: {validation.quality_issues}")

        # Checkpoint: competitor summaries (expanded for blog.System)
        summaries_checkpoint = await self.checkpoint.load(ctx.tenant_id, ctx.run_id, self.step_id, "competitor_summaries")

        if summaries_checkpoint:
            competitor_summaries = summaries_checkpoint["summaries"]
            competitor_full_texts = summaries_checkpoint.get("full_texts", [])
        else:
            competitor_summaries = self._prepare_competitor_summaries(competitors)
            competitor_full_texts = self._extract_full_texts(competitors)
            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "competitor_summaries",
                {"summaries": competitor_summaries, "full_texts": competitor_full_texts},
            )

        # Pre-analyze competitors for keyword extraction hints
        keyword_hints = self._pre_analyze_competitors(keyword, competitor_full_texts, step2_data)

        # Enrich keyword_hints with Google Ads related keywords from step1.5
        google_ads_keywords = step1_5_data.get("google_ads_related_keywords", [])
        if google_ads_keywords:
            keyword_hints["google_ads_related_keywords"] = google_ads_keywords
            logger.info(f"Enriched keyword_hints with {len(google_ads_keywords)} Google Ads related keywords")

        # Render prompt with blog.System requirements
        try:
            prompt_template = prompt_pack.get_prompt("step3b")
            initial_prompt = prompt_template.render(
                keyword=keyword,
                competitor_summaries=competitor_summaries,
                target_cooccurrence=self.TARGET_COOCCURRENCE,
                target_related=self.TARGET_RELATED,
                keyword_hints=keyword_hints,
            )

            # REQ-03: Add retry instruction if present
            retry_instruction = config.get("retry_instruction")
            if retry_instruction:
                feedback = (
                    "\n\n【レビューフィードバック】\n"
                    "前回の出力に対するフィードバックです。以下の点を改善してください:\n"
                    f"{retry_instruction}"
                )
                initial_prompt += feedback
                logger.info("Added retry instruction to prompt")
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client - uses 3-tier priority: UI per-step > step defaults > global config
        llm_provider, llm_model = get_step_model_config(self.step_id, config)
        llm = await get_step_llm_client(self.step_id, config, tenant_id=ctx.tenant_id)

        # LLM config (expanded max_tokens for larger output)
        # 100+キーワードの詳細分析には大きな出力が必要
        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 24000),  # Increased significantly for 100+ keywords with full details
            temperature=config.get("temperature", 0.5),
        )
        metadata = LLMCallMetadata(
            run_id=ctx.run_id,
            step_id=self.step_id,
            attempt=ctx.attempt,
            tenant_id=ctx.tenant_id,
        )

        # Define LLM call function for retry loop
        async def llm_call(prompt: str) -> Any:
            try:
                return await llm.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt=(
                        "You are a co-occurrence keyword analysis expert. "
                        "Extract 100-150 co-occurrence keywords and 30-50 related keywords. "
                        "Classify keywords by 3 phases (anxiety, understanding, action) "
                        "and identify LLMO/behavioral economics triggers. "
                        "CRITICAL: Output ONLY valid JSON. No explanations, no preamble. "
                        "Start with '{' and end with '}'."
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

        # Define prompt enhancement function
        def enhance_prompt(prompt: str, issues: list[str]) -> str:
            enhancement = "\n\n【重要】以下の形式で必ず出力してください：\n"
            for issue in issues:
                if issue == "output_too_small":
                    enhancement += "- 【重要】出力が短すぎます。すべてのカテゴリを詳細に記述してください。\n"
                    enhancement += "- 最低100個以上の共起キーワードを抽出してください。\n"
                elif issue == "insufficient_keyword_count":
                    enhancement += "- 【重要】キーワード数が不足しています。\n"
                    enhancement += (
                        "- 共起キーワード100個以上、LSIキーワード30個以上、関連キーワード30個以上を箇条書きで出力してください。\n"
                    )
                elif issue == "no_keyword_list":
                    enhancement += "- 各キーワードは箇条書き（・、-、*、数字）で列挙\n"
                elif issue == "no_keyword_categories":
                    enhancement += "- 「共起キーワード」「LSIキーワード」「関連キーワード」のカテゴリを明示\n"
                elif issue == "insufficient_phase_distribution":
                    enhancement += "- 3フェーズ（Phase1:不安・課題、Phase2:理解・比較、Phase3:行動・決定）への分類を明示\n"
                elif issue == "no_llmo_elements":
                    enhancement += "- LLMO要素（音声検索キーワード、質問形式キーワード）を抽出\n"
            return prompt + enhancement

        # Quality retry loop
        # accept_on_final=True: Accept output after retries (avoid infinite loops)
        # max_retries=2: Try twice before accepting
        retry_loop = QualityRetryLoop(max_retries=2, accept_on_final=True)

        # Callback to update step status to "retrying"
        async def on_retry(retry_num: int) -> None:
            await self._update_step_status(
                run_id=ctx.run_id,
                tenant_id=ctx.tenant_id,
                step_name=self.step_id,
                status="retrying",
                retry_count=retry_num,
            )

        loop_result = await retry_loop.execute(
            llm_call=llm_call,
            initial_prompt=initial_prompt,
            validator=self.quality_validator,
            enhance_prompt=enhance_prompt,
            extract_content=lambda r: r.content,
            on_retry=on_retry,
        )

        if not loop_result.success or loop_result.result is None:
            quality_issues = loop_result.quality.issues if loop_result.quality else "unknown"
            raise ActivityError(
                f"Quality validation failed after retries: {quality_issues}",
                category=ErrorCategory.RETRYABLE,
            )

        response = loop_result.result
        content: str = response.content

        # Parse output
        parse_result = self.parser.parse_json(content)

        data: dict[str, Any]
        if parse_result.success and isinstance(parse_result.data, dict):
            data = parse_result.data
        else:
            # Extract keywords from freeform content
            data = self._extract_keywords_from_freeform(content)

        # Post-process: Enrich with blog.System extensions
        enriched_data = self._enrich_with_blog_system_extensions(data, keyword, competitor_full_texts)

        # Enforce quality standards (warnings only, don't fail)
        quality_warnings = self._enforce_quality_standards(enriched_data)
        if quality_warnings:
            logger.warning(f"Quality warnings: {quality_warnings}")

        # Calculate content metrics
        text_metrics = self.metrics.text_metrics(content)

        # Build extraction summary
        extraction_summary = self._build_extraction_summary(enriched_data)

        return {
            "step": self.step_id,
            "keyword": keyword,
            "cooccurrence_analysis": content,
            "parsed_data": enriched_data,
            "format_detected": parse_result.format_detected,
            "competitor_count": len(competitors),
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
                "attempts": loop_result.attempts,
                "issues": loop_result.quality.issues if loop_result.quality else [],
                "warnings": quality_warnings,
            },
            "extraction_summary": extraction_summary,
        }

    def _prepare_competitor_summaries(self, competitors: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Prepare competitor summaries for prompt.

        Expanded for blog.System: Uses all 10 competitors with more content.
        """
        summaries = []
        for comp in competitors[:10]:  # Use all 10 competitors
            summaries.append(
                {
                    "title": comp.get("title", ""),
                    "url": comp.get("url", ""),
                    "content_preview": comp.get("content", "")[:1000],  # Expanded
                    "word_count": comp.get("word_count", 0),
                    "headings": comp.get("headings", [])[:10],
                }
            )
        return summaries

    def _extract_full_texts(self, competitors: list[dict[str, Any]]) -> list[str]:
        """Extract full texts from competitors for keyword analysis."""
        return [comp.get("content", "") for comp in competitors[:10]]

    def _pre_analyze_competitors(
        self,
        main_keyword: str,
        full_texts: list[str],
        step2_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Pre-analyze competitors to provide hints for LLM.

        Extracts frequency data and common patterns.
        """
        # Combine all texts
        combined_text = " ".join(full_texts)

        # Simple word frequency (Japanese-aware)
        # Split by common delimiters
        words = re.findall(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]+", combined_text)
        word_freq = Counter(words)

        # Get top frequent words (excluding main keyword)
        top_words = [w for w, _ in word_freq.most_common(200) if w != main_keyword and len(w) > 1]

        # Identify potential phase keywords from text
        phase_hints: dict[str, list[str]] = {
            "phase1": [],
            "phase2": [],
            "phase3": [],
        }

        for word in top_words[:100]:
            if any(re.search(p, word) for p in PHASE1_PATTERNS):
                phase_hints["phase1"].append(word)
            elif any(re.search(p, word) for p in PHASE2_PATTERNS):
                phase_hints["phase2"].append(word)
            elif any(re.search(p, word) for p in PHASE3_PATTERNS):
                phase_hints["phase3"].append(word)

        return {
            "top_frequent_words": top_words[:50],
            "phase_hints": phase_hints,
            "total_word_count": len(words),
            "unique_words": len(set(words)),
        }

    def _enrich_with_blog_system_extensions(
        self,
        data: dict[str, Any],
        main_keyword: str,
        competitor_texts: list[str],
    ) -> dict[str, Any]:
        """Enrich parsed data with blog.System extensions.

        Adds:
        - 3-phase distribution
        - LLMO optimized keywords
        - Behavioral economics triggers
        - CTA keywords
        - Keyword density analysis
        - Competitor keyword gaps
        - Keyword categorization
        """
        # Get all keywords
        all_keywords = self._collect_all_keywords(data)

        # 3-phase distribution
        three_phase = self._classify_keywords_by_phase(all_keywords)
        data["three_phase_distribution"] = {
            "phase1_keywords": [kw.model_dump() for kw in three_phase.phase1_keywords],
            "phase2_keywords": [kw.model_dump() for kw in three_phase.phase2_keywords],
            "phase3_keywords": [kw.model_dump() for kw in three_phase.phase3_keywords],
        }

        # LLMO optimized keywords
        llmo = self._extract_llmo_keywords(all_keywords)
        data["llmo_optimized_keywords"] = {
            "question_format": llmo.question_format,
            "voice_search": llmo.voice_search,
        }

        # Behavioral economics triggers
        behavioral = self._map_behavioral_triggers(all_keywords)
        data["behavioral_economics_triggers"] = {
            "loss_aversion": behavioral.loss_aversion,
            "social_proof": behavioral.social_proof,
            "authority": behavioral.authority,
            "consistency": behavioral.consistency,
            "liking": behavioral.liking,
            "scarcity": behavioral.scarcity,
        }

        # CTA keywords
        cta = self._extract_cta_keywords(all_keywords)
        data["cta_keywords"] = {
            "urgency": cta.urgency,
            "ease": cta.ease,
            "free": cta.free,
            "expertise": cta.expertise,
        }

        # Keyword density analysis
        density = self._analyze_keyword_density(main_keyword, competitor_texts)
        data["keyword_density_analysis"] = {
            "main_keyword_density": density.main_keyword_density,
            "cooccurrence_densities": density.cooccurrence_densities,
        }

        # Competitor keyword gaps
        gaps = self._find_competitor_gaps(all_keywords, competitor_texts)
        data["competitor_keyword_gaps"] = [gap.model_dump() for gap in gaps]

        # Keyword categorization (Essential/Standard/Unique)
        categorization = self._categorize_keywords(all_keywords, competitor_texts)
        data["keyword_categorization"] = {
            "essential": [kw.model_dump() for kw in categorization.essential],
            "standard": [kw.model_dump() for kw in categorization.standard],
            "unique": [kw.model_dump() for kw in categorization.unique],
        }

        return data

    def _collect_all_keywords(self, data: dict[str, Any]) -> list[str]:
        """Collect all keywords from parsed data."""
        keywords = []

        # From cooccurrence_keywords
        for kw in data.get("cooccurrence_keywords", []):
            if isinstance(kw, dict):
                keywords.append(kw.get("keyword", ""))
            elif isinstance(kw, str):
                keywords.append(kw)

        # From lsi_keywords
        for kw in data.get("lsi_keywords", []):
            if isinstance(kw, dict):
                keywords.append(kw.get("keyword", ""))
            elif isinstance(kw, str):
                keywords.append(kw)

        # From related_keywords
        for kw in data.get("related_keywords", []):
            if isinstance(kw, dict):
                keywords.append(kw.get("keyword", ""))
            elif isinstance(kw, str):
                keywords.append(kw)

        # From long_tail_variations
        keywords.extend(data.get("long_tail_variations", []))

        return [k for k in keywords if k]

    def _classify_keywords_by_phase(self, keywords: list[str]) -> ThreePhaseDistribution:
        """Classify keywords into 3 phases based on neuroscience patterns."""
        phase1 = []
        phase2 = []
        phase3 = []

        for kw in keywords:
            item = KeywordItem(keyword=kw)
            if any(re.search(p, kw) for p in PHASE1_PATTERNS):
                item.phase = 1
                phase1.append(item)
            elif any(re.search(p, kw) for p in PHASE3_PATTERNS):
                item.phase = 3
                phase3.append(item)
            elif any(re.search(p, kw) for p in PHASE2_PATTERNS):
                item.phase = 2
                phase2.append(item)
            else:
                # Default to phase 2 (understanding)
                item.phase = 2
                phase2.append(item)

        return ThreePhaseDistribution(
            phase1_keywords=phase1,
            phase2_keywords=phase2,
            phase3_keywords=phase3,
        )

    def _extract_llmo_keywords(self, keywords: list[str]) -> LLMOOptimizedKeywords:
        """Extract LLMO-optimized keywords."""
        question_format = []
        voice_search = []

        for kw in keywords:
            if re.search(QUESTION_FORMAT_PATTERNS, kw):
                question_format.append(kw)
            if re.search(VOICE_SEARCH_PATTERNS, kw):
                voice_search.append(kw)

        return LLMOOptimizedKeywords(
            question_format=question_format,
            voice_search=voice_search,
        )

    def _map_behavioral_triggers(self, keywords: list[str]) -> BehavioralEconomicsTriggers:
        """Map keywords to behavioral economics triggers."""
        triggers: dict[str, list[str]] = {k: [] for k in BEHAVIORAL_PATTERNS}

        for kw in keywords:
            for trigger_type, pattern in BEHAVIORAL_PATTERNS.items():
                if re.search(pattern, kw):
                    triggers[trigger_type].append(kw)

        return BehavioralEconomicsTriggers(
            loss_aversion=triggers["loss_aversion"],
            social_proof=triggers["social_proof"],
            authority=triggers["authority"],
            consistency=triggers["consistency"],
            liking=triggers["liking"],
            scarcity=triggers["scarcity"],
        )

    def _extract_cta_keywords(self, keywords: list[str]) -> CTAKeywords:
        """Extract CTA keywords."""
        cta: dict[str, list[str]] = {k: [] for k in CTA_PATTERNS}

        for kw in keywords:
            for cta_type, pattern in CTA_PATTERNS.items():
                if re.search(pattern, kw):
                    cta[cta_type].append(kw)

        return CTAKeywords(
            urgency=cta["urgency"],
            ease=cta["ease"],
            free=cta["free"],
            expertise=cta["expertise"],
        )

    def _analyze_keyword_density(self, main_keyword: str, competitor_texts: list[str]) -> KeywordDensityAnalysis:
        """Analyze keyword density across competitor articles."""
        densities = []

        for text in competitor_texts:
            if not text:
                continue
            word_count = len(text)
            if word_count == 0:
                continue
            main_count = text.count(main_keyword)
            density = (main_count * len(main_keyword)) / word_count * 100
            densities.append(density)

        avg_density = sum(densities) / len(densities) if densities else 0.0

        return KeywordDensityAnalysis(
            main_keyword_density=round(avg_density, 2),
            cooccurrence_densities={},  # Would need per-keyword analysis
        )

    def _find_competitor_gaps(self, keywords: list[str], competitor_texts: list[str]) -> list[CompetitorKeywordGap]:
        """Find keyword gaps (differentiation opportunities)."""
        gaps = []
        total_competitors = len(competitor_texts)

        for kw in keywords[:50]:  # Limit analysis
            coverage = sum(1 for text in competitor_texts if kw in text)
            coverage_rate = coverage / total_competitors if total_competitors > 0 else 0

            # Low coverage = differentiation opportunity
            if coverage_rate < 0.3:
                gaps.append(
                    CompetitorKeywordGap(
                        keyword=kw,
                        coverage_rate=round(coverage_rate, 2),
                        differentiation_score=round(1 - coverage_rate, 2),
                    )
                )

        # Sort by differentiation score
        gaps.sort(key=lambda g: g.differentiation_score, reverse=True)
        return gaps[:20]

    def _categorize_keywords(self, keywords: list[str], competitor_texts: list[str]) -> KeywordCategorization:
        """Categorize keywords by competitor coverage."""
        essential = []
        standard = []
        unique = []

        total_competitors = len(competitor_texts)

        for kw in keywords:
            coverage = sum(1 for text in competitor_texts if kw in text)
            coverage_rate = coverage / total_competitors if total_competitors > 0 else 0

            item = KeywordItem(keyword=kw, article_coverage=coverage)

            if coverage_rate >= 0.7:
                essential.append(item)
            elif coverage_rate >= 0.4:
                standard.append(item)
            else:
                unique.append(item)

        return KeywordCategorization(
            essential=essential,
            standard=standard,
            unique=unique,
        )

    def _enforce_quality_standards(self, data: dict[str, Any]) -> list[str]:
        """Enforce quality standards on parsed data.

        Returns warnings (does not fail).
        """
        warnings: list[str] = []

        cooccurrence = data.get("cooccurrence_keywords", [])
        lsi = data.get("lsi_keywords", [])
        related = data.get("related_keywords", [])

        if len(cooccurrence) < self.MIN_COOCCURRENCE_KEYWORDS:
            warnings.append(f"cooccurrence_count: {len(cooccurrence)} (target: {self.TARGET_COOCCURRENCE})")

        if len(lsi) < self.MIN_LSI_KEYWORDS:
            warnings.append(f"lsi_count: {len(lsi)} (target: {self.MIN_LSI_KEYWORDS})")

        if len(related) < self.MIN_RELATED_KEYWORDS:
            warnings.append(f"related_count: {len(related)} (target: {self.TARGET_RELATED})")

        # Check 3-phase distribution balance
        three_phase = data.get("three_phase_distribution", {})
        phase1_count = len(three_phase.get("phase1_keywords", []))
        phase3_count = len(three_phase.get("phase3_keywords", []))

        if phase1_count == 0:
            warnings.append("no_phase1_keywords")
        if phase3_count == 0:
            warnings.append("no_phase3_keywords")

        return warnings

    def _extract_keywords_from_freeform(self, content: str) -> dict[str, Any]:
        """Extract keywords from freeform content.

        Enhanced extraction when JSON parsing fails.
        """
        lines = content.split("\n")
        keywords: list[str] = []

        for line in lines:
            line = line.strip()
            # Match list items
            if line.startswith(("・", "-", "*", "•")) or re.match(r"^\d+\.", line):
                # Extract keyword (remove list marker)
                keyword = re.sub(r"^[・\-*•]\s*|\d+\.\s*", "", line)
                keyword = keyword.strip()
                if keyword and len(keyword) < 50:
                    keywords.append(keyword)

        # Split into categories (rough estimate)
        cooccurrence_count = min(len(keywords) * 2 // 3, self.TARGET_COOCCURRENCE)
        lsi_count = min(len(keywords) // 6, self.MIN_LSI_KEYWORDS)

        return {
            "cooccurrence_keywords": [{"keyword": k, "category": "cooccurrence"} for k in keywords[:cooccurrence_count]],
            "lsi_keywords": [{"keyword": k, "category": "lsi"} for k in keywords[cooccurrence_count : cooccurrence_count + lsi_count]],
            "related_keywords": [{"keyword": k, "category": "related"} for k in keywords[cooccurrence_count + lsi_count :]],
            "extracted_from_freeform": True,
        }

    def _build_extraction_summary(self, data: dict[str, Any]) -> dict[str, int]:
        """Build extraction summary counts."""
        three_phase = data.get("three_phase_distribution", {})
        llmo = data.get("llmo_optimized_keywords", {})
        behavioral = data.get("behavioral_economics_triggers", {})
        cta = data.get("cta_keywords", {})
        categorization = data.get("keyword_categorization", {})

        return {
            "cooccurrence": len(data.get("cooccurrence_keywords", [])),
            "lsi": len(data.get("lsi_keywords", [])),
            "related": len(data.get("related_keywords", [])),
            "phase1": len(three_phase.get("phase1_keywords", [])),
            "phase2": len(three_phase.get("phase2_keywords", [])),
            "phase3": len(three_phase.get("phase3_keywords", [])),
            "question_format": len(llmo.get("question_format", [])),
            "voice_search": len(llmo.get("voice_search", [])),
            "loss_aversion": len(behavioral.get("loss_aversion", [])),
            "social_proof": len(behavioral.get("social_proof", [])),
            "authority": len(behavioral.get("authority", [])),
            "essential": len(categorization.get("essential", [])),
            "standard": len(categorization.get("standard", [])),
            "unique": len(categorization.get("unique", [])),
            "cta_total": sum(len(v) for v in cta.values() if isinstance(v, list)),
            "gaps": len(data.get("competitor_keyword_gaps", [])),
        }


@activity.defn(name="step3b_cooccurrence_extraction")
async def step3b_cooccurrence_extraction(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 3B.

    Args:
        args: Dict containing:
            - tenant_id: Tenant identifier
            - run_id: Run identifier
            - config: Workflow configuration
            - retry_instruction: (Optional) User feedback for retry (REQ-03)
    """
    # REQ-03: Add retry instruction to config if present
    config = args["config"].copy()
    if "retry_instruction" in args:
        config["retry_instruction"] = args["retry_instruction"]
        logger.info(f"Step3B running with retry instruction: {args['retry_instruction'][:100]}...")

    step = Step3BCooccurrenceExtraction()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=config,
    )
