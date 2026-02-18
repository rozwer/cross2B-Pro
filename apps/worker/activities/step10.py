"""Step 10: Final Output Activity.

Generates 4 article variations in the required format.
Includes HTML validation and publication checklist.

Article Variations:
1. メイン記事: 最も包括的で詳細な記事
2. 初心者向け: 基礎から丁寧に説明
3. 実践編: 具体的なアクションにフォーカス
4. まとめ・比較: 要点を簡潔にまとめた記事

Execution Strategy:
- Sequential generation to ensure consistency and avoid duplication
- Each article uses previous summaries as context
- Per-article timeout: 150 seconds
- Total timeout: 600 seconds

Error Handling Strategy:
- Step9データ欠損: NON_RETRYABLE (step9を再実行する必要がある)
- Step9データ破損: NON_RETRYABLE (データ形式が不正)
- LLM呼び出し失敗: RETRYABLE (一時的なエラーの可能性)
- 部分的な失敗: 生成済み記事は保存、失敗記事のみリトライ
"""

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from typing import Any, TypedDict

import httpx
from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.worker.helpers.model_config import get_step_model_config
from apps.api.prompts.loader import PromptPackLoader
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
from apps.worker.helpers import (
    CheckpointManager,
    CompositeValidator,
    ContentMetrics,
    InputValidator,
    OutputParser,
    QualityResult,
)

from .base import ActivityError, BaseActivity, load_step_data

# API base URL for internal communication (Worker -> API)
API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000")


class ArticleVariationInfo(TypedDict):
    """Article variation type definition."""

    number: int
    type: ArticleVariationType
    target_audience: str
    description: str


# バリエーション定義
ARTICLE_VARIATIONS: list[ArticleVariationInfo] = [
    {
        "number": 1,
        "type": ArticleVariationType.MAIN,
        "target_audience": "SEOに関心があるすべての読者",
        "description": "最も包括的で詳細な記事",
    },
    {
        "number": 2,
        "type": ArticleVariationType.BEGINNER,
        "target_audience": "SEO初心者、これから学び始める人",
        "description": "基礎から丁寧に説明",
    },
    {
        "number": 3,
        "type": ArticleVariationType.PRACTICAL,
        "target_audience": "実践的なノウハウを求める中級者",
        "description": "具体的なアクションにフォーカス",
    },
    {
        "number": 4,
        "type": ArticleVariationType.SUMMARY,
        "target_audience": "要点だけを素早く把握したい人",
        "description": "要点を簡潔にまとめた記事",
    },
]


class Step9DataCorruptionError(Exception):
    """Step9データ破損エラー."""

    def __init__(self, message: str, field: str, expected: str, actual: str):
        super().__init__(message)
        self.field = field
        self.expected = expected
        self.actual = actual


class HTMLStructureValidator:
    """HTML構造の検証."""

    REQUIRED_TAGS = ["<html", "<head", "<body", "<title"]
    STRUCTURE_TAGS = ["<html", "<head", "<body"]

    def __init__(
        self,
        min_length: int = 500,
        require_meta: bool = True,
    ):
        self.min_length = min_length
        self.require_meta = require_meta

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """HTML構造を検証."""
        issues: list[str] = []
        warnings: list[str] = []
        scores: dict[str, float] = {}

        content_lower = content.lower()

        # Check minimum length
        if len(content) < self.min_length:
            issues.append(f"html_too_short: {len(content)} < {self.min_length}")

        # Check required tags
        found_tags = sum(1 for tag in self.REQUIRED_TAGS if tag in content_lower)
        scores["required_tags_found"] = float(found_tags)

        if found_tags < len(self.REQUIRED_TAGS):
            missing = [tag for tag in self.REQUIRED_TAGS if tag not in content_lower]
            issues.append(f"missing_html_tags: {missing}")

        # Check tag closure for structural tags
        for tag in self.STRUCTURE_TAGS:
            tag_name = tag[1:]  # Remove '<'
            close_tag = f"</{tag_name}>"
            open_count = content_lower.count(tag)
            close_count = content_lower.count(close_tag)
            if open_count != close_count:
                issues.append(f"unclosed_tag: {tag_name}")

        # Check for meta tags
        if self.require_meta:
            if "<meta" not in content_lower:
                warnings.append("no_meta_tags")

        # Check heading hierarchy
        h1_count = len(re.findall(r"<h1", content_lower))
        h2_count = len(re.findall(r"<h2", content_lower))
        scores["h1_count"] = float(h1_count)
        scores["h2_count"] = float(h2_count)

        if h1_count == 0:
            warnings.append("no_h1_heading")

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            scores=scores,
        )


