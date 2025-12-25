"""Step 11: Image Generation Activity.

記事への画像生成・挿入を行う工程。
Human-in-the-loopで複数のサブステップを経て画像を生成・挿入する。

フロー:
1. 画像生成を行うか確認 (11A)
2. 画像設定入力 (11B)
3. 挿入候補分析 (11C)
4. ユーザー確認・修正 (11D)
5. 各画像の生成指示入力 (11E)
6. 画像生成＆確認 (11F)
7. HTML/Markdownへ画像挿入 (11G)
8. プレビュー表示 (11H)
"""

import base64
import hashlib
import re
from datetime import datetime
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.state import GraphState
from apps.api.llm import GeminiClient, LLMRequestConfig, NanoBananaClient
from apps.worker.activities.schemas.step11 import (
    GeneratedImage,
    ImageGenerationRequest,
    ImageInsertionPosition,
    PositionAnalysisResult,
    Step11Config,
    Step11Output,
)

from .base import BaseActivity, load_step_data, save_step_data


class Step11ImageGeneration(BaseActivity):
    """Activity for image generation and insertion.

    このActivityは通常のActivityとは異なり、Human-in-the-loopを
    Temporal signalで制御する。

    単独テスト時はsignal待ちをスキップし、設定済みのconfigで実行する。
    """

    def __init__(self) -> None:
        """Initialize with helpers."""
        super().__init__()
        self._gemini_client: GeminiClient | None = None
        self._image_client: NanoBananaClient | None = None

    @property
    def step_id(self) -> str:
        return "step11"

    def _get_gemini_client(self) -> GeminiClient:
        """GeminiClientを取得（遅延初期化）."""
        if self._gemini_client is None:
            self._gemini_client = GeminiClient()
        return self._gemini_client

    def _get_image_client(self) -> NanoBananaClient:
        """NanoBananaClientを取得（遅延初期化）."""
        if self._image_client is None:
            self._image_client = NanoBananaClient()
        return self._image_client

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute image generation.

        NOTE: この実装は単独テスト用。
        実際のワークフローではsignal待機を使う。

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with step11 output
        """
        config = ctx.config
        warnings: list[str] = []

        # Step10のデータを読み込み
        step10_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step10") or {}

        # 4記事対応: articles配列から読み込み、なければlegacy形式にフォールバック
        articles_data = step10_data.get("articles", [])
        keyword = step10_data.get("keyword", "")

        # 後方互換性: 単一記事の場合
        if not articles_data and step10_data.get("markdown_content"):
            articles_data = [
                {
                    "article_number": 1,
                    "title": step10_data.get("article_title", keyword),
                    "content": step10_data.get("markdown_content", ""),
                    "html_content": step10_data.get("html_content", ""),
                }
            ]

        if not articles_data:
            # 画像生成をスキップ
            return Step11Output(
                step=self.step_id,
                enabled=False,
                warnings=["step10_data_missing"],
            ).model_dump()

        # Step11設定を取得
        step11_config = Step11Config(
            enabled=config.get("step11_enabled", True),
            image_count=config.get("step11_image_count", 3),
            position_request=config.get("step11_position_request", ""),
        )

        if not step11_config.enabled:
            # 全記事のコンテンツを結合（後方互換性）
            first_article = articles_data[0] if articles_data else {}
            return Step11Output(
                step=self.step_id,
                enabled=False,
                markdown_with_images=first_article.get("content", first_article.get("markdown_content", "")),
                html_with_images=first_article.get("html_content", ""),
            ).model_dump()

        activity.logger.info(
            f"Step11: Starting image generation for {len(articles_data)} articles, count={step11_config.image_count} per article"
        )

        # 全記事に対して画像を生成
        all_generated_images: list[GeneratedImage] = []
        total_tokens = 0
        total_analysis_tokens = 0
        global_image_index = 0

        for article_data in articles_data:
            article_number = article_data.get("article_number", 1)
            article_title = article_data.get("title", keyword)
            markdown_content = article_data.get("content", article_data.get("markdown_content", ""))
            # html_content は現在未使用（将来のHTML画像挿入用に保持可能）

            if not markdown_content:
                warnings.append(f"article_{article_number}_no_content")
                continue

            activity.logger.info(f"Step11: Processing article {article_number}: {article_title[:50]}...")

            # 1. 挿入位置を分析
            position_analysis = await self._analyze_positions(
                markdown_content=markdown_content,
                article_title=article_title,
                keyword=keyword,
                image_count=step11_config.image_count,
                position_request=step11_config.position_request,
            )
            total_analysis_tokens += position_analysis.usage.get("tokens", 0)

            if not position_analysis.positions:
                warnings.append(f"article_{article_number}_no_positions_found")
                continue

            # 2. 各位置に対して画像を生成
            for i, position in enumerate(position_analysis.positions):
                activity.logger.info(
                    f"Generating image {global_image_index + 1} (article {article_number}, pos {i + 1}): {position.section_title}"
                )

                try:
                    # 画像生成プロンプトを作成
                    image_prompt = await self._create_image_prompt(
                        position=position,
                        article_title=article_title,
                        keyword=keyword,
                    )

                    # 画像を生成
                    image_result = await self._generate_image(
                        prompt=image_prompt,
                        position=position,
                    )

                    if image_result:
                        # storageに保存（記事番号を含むパス）
                        image_path = await self._save_image_to_storage_with_article(
                            ctx=ctx,
                            image_data=image_result["image_data"],
                            article_number=article_number,
                            image_index=i,
                        )

                        generated_image = GeneratedImage(
                            request=ImageGenerationRequest(
                                position=position,
                                generated_prompt=image_prompt,
                                alt_text=image_result.get("alt_text", position.description),
                            ),
                            image_path=image_path,
                            image_digest=image_result.get("digest", ""),
                            image_base64=image_result.get("base64", ""),
                            mime_type="image/png",
                            file_size=len(image_result["image_data"]),
                            accepted=True,  # 単独テストでは自動承認
                            article_number=article_number,  # 記事番号を付与
                        )
                        all_generated_images.append(generated_image)
                        total_tokens += image_result.get("tokens", 0)
                        global_image_index += 1

                except Exception as e:
                    activity.logger.error(f"Failed to generate image for article {article_number}, pos {i + 1}: {e}")
                    warnings.append(f"article_{article_number}_image_{i + 1}_generation_failed: {str(e)}")

        # 3. 各記事に画像を挿入して結果を構築
        # 後方互換性のため、最初の記事のコンテンツを final として返す
        if articles_data:
            first_article = articles_data[0]
            article_1_images = [img for img in all_generated_images if img.article_number == 1]
            first_markdown = first_article.get("content", first_article.get("markdown_content", ""))
            first_html = first_article.get("html_content", "")
            final_markdown = self._insert_images_to_markdown(first_markdown, article_1_images)
            final_html = self._insert_images_to_html(first_html, article_1_images)
        else:
            final_markdown = ""
            final_html = ""

        # HTMLプレビューを保存
        if final_html:
            preview_path = self.store.build_path(
                tenant_id=ctx.tenant_id,
                run_id=ctx.run_id,
                step=self.step_id,
            ).replace("/output.json", "/preview.html")
            await self.store.put(
                content=final_html.encode("utf-8"),
                path=preview_path,
                content_type="text/html",
            )

        return Step11Output(
            step=self.step_id,
            enabled=True,
            image_count=len(all_generated_images),
            images=all_generated_images,
            markdown_with_images=final_markdown,
            html_with_images=final_html,
            model="gemini-2.5-flash-image",
            usage={
                "analysis_tokens": total_analysis_tokens,
                "image_tokens": total_tokens,
            },
            warnings=warnings,
        ).model_dump()

    async def _analyze_positions(
        self,
        markdown_content: str,
        article_title: str,
        keyword: str,
        image_count: int,
        position_request: str,
    ) -> PositionAnalysisResult:
        """記事を分析して画像挿入位置を特定.

        Args:
            markdown_content: 記事のMarkdownコンテンツ
            article_title: 記事タイトル
            keyword: キーワード
            image_count: 生成する画像数
            position_request: 位置に関するユーザーリクエスト

        Returns:
            PositionAnalysisResult
        """
        gemini = self._get_gemini_client()

        # セクション構造を抽出
        sections = self._extract_sections(markdown_content)
        sections_text = "\n".join([f"[{i}] {s['level']}: {s['title']}" for i, s in enumerate(sections)])

        system_prompt = f"""あなたはSEO記事の画像配置を最適化する専門家です。

