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
import re
from datetime import UTC, datetime
from typing import Any, TypedDict

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.activities.schemas.step10 import (
    ARTICLE_WORD_COUNT_TARGETS,
    ArticleStats,
    ArticleVariation,
    ArticleVariationType,
    HTMLValidationResult,
    PublicationReadiness,
    Step10Metadata,
    Step10Output,
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

        # Get LLM client
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "anthropic"))
        llm_model = model_config.get("model", config.get("llm_model"))
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

            activity.logger.info(f"Generating article {article_num}/4: {variation_type.value}")

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

            # Generate summary for next article (avoid duplication)
            if article_num < len(variations):
                summary = await self._generate_article_summary(llm, prompt_pack, config, article.content)
                previous_summaries.append(f"記事{article_num}（{variation_type.value}）: {summary}")

        # Generate checklist (once for all articles)
        checklist = await self._generate_checklist(llm, prompt_pack, config, keyword, warnings)

        # Build output
        metadata = Step10Metadata(
            generated_at=datetime.now(UTC),
            model=llm_provider,
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
            usage={"total_tokens": total_tokens},
            warnings=warnings,
        )

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

        return output.model_dump()

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
            base_content=base_content[:8000],  # Limit base content
            article_number=article_num,
            variation_type=variation_type.value,
            target_audience=target_audience,
            target_word_count_min=word_min,
            target_word_count_max=word_max,
            previous_summaries="\n".join(previous_summaries) if previous_summaries else "（最初の記事のため、前の記事はありません）",
        )

        # Generate content
        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 8000),
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

        return ArticleVariation(
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
            meta_description="",  # TODO: Generate per-article meta
            output_path=output_path,
            output_digest=output_digest,
        )

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
            max_tokens=config.get("max_tokens", 8000),
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


@activity.defn(name="step10_final_output")
async def step10_final_output(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 10."""
    step = Step10FinalOutput()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