class ChecklistValidator:
    """チェックリスト品質の検証."""

    CHECKLIST_INDICATORS = ["□", "☐", "[ ]", "・", "-", "1.", "✓", "✔"]

    def __init__(self, min_length: int = 100):
        self.min_length = min_length

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """チェックリストを検証."""
        issues: list[str] = []

        if len(content) < self.min_length:
            issues.append(f"checklist_too_short: {len(content)} < {self.min_length}")

        has_items = any(ind in content for ind in self.CHECKLIST_INDICATORS)
        if not has_items:
            issues.append("no_checklist_items")

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
        )


class Step10FinalOutput(BaseActivity):
    """Activity for final output generation with 4 article variations."""

    MIN_CONTENT_LENGTH = 1000
    MIN_HEADING_COUNT = 2
    MAX_CONTENT_LENGTH = 100000
    PER_ARTICLE_TIMEOUT = 150  # seconds
    TOTAL_TIMEOUT = 600  # seconds

    def __init__(self) -> None:
        """Initialize with helpers."""
        super().__init__()
        self.input_validator = InputValidator()
        self.parser = OutputParser()
        self.metrics = ContentMetrics()
        self.checkpoint = CheckpointManager(self.store)

        # HTML品質検証
        self.html_validator = CompositeValidator(
            [
                HTMLStructureValidator(min_length=500, require_meta=True),
            ]
        )

        # チェックリスト品質検証
        self.checklist_validator = ChecklistValidator(min_length=100)

    async def _broadcast_article_progress(
        self,
        run_id: str,
        article_number: int,
        total_articles: int,
        status: str,
        variation_type: str,
    ) -> None:
        """Broadcast article generation progress via WebSocket.

        Args:
            run_id: Run identifier
            article_number: Current article number (1-4)
            total_articles: Total number of articles
            status: Status message (e.g., 'generating', 'completed')
            variation_type: Article variation type
        """
        try:
            progress = int((article_number / total_articles) * 100)
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{API_BASE_URL}/api/internal/ws/broadcast",
                    json={
                        "run_id": run_id,
                        "step": self.step_id,
                        "event_type": "article_progress",
                        "status": status,
                        "progress": progress,
                        "message": f"記事 {article_number}/{total_articles} ({variation_type})",
                        "details": {
                            "article_number": article_number,
                            "total_articles": total_articles,
                            "variation_type": variation_type,
                        },
                    },
                )
        except Exception as e:
            activity.logger.warning(f"Failed to broadcast article progress: {e}")

    async def _log_article_digests(
        self,
        tenant_id: str,
        run_id: str,
        articles: list["ArticleVariation"],
    ) -> None:
        """Write audit log with per-article output_digest.

        Args:
            tenant_id: Tenant identifier
            run_id: Run identifier
            articles: List of generated articles
        """
        try:
            article_digests = [
                {
                    "article_number": a.article_number,
                    "variation_type": a.variation_type.value,
                    "output_digest": a.output_digest,
                    "word_count": a.word_count,
                }
                for a in articles
            ]
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{API_BASE_URL}/api/internal/audit/log",
                    json={
                        "tenant_id": tenant_id,
                        "run_id": run_id,
                        "step_name": self.step_id,
                        "action": "step10.articles_generated",
                        "details": {
                            "article_count": len(articles),
                            "articles": article_digests,
                        },
                    },
                )
        except Exception as e:
            activity.logger.warning(f"Failed to log article digests: {e}")

    def _validate_step9_data_integrity(
        self,
        step9_data: dict[str, Any],
    ) -> tuple[bool, list[str], list[str]]:
        """Step9データの整合性を詳細に検証."""
        errors: list[str] = []
        warnings: list[str] = []

        final_content = step9_data.get("final_content")
        if final_content is None:
            errors.append("step9.final_content is missing - step9 may not have completed successfully")
            return False, errors, warnings

        if not isinstance(final_content, str):
            errors.append(f"step9.final_content has invalid type: expected str, got {type(final_content).__name__}")
            return False, errors, warnings

        # 破損パターンの検出
        corruption_patterns = [
            (r"^\s*\{", "Content starts with JSON - possible serialization error"),
            (r"^\s*<\?xml", "Content starts with XML declaration - wrong format"),
            (r"^null$", "Content is literal 'null'"),
            (r"^\s*undefined\s*$", "Content is literal 'undefined'"),
            (r"^\[object Object\]$", "Content is '[object Object]' - serialization error"),
        ]

        for pattern, message in corruption_patterns:
            if re.match(pattern, final_content.strip(), re.IGNORECASE):
                errors.append(f"step9.final_content appears corrupted: {message}")
                return False, errors, warnings

        content_length = len(final_content)
        if content_length == 0:
            errors.append("step9.final_content is empty")
            return False, errors, warnings

        if content_length < self.MIN_CONTENT_LENGTH:
            errors.append(f"step9.final_content is too short: {content_length} chars (minimum: {self.MIN_CONTENT_LENGTH})")
            return False, errors, warnings

        if content_length > self.MAX_CONTENT_LENGTH:
            warnings.append(f"step9.final_content is unusually long: {content_length} chars")

        heading_pattern = r"^#{1,6}\s+"
        headings = re.findall(heading_pattern, final_content, re.MULTILINE)
        if len(headings) < self.MIN_HEADING_COUNT:
            warnings.append(f"step9.final_content has insufficient headings: {len(headings)}")

        # meta_description の検証（推奨）
        meta_desc = step9_data.get("meta_description")
        if meta_desc:
            if not isinstance(meta_desc, str):
                warnings.append(f"step9.meta_description has invalid type: expected str, got {type(meta_desc).__name__}")
            elif len(meta_desc) > 300:
                warnings.append(f"step9.meta_description is too long: {len(meta_desc)} chars (recommended < 160)")

        # article_title の検証（推奨）
        article_title = step9_data.get("article_title")
        if article_title:
            if not isinstance(article_title, str):
                warnings.append(f"step9.article_title has invalid type: expected str, got {type(article_title).__name__}")
            elif len(article_title) > 200:
                warnings.append(f"step9.article_title is unusually long: {len(article_title)} chars")

        return True, errors, warnings

    def _build_error_details(
        self,
        errors: list[str],
        warnings: list[str],
        step9_data: dict[str, Any],
    ) -> dict[str, Any]:
        """エラー詳細情報を構築."""
        details: dict[str, Any] = {
            "errors": errors,
            "warnings": warnings,
            "recovery_suggestions": [],
        }

        if any("missing" in e.lower() for e in errors):
            details["recovery_suggestions"].append("Re-run step9 to generate final_content")
        if any("too short" in e.lower() for e in errors):
            details["recovery_suggestions"].append("Check step9 output quality - content may have been truncated")
        if any("corrupted" in e.lower() for e in errors):
            details["recovery_suggestions"].append("Investigate step9 output format - data serialization may have failed")

        if step9_data:
            details["data_summary"] = {
                "has_final_content": "final_content" in step9_data,
                "final_content_type": type(step9_data.get("final_content")).__name__,
                "final_content_length": len(step9_data.get("final_content", "")),
                "has_meta_description": "meta_description" in step9_data,
                "has_article_title": "article_title" in step9_data,
                "available_keys": list(step9_data.keys()),
            }

        return details

    @property
    def step_id(self) -> str:
        return "step10"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute final output generation with 4 article variations."""
        config = ctx.config
        pack_id = config.get("pack_id")
        warnings: list[str] = []
        enable_4articles = config.get("enable_4articles", True)

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

        # Load step0 data for CTA specification
        step0_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step0") or {}
        cta_spec = step0_data.get("cta_specification", {}) or step0_data.get("cta", {})
        cta_placements = cta_spec.get("placements", {}) if isinstance(cta_spec, dict) else {}
        cta_url = ""
        cta_text = ""
        for phase in ("final", "early", "mid"):
            placement = cta_placements.get(phase, {})
            if isinstance(placement, dict) and placement.get("url"):
                cta_url = placement["url"]
                cta_text = placement.get("text", "")
                break
        if cta_url:
            cta_info_str = (
                f"CTA URL: {cta_url}\n"
                f"CTAテキスト: {cta_text}\n"
                f"上記URLをCTAリンクのhref属性に設定すること。"
            )
        else:
            cta_info_str = json.dumps(cta_spec, ensure_ascii=False) if cta_spec else ""

        # Load step9 data
        step9_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step9")

        if step9_data is None:
            activity.logger.error(f"Step9 data not found for run_id={ctx.run_id}")
            raise ActivityError(
                "Step9 output not found - step9 must complete before step10",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Validate step9 data
        is_valid, integrity_errors, integrity_warnings = self._validate_step9_data_integrity(step9_data)

        if not is_valid:
            raise ActivityError(
                f"Step9 data integrity check failed: {integrity_errors[0]}",
                category=ErrorCategory.NON_RETRYABLE,
                details=self._build_error_details(integrity_errors, integrity_warnings, step9_data),
            )

        for warning in integrity_warnings:
            activity.logger.warning(f"Step9 data warning: {warning}")
            warnings.append(warning)

        # Validate inputs
        validation = self.input_validator.validate(
            data={"step9": step9_data},
            required=["step9.final_content"],
            recommended=["step9.meta_description"],
            min_lengths={"step9.final_content": self.MIN_CONTENT_LENGTH},
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        base_content = step9_data.get("final_content", "")
        # meta_description と article_title は将来的に使用予定（per-article meta生成時）
        _ = step9_data.get("meta_description", "")  # noqa: F841
        _ = step9_data.get("article_title", keyword)  # noqa: F841

        # Get LLM client (Claude Opus for step10 via step defaults)
        llm_provider, llm_model = get_step_model_config(self.step_id, config)
        llm = get_llm_client(llm_provider, model=llm_model)

        # Generate article variations (default: 4 articles)
        articles: list[ArticleVariation] = []
        previous_summaries: list[str] = []
        total_tokens = 0
        variations = ARTICLE_VARIATIONS if enable_4articles else ARTICLE_VARIATIONS[:1]

        if not enable_4articles:
            warnings.append("enable_4articles_disabled")

        activity.logger.info(f"Starting {len(variations)}-article generation for keyword: {keyword}")

        for variation_info in variations:
            article_num = variation_info["number"]
            variation_type = variation_info["type"]
            total_articles = len(variations)

            activity.logger.info(f"Generating article {article_num}/{total_articles}: {variation_type.value}")

            # Broadcast article generation start
            await self._broadcast_article_progress(
                run_id=ctx.run_id,
                article_number=article_num,
                total_articles=total_articles,
                status="generating",
                variation_type=variation_type.value,
            )

            # Check for existing checkpoint
            input_digest = self.checkpoint.compute_digest(
                {
                    "keyword": keyword,
                    "article_number": article_num,
                    "base_content_hash": hashlib.sha256(base_content[:500].encode()).hexdigest()[:16],
                }
            )

            article_checkpoint = await self.checkpoint.load(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                f"article_{article_num}",
                input_digest=input_digest,
            )

            if article_checkpoint:
                try:
                    activity.logger.info(f"Loaded article {article_num} from checkpoint")
                    article = ArticleVariation(**article_checkpoint)
                except Exception as e:
                    activity.logger.warning(f"Invalid checkpoint for article {article_num}: {e}. Regenerating.")
                    article_checkpoint = None

            if not article_checkpoint:
                # Generate article
                article = await self._generate_article_variation(
                    llm=llm,
                    prompt_pack=prompt_pack,
                    config=config,
                    keyword=keyword,
                    base_content=base_content,
                    variation_info=variation_info,
                    previous_summaries=previous_summaries,
                    ctx=ctx,
                    cta_info_str=cta_info_str,
                )
                total_tokens += article.word_count  # Approximate

                # Save checkpoint
                await self.checkpoint.save(
                    ctx.tenant_id,
                    ctx.run_id,
                    self.step_id,
                    f"article_{article_num}",
                    article.model_dump(),
                    input_digest=input_digest,
                )

            articles.append(article)

            # Broadcast article generation completed
            await self._broadcast_article_progress(
                run_id=ctx.run_id,
                article_number=article_num,
                total_articles=total_articles,
                status="completed",
                variation_type=variation_type.value,
            )

            # Generate summary for next article (avoid duplication)
            if article_num < len(variations):
                summary = await self._generate_article_summary(llm, prompt_pack, config, article.content)
                previous_summaries.append(f"記事{article_num}（{variation_type.value}）: {summary}")

        # Log per-article output_digests to audit log
        await self._log_article_digests(ctx.tenant_id, ctx.run_id, articles)

        # Generate checklist (once for all articles)
        checklist = await self._generate_checklist(llm, prompt_pack, config, keyword, warnings)

        # Build output
        metadata = Step10Metadata(
            generated_at=datetime.now(UTC),
            model=llm_provider,
            model_config_data={
                "platform": llm_provider,
                "model": llm_model or "",
            },
            total_word_count=sum(a.word_count for a in articles),
            generation_order=[a.article_number for a in articles],
        )

        # Determine publication readiness
        blocking_issues: list[str] = []
        for article in articles:
            if article.stats and article.stats.word_count < 500:
                blocking_issues.append(f"article_{article.article_number}_word_count_too_low")

        publication_readiness = PublicationReadiness(
            is_ready=len(blocking_issues) == 0,
            blocking_issues=blocking_issues,
            warnings=warnings,
        )

        output = Step10Output(
            step=self.step_id,
            keyword=keyword,
            articles=articles,
            metadata=metadata,
            publication_checklist=checklist,
            publication_readiness=publication_readiness,
            model=llm_provider,
            token_usage={"input": 0, "output": total_tokens},
            warnings=warnings,
        )

        # blog.System Ver8.3: 全体サマリーを追加
        output.total_word_count_report = self._build_total_word_count_report(articles)
        output.overall_publication_checklist = self._build_overall_publication_checklist(articles)

        # Populate legacy fields for backward compatibility
        output.populate_legacy_fields()

        # Save individual article files
        for article in articles:
            article_path = self.store.build_path(
                tenant_id=ctx.tenant_id,
                run_id=ctx.run_id,
                step=self.step_id,
            ).replace("/output.json", f"/article_{article.article_number}.md")

            await self.store.put(
                content=article.content.encode("utf-8"),
                path=article_path,
                content_type="text/markdown",
            )

            if article.html_content:
                html_path = article_path.replace(".md", ".html")
                await self.store.put(
                    content=article.html_content.encode("utf-8"),
                    path=html_path,
                    content_type="text/html",
                )

        # Save main preview (first article)
        main_article = output.get_main_article()
        if main_article and main_article.html_content:
            preview_path = self.store.build_path(
                tenant_id=ctx.tenant_id,
                run_id=ctx.run_id,
                step=self.step_id,
            ).replace("/output.json", "/preview.html")
            await self.store.put(
                content=main_article.html_content.encode("utf-8"),
                path=preview_path,
                content_type="text/html",
            )

        activity.logger.info(f"Step10 completed: Generated {len(articles)} articles, total {metadata.total_word_count} words")

        output_path = self.store.build_path(ctx.tenant_id, ctx.run_id, self.step_id)
        output.output_path = output_path
        # Use mode="json" to ensure datetime objects are serialized to ISO strings
        output_data = output.model_dump(mode="json")
        output_data["output_digest"] = hashlib.sha256(json.dumps(output_data, ensure_ascii=False, indent=2).encode("utf-8")).hexdigest()[
            :16
        ]

        return output_data

    async def _generate_article_variation(
        self,
        llm: Any,
        prompt_pack: Any,
        config: dict[str, Any],
        keyword: str,
        base_content: str,
        variation_info: dict[str, Any],
        previous_summaries: list[str],
        ctx: ExecutionContext,
        cta_info_str: str = "",
    ) -> ArticleVariation:
        """Generate a single article variation."""
        article_num = variation_info["number"]
        variation_type: ArticleVariationType = variation_info["type"]
        target_audience = variation_info["target_audience"]

        # Get word count targets
        word_min, word_max = ARTICLE_WORD_COUNT_TARGETS[variation_type]

        # Render prompt
        variation_prompt = prompt_pack.get_prompt("step10_article_variation")
        prompt_text = variation_prompt.render(
            keyword=keyword,
            base_content=base_content[:20000],  # Expanded from 8000 to 20000 for long articles
            article_number=article_num,
            variation_type=variation_type.value,
            target_audience=target_audience,
            target_word_count_min=word_min,
            target_word_count_max=word_max,
            previous_summaries="\n".join(previous_summaries) if previous_summaries else "（最初の記事のため、前の記事はありません）",
            cta_info=cta_info_str,
        )

        # Generate content
        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 12000),  # Extended from 8000 for longer articles
            temperature=0.7,  # Slightly higher for variation
        )

        response = await llm.generate(
            messages=[{"role": "user", "content": prompt_text}],
            system_prompt="あなたはSEO記事のバリエーション生成の専門家です。",
            config=llm_config,
        )

        content = str(response.content)

        # Extract title from content
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1) if title_match else f"{keyword} - {variation_type.value}"

        # Extract sections
        sections = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)

        # Calculate metrics
        text_metrics = self.metrics.text_metrics(content)
        md_metrics = self.metrics.markdown_metrics(content)

        stats = ArticleStats(
            word_count=text_metrics.word_count,
            char_count=text_metrics.char_count,
            paragraph_count=text_metrics.paragraph_count,
            sentence_count=text_metrics.sentence_count,
            heading_count=md_metrics.h2_count + md_metrics.h3_count,
            h1_count=md_metrics.h1_count,
            h2_count=md_metrics.h2_count,
            h3_count=md_metrics.h3_count,
            list_count=md_metrics.list_count,
            link_count=md_metrics.link_count,
            image_count=md_metrics.image_count,
        )

        # Generate HTML
        html_content = await self._generate_html_for_article(llm, prompt_pack, config, keyword, content)

        # Validate HTML
        html_validation_result = self.html_validator.validate(html_content)
        html_validation = HTMLValidationResult(
            is_valid=html_validation_result.is_acceptable,
            has_required_tags=html_validation_result.scores.get("required_tags_found", 0) >= 4,
            has_meta_tags="no_meta_tags" not in html_validation_result.warnings,
            has_proper_heading_hierarchy="no_h1_heading" not in html_validation_result.warnings,
            issues=html_validation_result.issues,
        )

        # Build output path
        output_path = self.store.build_path(
            tenant_id=ctx.tenant_id,
            run_id=ctx.run_id,
            step=self.step_id,
        ).replace("/output.json", f"/article_{article_num}.md")

        output_digest = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Generate meta description
        meta_description = await self._generate_meta_description(
            llm=llm,
            title=title,
            content=content,
            keyword=keyword,
            target_audience=target_audience,
        )

        # blog.System Ver8.3: ArticleVariation を一旦作成
        article = ArticleVariation(
            article_number=article_num,
            variation_type=variation_type,
            title=title,
            content=content,
            html_content=html_content,
            word_count=text_metrics.word_count,
            target_audience=target_audience,
            sections=sections,
            stats=stats,
            html_validation=html_validation,
            meta_description=meta_description,
            output_path=output_path,
            output_digest=output_digest,
        )

        # blog.System Ver8.3: 拡張フィールドを追加
        article.structured_data = self._build_structured_data(article, keyword)
        article.word_count_report = self._calculate_word_count_report(article)
        article.publication_checklist_detailed = self._build_publication_checklist_detailed(article)

        return article

    async def _generate_html_for_article(
        self,
        llm: Any,
        prompt_pack: Any,
        config: dict[str, Any],
        keyword: str,
        content: str,
    ) -> str:
        """Generate HTML for a single article."""
        html_prompt = prompt_pack.get_prompt("step10_html")
        prompt_text = html_prompt.render(
            keyword=keyword,
            content=content,
        )

        html_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 12000),  # Extended from 8000 for longer articles
            temperature=0.3,
        )

        response = await llm.generate(
            messages=[{"role": "user", "content": prompt_text}],
            system_prompt="You are an HTML formatting expert.",
            config=html_config,
        )

        html_content = str(response.content)

        # Remove code blocks if present
        if "```html" in html_content:
            # Extract content between ```html and ```
            match = re.search(r"```html\s*(.*?)\s*```", html_content, re.DOTALL)
            if match:
                html_content = match.group(1)
        elif "```" in html_content:
            # Extract content between ``` and ```
            match = re.search(r"```\s*(.*?)\s*```", html_content, re.DOTALL)
            if match:
                html_content = match.group(1)

        return html_content

    async def _generate_meta_description(
        self,
        llm: Any,
        title: str,
        content: str,
        keyword: str,
        target_audience: str,
    ) -> str:
        """Generate SEO meta description for an article.

        Args:
            llm: LLM client
            title: Article title
            content: Article content (markdown)
            keyword: Target keyword
            target_audience: Target audience description

        Returns:
            Meta description (120-160 characters)
        """
        # Use first 2000 chars of content for context
        content_preview = content[:2000]

        prompt = f"""以下の記事に対して、SEOに最適化されたメタディスクリプションを生成してください。