以下の記事を分析し、読者の理解を助け、記事の価値を高めるための画像挿入ポイントを**正確に{image_count}箇所**特定してください。

## 画像挿入の基準

1. **概念の視覚化**: 抽象的な概念を図解で説明できる箇所
2. **プロセスの説明**: 手順やフローを視覚的に示せる箇所
3. **比較・対比**: 複数の要素を比較している箇所
4. **重要なポイント**: 読者が特に注目すべき重要な内容

{("## ユーザーからのリクエスト" + chr(10) + position_request) if position_request else ""}
"""

        user_message = f"""# 記事情報

**タイトル**: {article_title}
**キーワード**: {keyword}

## セクション構造

{sections_text}

## 記事本文（抜粋）

{markdown_content[:6000]}

---

上記の記事を分析し、最適な画像挿入ポイントを{image_count}箇所特定してください。
"""

        schema = {
            "type": "object",
            "properties": {
                "analysis_summary": {"type": "string"},
                "positions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "section_title": {"type": "string"},
                            "section_index": {"type": "integer"},
                            "position": {"type": "string", "enum": ["before", "after"]},
                            "source_text": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["section_title", "section_index", "position", "source_text", "description"],
                    },
                },
            },
            "required": ["analysis_summary", "positions"],
        }

        config = LLMRequestConfig(temperature=0.3, max_tokens=4096)

        try:
            # generate_json_with_usage でトークン使用量も取得
            response = await gemini.generate_json_with_usage(
                messages=[{"role": "user", "content": user_message}],
                system_prompt=system_prompt,
                schema=schema,
                config=config,
            )

            result = response.data
            token_usage = response.token_usage

            positions = [
                ImageInsertionPosition(
                    section_title=p["section_title"],
                    section_index=p["section_index"],
                    position=p["position"],
                    source_text=p.get("source_text", ""),
                    description=p.get("description", ""),
                )
                for p in result.get("positions", [])
            ]

            return PositionAnalysisResult(
                analysis_summary=result.get("analysis_summary", ""),
                positions=positions,
                model=response.model,
                usage={
                    "input_tokens": token_usage.input,
                    "output_tokens": token_usage.output,
                    "total_tokens": token_usage.total,
                },
            )

        except Exception as e:
            activity.logger.error(f"Position analysis failed: {e}")
            return PositionAnalysisResult(
                analysis_summary=f"Analysis failed: {e}",
                positions=[],
            )

    async def _create_image_prompt(
        self,
        position: ImageInsertionPosition,
        article_title: str,
        keyword: str,
    ) -> str:
        """画像生成プロンプトを作成.

        Args:
            position: 挿入位置情報
            article_title: 記事タイトル
            keyword: キーワード

        Returns:
            英語の画像生成プロンプト
        """
        return await self._create_image_prompt_with_instruction(
            position=position,
            article_title=article_title,
            keyword=keyword,
            user_instruction="",
        )

    async def _create_image_prompt_with_instruction(
        self,
        position: ImageInsertionPosition,
        article_title: str,
        keyword: str,
        user_instruction: str = "",
    ) -> str:
        """ユーザー指示を含む画像生成プロンプトを作成.

        Args:
            position: 挿入位置情報
            article_title: 記事タイトル
            keyword: キーワード
            user_instruction: ユーザーからの追加指示

        Returns:
            英語の画像生成プロンプト
        """
        gemini = self._get_gemini_client()

        system_prompt = """あなたは画像生成AI用のプロンプトを作成する専門家です。
