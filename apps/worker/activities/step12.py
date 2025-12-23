"""Step 12: WordPress HTML Generation Activity.

最終記事と画像提案を元にWordPress用HTMLを生成する工程。
4記事分のHTMLをGutenbergブロック形式で出力する。
"""

import html
import re
from datetime import datetime
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.state import GraphState
from apps.api.llm import AnthropicClient
from apps.worker.activities.schemas.step12 import (
    ArticleImage,
    ArticleMetadata,
    CommonAssets,
    GenerationMetadata,
    Step12Output,
    WordPressArticle,
)

from .base import BaseActivity, load_step_data


class Step12WordPressHtmlGeneration(BaseActivity):
    """Activity for WordPress HTML generation.

    Step10の4記事とStep11の画像情報を元に、
    WordPress Gutenbergブロック形式のHTMLを生成する。
    """

    def __init__(self) -> None:
        """Initialize with helpers."""
        super().__init__()
        self._anthropic_client: AnthropicClient | None = None

    @property
    def step_id(self) -> str:
        return "step12"

    def _get_anthropic_client(self) -> AnthropicClient:
        """AnthropicClientを取得（遅延初期化）."""
        if self._anthropic_client is None:
            self._anthropic_client = AnthropicClient()
        return self._anthropic_client

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute WordPress HTML generation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with step12 output
        """
        warnings: list[str] = []
        total_tokens = 0

        # 前工程のデータを読み込み
        step0_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step0") or {}
        # step6_5は将来的に使用予定（構成情報の参照）
        _ = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step6_5") or {}
        step10_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step10") or {}
        step11_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step11") or {}

        keyword = step0_data.get("keyword", "")
        if not keyword:
            keyword = step10_data.get("keyword", "")

        # Step10の記事を取得
        articles_data = step10_data.get("articles", [])
        if not articles_data:
            # 後方互換性: 単一記事の場合
            if step10_data.get("markdown_content"):
                articles_data = [
                    {
                        "article_number": 1,
                        "title": step10_data.get("article_title", ""),
                        "content": step10_data.get("markdown_content", ""),
                        "html_content": step10_data.get("html_content", ""),
                        "meta_description": step10_data.get("meta_description", ""),
                    }
                ]

        if not articles_data:
            warnings.append("step10_data_missing")
            return Step12Output(
                step=self.step_id,
                warnings=warnings,
            ).model_dump()

        # Step11の画像情報を取得
        images_data = step11_data.get("images", [])

        activity.logger.info(
            f"Step12: Generating WordPress HTML for {len(articles_data)} articles, keyword={keyword}, images={len(images_data)}"
        )

        # 各記事をWordPress用HTMLに変換
        wordpress_articles: list[WordPressArticle] = []

        for article_data in articles_data:
            article_number = article_data.get("article_number", 1)
            title = article_data.get("title", "")
            content = article_data.get("content", "")
            html_content = article_data.get("html_content", "")
            meta_description = article_data.get("meta_description", "")

            activity.logger.info(f"Processing article {article_number}: {title[:50]}...")

            # MarkdownからGutenbergブロック形式HTMLに変換
            gutenberg_html = await self._convert_to_gutenberg_blocks(
                markdown_content=content,
                html_content=html_content,
                images=images_data,
                article_number=article_number,
            )

            # 画像情報を抽出
            article_images = self._extract_article_images(images_data, article_number)

            # メタデータを生成
            word_count = len(content) if content else len(html_content)
            slug = self._generate_slug(title, keyword)

            wordpress_article = WordPressArticle(
                article_number=article_number,
                filename=f"article_{article_number}.html",
                html_content=gutenberg_html,
                gutenberg_blocks=gutenberg_html,
                metadata=ArticleMetadata(
                    title=title,
                    meta_description=meta_description,
                    focus_keyword=keyword,
                    word_count=word_count,
                    slug=slug,
                    categories=[],
                    tags=[],
                ),
                images=article_images,
            )
            wordpress_articles.append(wordpress_article)

            # 個別記事をStorageに保存
            article_path = f"tenants/{ctx.tenant_id}/runs/{ctx.run_id}/{self.step_id}/article_{article_number}.html"
            await self.store.put(
                content=gutenberg_html.encode("utf-8"),
                path=article_path,
                content_type="text/html",
            )

        # 共通アセット情報
        common_assets = CommonAssets()

        # 生成メタデータ
        total_images = sum(len(a.images) for a in wordpress_articles)
        generation_metadata = GenerationMetadata(
            generated_at=datetime.now(),
            model="claude-3-5-sonnet",
            wordpress_version_target="6.0+",
            total_articles=len(wordpress_articles),
            total_images=total_images,
        )

        # 出力を構築
        output = Step12Output(
            step=self.step_id,
            articles=wordpress_articles,
            common_assets=common_assets,
            generation_metadata=generation_metadata,
            model="claude-3-5-sonnet",
            usage={"total_tokens": total_tokens},
            warnings=warnings,
        )

        return output.model_dump()

    async def _convert_to_gutenberg_blocks(
        self,
        markdown_content: str,
        html_content: str,
        images: list[dict[str, Any]],
        article_number: int,
    ) -> str:
        """MarkdownをWordPress Gutenbergブロック形式HTMLに変換.

        Args:
            markdown_content: Markdownコンテンツ
            html_content: HTMLコンテンツ（フォールバック用）
            images: 画像情報リスト
            article_number: 記事番号

        Returns:
            Gutenbergブロック形式HTML
        """
        # HTMLがあればそれをベースに、なければMarkdownを変換
        source_content = html_content if html_content else self._markdown_to_html(markdown_content)

        # Gutenbergブロック形式に変換
        gutenberg_html = self._wrap_in_gutenberg_blocks(source_content)

        # 画像を挿入
        gutenberg_html = self._insert_images_to_gutenberg(gutenberg_html, images)

        return gutenberg_html

    def _markdown_to_html(self, markdown_content: str) -> str:
        """MarkdownをHTMLに変換（簡易実装）."""
        html = markdown_content

        # 見出し変換
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # 太字・イタリック
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

        # リンク
        html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)

        # リスト
        html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
        html = re.sub(r"(<li>.*</li>\n)+", r"<ul>\g<0></ul>", html)

        # 段落
        paragraphs = html.split("\n\n")
        processed = []
        for p in paragraphs:
            p = p.strip()
            if p and not p.startswith("<"):
                p = f"<p>{p}</p>"
            processed.append(p)
        html = "\n".join(processed)

        return html

    def _wrap_in_gutenberg_blocks(self, html_content: str) -> str:
        """HTMLをGutenbergブロック形式でラップ.

        WordPress Gutenbergエディタで認識される形式に変換。
        """
        lines = html_content.split("\n")
        gutenberg_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 見出しブロック
            if line.startswith("<h1"):
                gutenberg_lines.append('<!-- wp:heading {"level":1} -->')
                gutenberg_lines.append(line)
                gutenberg_lines.append("<!-- /wp:heading -->")
            elif line.startswith("<h2"):
                gutenberg_lines.append("<!-- wp:heading -->")
                gutenberg_lines.append(line)
                gutenberg_lines.append("<!-- /wp:heading -->")
            elif line.startswith("<h3"):
                gutenberg_lines.append('<!-- wp:heading {"level":3} -->')
                gutenberg_lines.append(line)
                gutenberg_lines.append("<!-- /wp:heading -->")
            # 段落ブロック
            elif line.startswith("<p"):
                gutenberg_lines.append("<!-- wp:paragraph -->")
                gutenberg_lines.append(line)
                gutenberg_lines.append("<!-- /wp:paragraph -->")
            # リストブロック
            elif line.startswith("<ul"):
                gutenberg_lines.append("<!-- wp:list -->")
                gutenberg_lines.append(line)
                gutenberg_lines.append("<!-- /wp:list -->")
            elif line.startswith("<ol"):
                gutenberg_lines.append('<!-- wp:list {"ordered":true} -->')
                gutenberg_lines.append(line)
                gutenberg_lines.append("<!-- /wp:list -->")
            # 引用ブロック
            elif line.startswith("<blockquote"):
                gutenberg_lines.append("<!-- wp:quote -->")
                gutenberg_lines.append(line)
                gutenberg_lines.append("<!-- /wp:quote -->")
            # 画像ブロック
            elif line.startswith("<img") or line.startswith("<figure"):
                gutenberg_lines.append("<!-- wp:image -->")
                gutenberg_lines.append(f'<figure class="wp-block-image">{line}</figure>')
                gutenberg_lines.append("<!-- /wp:image -->")
            else:
                # その他はそのまま追加
                gutenberg_lines.append(line)

        return "\n".join(gutenberg_lines)

    def _insert_images_to_gutenberg(
        self,
        html_content: str,
        images: list[dict[str, Any]],
    ) -> str:
        """画像をGutenbergブロック形式で挿入.

        Args:
            html_content: HTML コンテンツ
            images: 画像情報リスト

        Returns:
            画像挿入済みHTML
        """
        if not images:
            return html_content

        for img_data in images:
            position_data = img_data.get("position", {})
            section_title = position_data.get("section_title", "") if isinstance(position_data, dict) else ""
            alt_text = img_data.get("alt_text", "")
            image_base64 = img_data.get("image_base64", "")
            image_path = img_data.get("image_path", "")

            if not image_base64 and not image_path:
                continue

            # 画像ソースを決定
            if image_base64:
                src = f"data:image/png;base64,{image_base64}"
            else:
                src = image_path

            # XSS対策: HTMLエスケープを適用
            src_escaped = html.escape(src, quote=True)
            alt_escaped = html.escape(alt_text, quote=True)

            # Gutenberg画像ブロックを作成
            figure_html = (
                f'<figure class="wp-block-image size-large">'
                f'<img src="{src_escaped}" alt="{alt_escaped}"/>'
                f'<figcaption class="wp-element-caption">{alt_escaped}</figcaption>'
                f"</figure>"
            )
            image_block = f'<!-- wp:image {{"sizeSlug":"large"}} -->\n{figure_html}\n<!-- /wp:image -->'

            # セクションタイトルの後に挿入
            if section_title:
                # h2またはh3タグを探して挿入
                patterns = [
                    ("<!-- /wp:heading -->\n", f"<h2>{section_title}</h2>"),
                    ("<!-- /wp:heading -->\n", f"<h3>{section_title}</h3>"),
                ]
                for end_tag, _ in patterns:
                    # セクションの見出し終了タグの後に挿入
                    if section_title in html_content:
                        # セクションを含む見出しブロックを探す
                        heading_pattern = rf"(<!-- wp:heading[^>]*-->.*?{re.escape(section_title)}.*?<!-- /wp:heading -->)"
                        match = re.search(heading_pattern, html_content, re.DOTALL)
                        if match:
                            insert_pos = match.end()
                            html_content = html_content[:insert_pos] + "\n" + image_block + html_content[insert_pos:]
                            break

        return html_content

    def _extract_article_images(
        self,
        images: list[dict[str, Any]],
        article_number: int,
    ) -> list[ArticleImage]:
        """記事に関連する画像を抽出.

        Note: 現状は全画像を各記事に適用。
        将来的には記事番号でフィルタリング可能。
        """
        article_images = []
        for i, img_data in enumerate(images):
            position_data = img_data.get("position", {})
            section_title = position_data.get("section_title", "") if isinstance(position_data, dict) else ""

            article_images.append(
                ArticleImage(
                    position=section_title,
                    alt_text=img_data.get("alt_text", ""),
                    suggested_filename=f"image_{article_number}_{i + 1}.png",
                    image_path=img_data.get("image_path", ""),
                    image_base64=img_data.get("image_base64", ""),
                )
            )
        return article_images

    def _generate_slug(self, title: str, keyword: str) -> str:
        """URLスラッグを生成.

        Args:
            title: 記事タイトル
            keyword: キーワード

        Returns:
            URLスラッグ
        """
        # タイトルからスラッグを生成
        slug = title.lower() if title else keyword.lower()

        # 日本語の場合はキーワードベースで
        if any(ord(c) > 127 for c in slug):
            # 簡易的なローマ字化（実際はより高度な変換が必要）
            slug = keyword.lower().replace(" ", "-")

        # 特殊文字を除去
        slug = re.sub(r"[^a-z0-9\-]", "", slug)
        slug = re.sub(r"-+", "-", slug)
        slug = slug.strip("-")

        return slug[:50]  # 最大50文字


@activity.defn(name="step12_wordpress_html_generation")
async def step12_wordpress_html_generation(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 12."""
    step = Step12WordPressHtmlGeneration()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args.get("config", {}),
    )