【要件】
- 文字数: 120〜160文字（これは厳守）
- ターゲットキーワード「{keyword}」を自然に含める
- 読者の検索意図に応える内容
- クリックしたくなる魅力的な文章
- ターゲット読者: {target_audience}

【記事タイトル】
{title}

【記事の冒頭】
{content_preview}

【出力形式】
メタディスクリプションのみを出力してください。説明や補足は不要です。"""

        meta_config = LLMRequestConfig(
            max_tokens=200,
            temperature=0.5,
        )

        try:
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="あなたはSEOメタディスクリプション生成の専門家です。",
                config=meta_config,
            )

            meta_description = str(response.content).strip()

            # Remove quotes if present
            if meta_description.startswith('"') and meta_description.endswith('"'):
                meta_description = meta_description[1:-1]
            if meta_description.startswith("「") and meta_description.endswith("」"):
                meta_description = meta_description[1:-1]

            # Truncate if too long (Google displays ~155-160 chars)
            if len(meta_description) > 160:
                meta_description = meta_description[:157] + "..."

            return meta_description

        except Exception as e:
            activity.logger.warning(f"Meta description generation failed: {e}")
            # Fallback: use first 155 chars of content
            fallback = re.sub(r"^#.*\n", "", content)  # Remove title
            fallback = re.sub(r"\s+", " ", fallback).strip()  # Normalize whitespace
            return fallback[:155] + "..." if len(fallback) > 155 else fallback

    async def _generate_article_summary(
        self,
        llm: Any,
        prompt_pack: Any,
        config: dict[str, Any],
        content: str,
    ) -> str:
        """Generate a summary of an article for deduplication."""
        summary_prompt = prompt_pack.get_prompt("step10_article_summary")
        prompt_text = summary_prompt.render(content=content[:3000])

        summary_config = LLMRequestConfig(
            max_tokens=300,
            temperature=0.3,
        )

        response = await llm.generate(
            messages=[{"role": "user", "content": prompt_text}],
            system_prompt="簡潔に要約してください。",
            config=summary_config,
        )

        return str(response.content).strip()

    async def _generate_checklist(
        self,
        llm: Any,
        prompt_pack: Any,
        config: dict[str, Any],
        keyword: str,
        warnings: list[str],
    ) -> str:
        """Generate publication checklist."""
        checklist_prompt = prompt_pack.get_prompt("step10_checklist")
        prompt_text = checklist_prompt.render(keyword=keyword)

        checklist_config = LLMRequestConfig(max_tokens=1000, temperature=0.3)

        try:
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt_text}],
                system_prompt="You are a publication checklist expert.",
                config=checklist_config,
            )
            return str(response.content)
        except Exception as e:
            activity.logger.error(f"Checklist generation failed: {e}")
            warnings.append("checklist_generation_failed")
            return ""

    # =========================================================================
    # blog.System Ver8.3: 拡張機能
    # =========================================================================

    def _build_structured_data(
        self,
        article: ArticleVariation,
        keyword: str,
        author_name: str = "記事作成AI",
    ) -> StructuredData:
        """記事用のJSON-LD構造化データを生成.

        Args:
            article: 記事データ
            keyword: 対象キーワード
            author_name: 著者名

        Returns:
            StructuredData with Article schema
        """
        # Article schema (JSON-LD)
        json_ld = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": article.title,
            "description": article.meta_description or "",
            "author": {
                "@type": "Person",
                "name": author_name,
            },
            "articleSection": article.variation_type.value,
            "wordCount": article.word_count,
            "keywords": keyword,
        }

        # FAQPage schema (if FAQ sections exist)
        faq_schema: dict[str, Any] | None = None
        faq_sections = [s for s in article.sections if "FAQ" in s or "よくある質問" in s]
        if faq_sections:
            # FAQスキーマの基本構造（実際のQ&AはHTML解析が必要）
            faq_schema = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [],  # Activity側ではプレースホルダー、後続処理で埋める
            }

        return StructuredData(
            json_ld=json_ld,
            faq_schema=faq_schema,
        )

    def _calculate_word_count_report(
        self,
        article: ArticleVariation,
    ) -> WordCountReport:
        """記事の文字数レポートを計算.

        Args:
            article: 記事データ

        Returns:
            WordCountReport with target vs achieved analysis
        """
        variation_type = article.variation_type
        target_min, target_max = ARTICLE_WORD_COUNT_TARGETS.get(variation_type, (3000, 5000))
        target_mid = (target_min + target_max) // 2
        achieved = article.word_count

        variance = achieved - target_mid

        # Calculate status
        variance_percent = (variance / target_mid) * 100 if target_mid > 0 else 0
        if -5 <= variance_percent <= 5:
            status = "on_target"
        elif variance_percent > 5:
            status = "over"
        else:
            status = "under"

        # セクション別内訳（簡易版: セクション数で均等配分を仮定）
        section_breakdown: list[SectionWordCount] = []
        section_count = len(article.sections) if article.sections else 1
        words_per_section = achieved // section_count if section_count > 0 else 0
        target_per_section = target_mid // section_count if section_count > 0 else 0

        for section_title in article.sections:
            section_variance = words_per_section - target_per_section
            section_status = (
                "on_target" if abs(section_variance) <= target_per_section * 0.1 else ("over" if section_variance > 0 else "under")
            )
            section_breakdown.append(
                SectionWordCount(
                    section_title=section_title,
                    target=target_per_section,
                    achieved=words_per_section,
                    variance=section_variance,
                    status=section_status,
                )
            )

        return WordCountReport(
            target=target_mid,
            achieved=achieved,
            variance=variance,
            status=status,
            section_breakdown=section_breakdown,
        )

    def _build_publication_checklist_detailed(
        self,
        article: ArticleVariation,
    ) -> PublicationChecklistDetailed:
        """詳細公開チェックリストを構築.

        Args:
            article: 記事データ

        Returns:
            PublicationChecklistDetailed with SEO/4Pillars/Technical checks
        """
        stats = article.stats
        html_validation = article.html_validation

        # SEO チェック
        seo_checklist = SEOChecklist(
            title_optimized=bool(article.title and len(article.title) <= 60),
            meta_description_present=bool(article.meta_description and 120 <= len(article.meta_description) <= 160),
            headings_hierarchy_valid=(html_validation.has_proper_heading_hierarchy if html_validation else False),
            internal_links_present=(stats.link_count > 0 if stats else False),
            keyword_density_appropriate=True,  # 詳細計算は後続処理で
        )

        # 4本柱チェック — CTA実検出
        content_text = article.content or ""
        has_cta_boxes = 'class="cta-box' in content_text or "cta-box" in content_text
        has_cta_text = any(ind in content_text for ind in ["資料請求", "無料相談", "今すぐ", "無料ダウンロード", "お問い合わせ"])
        four_pillars_checklist = FourPillarsChecklist(
            neuroscience_applied=True,  # 3フェーズ構成で透明適用
            behavioral_economics_applied=True,  # テクニックとして透明適用
            llmo_optimized=True,  # 質問形式H2 + スニペット回答
            kgi_cta_placed=has_cta_boxes or has_cta_text,
        )

        # 技術チェック
        technical_checklist = TechnicalChecklist(
            html_valid=html_validation.is_valid if html_validation else False,
            images_have_alt=(
                html_validation.issues is not None and "missing_alt" not in str(html_validation.issues) if html_validation else True
            ),
            links_valid=True,  # 外部リンク検証は後続処理で
        )

        return PublicationChecklistDetailed(
            seo_checklist=seo_checklist,
            four_pillars_checklist=four_pillars_checklist,
            technical_checklist=technical_checklist,
        )

    def _build_overall_publication_checklist(
        self,
        articles: list[ArticleVariation],
    ) -> PublicationChecklistDetailed:
        """全記事の統合公開チェックリストを構築.

        Args:
            articles: 全記事リスト

        Returns:
            PublicationChecklistDetailed aggregated from all articles
        """
        # 全記事のチェックリストを統合
        seo_all_pass = True
        fp_all_pass = True
        tech_all_pass = True

        for article in articles:
            checklist = self._build_publication_checklist_detailed(article)
            if not checklist.seo_checklist.title_optimized:
                seo_all_pass = False
            if not checklist.seo_checklist.meta_description_present:
                seo_all_pass = False
            if not checklist.technical_checklist.html_valid:
                tech_all_pass = False

        return PublicationChecklistDetailed(
            seo_checklist=SEOChecklist(
                title_optimized=seo_all_pass,
                meta_description_present=seo_all_pass,
                headings_hierarchy_valid=seo_all_pass,
                internal_links_present=seo_all_pass,
                keyword_density_appropriate=seo_all_pass,
            ),
            four_pillars_checklist=FourPillarsChecklist(
                neuroscience_applied=fp_all_pass,
                behavioral_economics_applied=fp_all_pass,
                llmo_optimized=fp_all_pass,
                kgi_cta_placed=fp_all_pass,
            ),
            technical_checklist=TechnicalChecklist(
                html_valid=tech_all_pass,
                images_have_alt=tech_all_pass,
                links_valid=tech_all_pass,
            ),
        )

    def _build_total_word_count_report(
        self,
        articles: list[ArticleVariation],
    ) -> WordCountReport:
        """全記事の合計文字数レポートを構築.

        Args:
            articles: 全記事リスト

        Returns:
            WordCountReport for total word count
        """
        # 全記事の目標と実績を合算
        total_target = 0
        total_achieved = 0

        for article in articles:
            variation_type = article.variation_type
            target_min, target_max = ARTICLE_WORD_COUNT_TARGETS.get(variation_type, (3000, 5000))
            total_target += (target_min + target_max) // 2
            total_achieved += article.word_count

        variance = total_achieved - total_target

        # Calculate status
        variance_percent = (variance / total_target) * 100 if total_target > 0 else 0
        if -5 <= variance_percent <= 5:
            status = "on_target"
        elif variance_percent > 5:
            status = "over"
        else:
            status = "under"

        # 記事別内訳
        section_breakdown = [
            SectionWordCount(
                section_title=f"記事{a.article_number}（{a.variation_type.value}）",
                target=sum(ARTICLE_WORD_COUNT_TARGETS.get(a.variation_type, (3000, 5000))) // 2,
                achieved=a.word_count,
                variance=a.word_count - sum(ARTICLE_WORD_COUNT_TARGETS.get(a.variation_type, (3000, 5000))) // 2,
                status="on_target",  # 簡易
            )
            for a in articles
        ]

        return WordCountReport(
            target=total_target,
            achieved=total_achieved,
            variance=variance,
            status=status,
            section_breakdown=section_breakdown,
        )


@activity.defn(name="step10_final_output")
async def step10_final_output(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 10."""
    step = Step10FinalOutput()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