与えられた情報から、高品質な画像を生成するための詳細なプロンプトを英語で作成してください。

プロンプトの要件:
- 英語で記述
- 具体的で詳細な描写（色、構図、スタイルを明記）
- SEO記事に適した、プロフェッショナルでクリーンなデザイン
- フラットデザイン、インフォグラフィック風、またはイラスト風のスタイル
- テキストは含めない（言語に依存しないビジュアル）
"""

        user_instruction_section = ""
        if user_instruction:
            user_instruction_section = f"""

## ユーザーからの追加指示
{user_instruction}
"""

        user_message = f"""以下の情報から画像生成プロンプトを作成してください。

記事タイトル: {article_title}
キーワード: {keyword}
セクション: {position.section_title}
説明: {position.description}
元テキスト: {position.source_text[:500]}{user_instruction_section}

プロンプトのみを出力してください（説明不要）。
"""

        config = LLMRequestConfig(temperature=0.5, max_tokens=500)

        try:
            response = await gemini.generate(
                messages=[{"role": "user", "content": user_message}],
                system_prompt=system_prompt,
                config=config,
            )

            prompt = response.content.strip()

            # スタイル指示を追加
            style_suffix = """

Style: Clean, professional, modern flat design illustration.
Colors: Vibrant but balanced color palette, suitable for blog/web content.
Composition: Clear focal point, good use of negative space.
Quality: High resolution, crisp edges, suitable for web display.
No text or watermarks in the image."""

            return f"{prompt}{style_suffix}"

        except Exception as e:
            activity.logger.error(f"Prompt creation failed: {e}")
            # フォールバックプロンプト
            return f"""Professional infographic illustration about {keyword}.
Topic: {position.section_title}.
Style: Clean, modern flat design with vibrant colors.
No text in the image."""

    async def _generate_image(
        self,
        prompt: str,
        position: ImageInsertionPosition,
    ) -> dict[str, Any] | None:
        """画像を生成.

        Args:
            prompt: 画像生成プロンプト
            position: 挿入位置情報

        Returns:
            生成結果（image_data, base64, digest, alt_text）またはNone
        """
        try:
            image_client = self._get_image_client()
            result = await image_client.generate_image(prompt=prompt)

            if not result.images:
                return None

            image_data = result.images[0]
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            image_digest = hashlib.sha256(image_data).hexdigest()

            return {
                "image_data": image_data,
                "base64": image_base64,
                "digest": image_digest,
                "alt_text": position.description,
                "tokens": result.token_usage.total if result.token_usage else 0,
            }

        except Exception as e:
            activity.logger.error(f"Image generation failed: {e}")
            return None

    async def _save_image_to_storage(
        self,
        ctx: ExecutionContext,
        image_data: bytes,
        image_index: int,
    ) -> str:
        """画像をstorageに保存.

        Args:
            ctx: 実行コンテキスト
            image_data: 画像バイナリ
            image_index: 画像インデックス

        Returns:
            保存先パス
        """
        path = f"tenants/{ctx.tenant_id}/runs/{ctx.run_id}/{self.step_id}/images/image_{image_index + 1}.png"

        await self.store.put(
            content=image_data,
            path=path,
            content_type="image/png",
        )

        return path

    async def _save_image_to_storage_with_article(
        self,
        ctx: ExecutionContext,
        image_data: bytes,
        article_number: int,
        image_index: int,
    ) -> str:
        """記事番号を含むパスで画像をstorageに保存.

        Args:
            ctx: 実行コンテキスト
            image_data: 画像バイナリ
            article_number: 記事番号（1-4）
            image_index: 画像インデックス（記事内）

        Returns:
            保存先パス
        """
        path = f"tenants/{ctx.tenant_id}/runs/{ctx.run_id}/{self.step_id}/images/article_{article_number}/image_{image_index + 1}.png"

        await self.store.put(
            content=image_data,
            path=path,
            content_type="image/png",
        )

        return path

    def _extract_sections(self, markdown_content: str) -> list[dict[str, Any]]:
        """Markdownから見出し構造を抽出."""
        sections = []
        heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)

        for match in heading_pattern.finditer(markdown_content):
            level = len(match.group(1))
            title = match.group(2).strip()
            sections.append(
                {
                    "level": f"h{level}",
                    "title": title,
                    "start_pos": match.start(),
                }
            )

        return sections

    def _insert_images_to_markdown(
        self,
        markdown_content: str,
        images: list[GeneratedImage],
    ) -> str:
        """画像をMarkdownに挿入.

        Args:
            markdown_content: 元のMarkdownコンテンツ
            images: 生成された画像リスト

        Returns:
            画像挿入後のMarkdown
        """
        if not images:
            return markdown_content

        # セクション位置をマッピング
        sections = self._extract_sections(markdown_content)

        # 挿入位置を後ろから処理（位置がずれないように）
        insertions: list[tuple[int, str]] = []

        for img in images:
            section_idx = img.request.position.section_index
            if section_idx >= len(sections):
                continue

            section = sections[section_idx]
            position = img.request.position.position

            # 画像Markdownを作成
            image_md = f"\n\n![{img.request.alt_text}]({img.image_path})\n\n"

            if position == "before":
                insert_pos = section["start_pos"]
            else:
                # セクションの次の見出しまたは文末
                if section_idx + 1 < len(sections):
                    insert_pos = sections[section_idx + 1]["start_pos"]
                else:
                    insert_pos = len(markdown_content)

            insertions.append((insert_pos, image_md))

        # 後ろから挿入
        insertions.sort(key=lambda x: x[0], reverse=True)
        result = markdown_content
        for pos, image_md in insertions:
            result = result[:pos] + image_md + result[pos:]

        return result

    def _insert_images_to_html(
        self,
        html_content: str,
        images: list[GeneratedImage],
    ) -> str:
        """画像をHTMLに挿入.

        Args:
            html_content: 元のHTMLコンテンツ
            images: 生成された画像リスト

        Returns:
            画像挿入後のHTML
        """
        if not images or not html_content:
            return html_content

        # h2/h3タグを探して挿入
        for img in images:
            section_title = img.request.position.section_title
            position = img.request.position.position

            # HTMLエスケープを考慮してセクションを検索
            # 単純なテキストマッチで探す
            patterns = [
                f"<h2[^>]*>{re.escape(section_title)}</h2>",
                f"<h3[^>]*>{re.escape(section_title)}</h3>",
                f"<h2[^>]*>.*{re.escape(section_title[:20])}.*</h2>",
                f"<h3[^>]*>.*{re.escape(section_title[:20])}.*</h3>",
            ]

            for pattern in patterns:
                match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
                if match:
                    # 画像HTMLを作成
                    image_html = f'''
    <figure style="margin: 2em 0; text-align: center;">
        <img src="data:image/png;base64,{img.image_base64}"
             alt="{img.request.alt_text}"
             style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <figcaption style="margin-top: 0.5em; font-size: 0.9em; color: #666;">
            {img.request.alt_text}
        </figcaption>
    </figure>
'''

                    if position == "before":
                        html_content = html_content[: match.start()] + image_html + html_content[match.start() :]
                    else:
                        html_content = html_content[: match.end()] + image_html + html_content[match.end() :]
                    break

        return html_content


@activity.defn(name="step11_image_generation")
async def step11_image_generation(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 11 (legacy single-phase)."""
    step = Step11ImageGeneration()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )


# ========== Multi-phase Activity Functions ==========


@activity.defn(name="step11_mark_skipped")
async def step11_mark_skipped(args: dict[str, Any]) -> dict[str, Any]:
    """Mark step11 as skipped.

    If step11 data already exists (e.g., saved by API finalize_images),
    return it without overwriting. This prevents overwriting images
    processed through the API flow.

    Args:
        args: Activity arguments with tenant_id, run_id, config

    Returns:
        dict with artifact_ref and status
    """
    step = Step11ImageGeneration()

    output_path = step.store.build_path(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        step="step11",
    )

    # Check if step11 data already exists (e.g., saved by API finalize_images)
    existing_data = await load_step_data(step.store, args["tenant_id"], args["run_id"], "step11")
    if existing_data and existing_data.get("images"):
        # Step11 was already processed via API with images - don't overwrite
        activity.logger.info(f"Step11 data already exists with {len(existing_data.get('images', []))} images, skipping overwrite")
        return {
            "status": "completed_via_api",
            "artifact_ref": {
                "path": output_path,
                "digest": hashlib.sha256(str(existing_data).encode()).hexdigest()[:16],
            },
        }

    # Load step10 data to pass through markdown/html unchanged
    step10_data = await load_step_data(step.store, args["tenant_id"], args["run_id"], "step10") or {}

    output = Step11Output(
        step="step11",
        enabled=False,
        image_count=0,
        markdown_with_images=step10_data.get("markdown_content", ""),
        html_with_images=step10_data.get("html_content", ""),
        warnings=["skipped_by_user"],
    )

    output_data = output.model_dump()
    await save_step_data(
        step.store,
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        step="step11",
        data=output_data,
    )

    return {
        "status": "skipped",
        "artifact_ref": {
            "path": output_path,
            "digest": hashlib.sha256(str(output_data).encode()).hexdigest()[:16],
        },
    }


@activity.defn(name="step11_analyze_positions")
async def step11_analyze_positions(args: dict[str, Any]) -> dict[str, Any]:
    """Analyze article to propose image insertion positions.

    Phase 11B: LLM analyzes the article and identifies optimal insertion points.

    Args:
        args: Activity arguments with:
            - tenant_id: Tenant identifier
            - run_id: Run identifier
            - config: Configuration with step11_image_count, step11_position_request

    Returns:
        dict with positions list and analysis_summary
    """
    step = Step11ImageGeneration()

    # Load step10 data
    step10_data = await load_step_data(step.store, args["tenant_id"], args["run_id"], "step10") or {}

    keyword = step10_data.get("keyword", "")
    articles_data = step10_data.get("articles", [])

    # Backward compatibility: single-article output
    if not articles_data and step10_data.get("markdown_content"):
        articles_data = [
            {
                "article_number": 1,
                "title": step10_data.get("article_title", keyword),
                "content": step10_data.get("markdown_content", ""),
            }
        ]

    if not articles_data:
        return {
            "positions": [],
            "analysis_summary": "No markdown content available",
            "sections": [],
        }

    config = args.get("config", {})
    image_count = config.get("step11_image_count", 3)
    position_request = config.get("step11_position_request", "")

    positions: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    summaries: list[str] = []

    for article_data in articles_data:
        article_number = article_data.get("article_number", 1)
        article_title = article_data.get("title", keyword)
        markdown_content = article_data.get("content", article_data.get("markdown_content", ""))

        if not markdown_content:
            continue

        activity.logger.info(f"Step11 (11B): Analyzing positions for article {article_number} ({article_title}), count={image_count}")

        # Analyze positions per article
        position_result = await step._analyze_positions(
            markdown_content=markdown_content,
            article_title=article_title,
            keyword=keyword,
            image_count=image_count,
            position_request=position_request,
        )

        for pos in position_result.positions:
            pos.article_number = article_number
            positions.append(pos.model_dump())

        # Extract sections for UI to display
        article_sections = step._extract_sections(markdown_content)
        for idx, section in enumerate(article_sections):
            section["section_index"] = idx
            section["article_number"] = article_number
            section["section_key"] = f"{article_number}:{idx}"
        sections.extend(article_sections)

        if position_result.analysis_summary:
            summaries.append(f"記事{article_number}: {position_result.analysis_summary}")

    # Save intermediate result
    result_data = {
        "positions": positions,
        "analysis_summary": " / ".join(summaries) if summaries else "",
        "sections": sections,
        "model": "gemini",
    }

    await save_step_data(
        step.store,
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        step="step11",
        data={"position_analysis": result_data},
        filename="positions.json",
    )

    return result_data


@activity.defn(name="step11_generate_images")
async def step11_generate_images(args: dict[str, Any]) -> dict[str, Any]:
    """Generate images for all positions with user instructions.

    Phase 11D: Generate images based on confirmed positions and user instructions.

    Args:
        args: Activity arguments with:
            - tenant_id: Tenant identifier
            - run_id: Run identifier
            - config: Configuration
            - positions: List of confirmed positions
            - instructions: List of user instructions per position

    Returns:
        dict with images list
    """
    step = Step11ImageGeneration()
    ctx = ExecutionContext(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        step_id="step11_generate_images",
        attempt=1,
        started_at=datetime.now(),
        timeout_seconds=3600,
        config=args.get("config", {}),
    )

    # Load step10 data for context
    step10_data = await load_step_data(step.store, args["tenant_id"], args["run_id"], "step10") or {}

    keyword = step10_data.get("keyword", "")
    articles_data = step10_data.get("articles", [])

    # Backward compatibility: single-article output
    if not articles_data and step10_data.get("markdown_content"):
        articles_data = [
            {
                "article_number": 1,
                "title": step10_data.get("article_title", keyword),
                "content": step10_data.get("markdown_content", ""),
                "html_content": step10_data.get("html_content", ""),
            }
        ]

    articles_by_number = {int(article.get("article_number", 1)): article for article in articles_data if article}
    default_article_title = step10_data.get("article_title", keyword)

    positions = args.get("positions", [])
    instructions = args.get("instructions", [])

    # Build instruction map (index -> instruction)
    instruction_map = {inst["index"]: inst.get("instruction", "") for inst in instructions}

    generated_images: list[dict[str, Any]] = []
    warnings: list[str] = []

    article_image_indices: dict[int, int] = {}

    for i, pos_data in enumerate(positions):
        position = ImageInsertionPosition(**pos_data) if isinstance(pos_data, dict) else pos_data

        article_number = position.article_number or (pos_data.get("article_number") if isinstance(pos_data, dict) else None) or 1
        try:
            article_number = int(article_number)
        except (TypeError, ValueError):
            article_number = 1
        position.article_number = article_number
        article_data = articles_by_number.get(article_number)
        article_title = article_data.get("title", default_article_title) if article_data else default_article_title
        article_image_index = article_image_indices.get(article_number, 0)
        article_image_indices[article_number] = article_image_index + 1

        activity.logger.info(f"Generating image {i + 1}/{len(positions)}: article {article_number} {position.section_title}")

        user_instruction = instruction_map.get(i, "")

        try:
            # Create image prompt with user instruction
            image_prompt = await step._create_image_prompt_with_instruction(
                position=position,
                article_title=article_title,
                keyword=keyword,
                user_instruction=user_instruction,
            )

            # Generate image
            image_result = await step._generate_image(
                prompt=image_prompt,
                position=position,
            )

            if image_result:
                # Save to storage
                image_path = await step._save_image_to_storage_with_article(
                    ctx=ctx,
                    image_data=image_result["image_data"],
                    article_number=article_number,
                    image_index=article_image_index,
                )

                generated_image = {
                    "index": i,
                    "position": position.model_dump(),
                    "user_instruction": user_instruction,
                    "generated_prompt": image_prompt,
                    "image_path": image_path,
                    "image_digest": image_result.get("digest", ""),
                    "image_base64": image_result.get("base64", ""),
                    "alt_text": image_result.get("alt_text", position.description),
                    "mime_type": "image/png",
                    "file_size": len(image_result["image_data"]),
                    "retry_count": 0,
                    "accepted": False,  # User must accept
                    "article_number": article_number,
                }
                generated_images.append(generated_image)
            else:
                warnings.append(f"image_{i + 1}_generation_failed")

        except Exception as e:
            activity.logger.error(f"Failed to generate image {i + 1}: {e}")
            warnings.append(f"image_{i + 1}_error: {str(e)}")

    # Save intermediate result
    await save_step_data(
        step.store,
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        step="step11",
        data={"generated_images": generated_images, "warnings": warnings},
        filename="images.json",
    )

    return {
        "images": generated_images,
        "warnings": warnings,
    }


@activity.defn(name="step11_retry_image")
async def step11_retry_image(args: dict[str, Any]) -> dict[str, Any]:
    """Retry generating a single image with new instruction.

    Phase 11D (retry): Regenerate one image based on user feedback.

    Args:
        args: Activity arguments with:
            - tenant_id: Tenant identifier
            - run_id: Run identifier
            - config: Configuration
            - image_index: Index of image to retry
            - position: Position data for this image
            - instruction: New instruction from user
            - original_instruction: Original instruction for reference

    Returns:
        dict with success status and new image data
    """
    step = Step11ImageGeneration()
    ctx = ExecutionContext(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        step_id="step11_retry_image",
        attempt=1,
        started_at=datetime.now(),
        timeout_seconds=3600,
        config=args.get("config", {}),
    )

    # Load step10 data for context
    step10_data = await load_step_data(step.store, args["tenant_id"], args["run_id"], "step10") or {}

    keyword = step10_data.get("keyword", "")
    articles_data = step10_data.get("articles", [])

    # Backward compatibility: single-article output
    if not articles_data and step10_data.get("markdown_content"):
        articles_data = [
            {
                "article_number": 1,
                "title": step10_data.get("article_title", keyword),
                "content": step10_data.get("markdown_content", ""),
                "html_content": step10_data.get("html_content", ""),
            }
        ]

    articles_by_number = {int(article.get("article_number", 1)): article for article in articles_data if article}
    default_article_title = step10_data.get("article_title", keyword)

    image_index = args.get("image_index", 0)
    pos_data = args.get("position", {})
    position = ImageInsertionPosition(**pos_data) if isinstance(pos_data, dict) else pos_data
    article_number = position.article_number or (pos_data.get("article_number") if isinstance(pos_data, dict) else None) or 1
    try:
        article_number = int(article_number)
    except (TypeError, ValueError):
        article_number = 1
    position.article_number = article_number
    article_data = articles_by_number.get(article_number)
    article_title = article_data.get("title", default_article_title) if article_data else default_article_title

    retry_instruction = args.get("instruction", "")
    original_instruction = args.get("original_instruction", "")

    # Combine original and retry instructions
    combined_instruction = original_instruction
    if retry_instruction:
        combined_instruction = f"{original_instruction}\n\n追加の指示: {retry_instruction}"

    activity.logger.info(f"Step11: Retrying image {image_index + 1} for {position.section_title}")

    try:
        # Create image prompt with combined instruction
        image_prompt = await step._create_image_prompt_with_instruction(
            position=position,
            article_title=article_title,
            keyword=keyword,
            user_instruction=combined_instruction,
        )

        # Generate image
        image_result = await step._generate_image(
            prompt=image_prompt,
            position=position,
        )

        if image_result:
            # Save to storage (overwrite)
            image_path = await step._save_image_to_storage_with_article(
                ctx=ctx,
                image_data=image_result["image_data"],
                article_number=article_number,
                image_index=image_index,
            )

            return {
                "success": True,
                "image": {
                    "index": image_index,
                    "position": position.model_dump(),
                    "user_instruction": combined_instruction,
                    "generated_prompt": image_prompt,
                    "image_path": image_path,
                    "image_digest": image_result.get("digest", ""),
                    "image_base64": image_result.get("base64", ""),
                    "alt_text": image_result.get("alt_text", position.description),
                    "mime_type": "image/png",
                    "file_size": len(image_result["image_data"]),
                    "accepted": False,
                    "article_number": article_number,
                },
            }

    except Exception as e:
        activity.logger.error(f"Failed to retry image {image_index + 1}: {e}")
        return {
            "success": False,
            "error": str(e),
        }

    return {"success": False, "error": "Image generation returned no result"}


@activity.defn(name="step11_insert_images")
async def step11_insert_images(args: dict[str, Any]) -> dict[str, Any]:
    """Insert images into markdown and HTML content.

    Phase 11E: Deterministically insert images at specified positions.

    Args:
        args: Activity arguments with:
            - tenant_id: Tenant identifier
            - run_id: Run identifier
            - config: Configuration
            - images: List of generated images
            - positions: List of positions

    Returns:
        dict with final_markdown, final_html, and artifact_ref
    """
    step = Step11ImageGeneration()

    # Load step10 data
    step10_data = await load_step_data(step.store, args["tenant_id"], args["run_id"], "step10") or {}

    articles_data = step10_data.get("articles", [])

    # Backward compatibility: single-article output
    if not articles_data and step10_data.get("markdown_content"):
        articles_data = [
            {
                "article_number": 1,
                "title": step10_data.get("article_title", ""),
                "content": step10_data.get("markdown_content", ""),
                "html_content": step10_data.get("html_content", ""),
            }
        ]

    main_article = None
    for article in articles_data:
        if article.get("article_number") == 1:
            main_article = article
            break
    if not main_article and articles_data:
        main_article = articles_data[0]

    markdown_content = ""
    html_content = ""
    main_article_number = 1
    if main_article:
        markdown_content = main_article.get("content", main_article.get("markdown_content", ""))
        html_content = main_article.get("html_content", "")
        main_article_number = main_article.get("article_number", 1)

    images_data = args.get("images", [])
    # Note: positions_data is available in args but extracted from images_data below

    # Convert to model objects
    generated_images = []
    for img_data in images_data:
        # Create GeneratedImage from dict
        pos_data = img_data.get("position", {})
        position = ImageInsertionPosition(**pos_data) if isinstance(pos_data, dict) else pos_data

        article_number = img_data.get("article_number") or pos_data.get("article_number")
        if article_number is not None:
            try:
                article_number = int(article_number)
            except (TypeError, ValueError):
                article_number = None
        if article_number is not None:
            position.article_number = article_number

        generated_images.append(
            GeneratedImage(
                request=ImageGenerationRequest(
                    position=position,
                    user_instruction=img_data.get("user_instruction", ""),
                    generated_prompt=img_data.get("generated_prompt", ""),
                    alt_text=img_data.get("alt_text", ""),
                ),
                image_path=img_data.get("image_path", ""),
                image_digest=img_data.get("image_digest", ""),
                image_base64=img_data.get("image_base64", ""),
                mime_type=img_data.get("mime_type", "image/png"),
                file_size=img_data.get("file_size", 0),
                retry_count=img_data.get("retry_count", 0),
                accepted=True,  # All images at this point are accepted
                article_number=article_number,
            )
        )

    # Insert images into markdown and HTML
    article_images = [img for img in generated_images if img.article_number in (None, main_article_number)]
    final_markdown = step._insert_images_to_markdown(markdown_content, article_images)
    final_html = step._insert_images_to_html(html_content, article_images)

    # Save preview HTML
    preview_path = f"tenants/{args['tenant_id']}/runs/{args['run_id']}/step11/preview.html"
    if final_html:
        await step.store.put(
            content=final_html.encode("utf-8"),
            path=preview_path,
            content_type="text/html",
        )

    # Create output
    output = Step11Output(
        step="step11",
        enabled=True,
        image_count=len(generated_images),
        images=generated_images,
        markdown_with_images=final_markdown,
        html_with_images=final_html,
        model="gemini-2.5-flash-image",
        usage={},
    )

    # Save final output
    output_data = output.model_dump()
    output_path = step.store.build_path(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        step="step11",
    )
    await save_step_data(
        step.store,
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        step="step11",
        data=output_data,
    )

    return {
        "final_markdown": final_markdown,
        "final_html": final_html,
        "preview_path": preview_path,
        "artifact_ref": {
            "path": output_path,
            "digest": hashlib.sha256(str(output_data).encode()).hexdigest()[:16],
        },
    }
