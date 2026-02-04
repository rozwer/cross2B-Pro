"""Step 12: WordPress HTML Generation Activity.

最終記事と画像提案を元にWordPress用HTMLを生成する工程。
4記事分のHTMLをGutenbergブロック形式で出力する。
"""

import hashlib
import html
import json
import logging
import re
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
    StructuredDataBlocks,
    WordPressArticle,
    YoastSeoMetadata,
)

from .base import ActivityError, BaseActivity, load_step_data

logger = logging.getLogger(__name__)


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

            # 記事番号で画像をフィルタリング
            filtered_images = [
                img for img in images_data if img.get("article_number") is None or img.get("article_number") == article_number
            ]

            # MarkdownからGutenbergブロック形式HTMLに変換
            gutenberg_html = await self._convert_to_gutenberg_blocks(
                markdown_content=content,
                html_content=html_content,
                images=filtered_images,
                article_number=article_number,
            )

            # 画像情報を抽出
            article_images = self._extract_article_images(images_data, article_number)

            # メタデータを生成
            word_count = len(content) if content else len(html_content)
            slug = self._generate_slug(title, keyword)

            # blog.System 統合: Yoast SEO メタデータ生成
            yoast_metadata = self._generate_yoast_metadata(
                title=title,
                meta_description=meta_description,
                keyword=keyword,
                content=content or html_content,
            )

            # blog.System 統合: Gutenbergブロックタイプ収集
            block_types = self._collect_gutenberg_block_types(gutenberg_html)

            # blog.System 統合: 構造化データ生成
            # step8のFAQデータがあれば使用
            step8_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step8") or {}
            faq_data = step8_data.get("faqs", [])
            structured_data = self._generate_structured_data(
                title=title,
                meta_description=meta_description,
                keyword=keyword,
                content=content or html_content,
                article_number=article_number,
                faq_data=faq_data,
            )

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
                yoast_seo_metadata=yoast_metadata,
                gutenberg_block_types_used=block_types,
                structured_data_blocks=structured_data,
            )
            wordpress_articles.append(wordpress_article)

            # 個別記事をStorageに保存 (using build_path for consistency)
            article_path = self.store.build_path(ctx.tenant_id, ctx.run_id, self.step_id, f"article_{article_number}.html")
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
            generated_at=ctx.started_at,
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
            token_usage={"input": 0, "output": total_tokens},
            warnings=warnings,
        )

        output_path = self.store.build_path(ctx.tenant_id, ctx.run_id, self.step_id)
        output.output_path = output_path
        # Use mode="json" to ensure datetime objects are serialized to ISO strings
        output_data = output.model_dump(mode="json")
        output_data["output_digest"] = hashlib.sha256(json.dumps(output_data, ensure_ascii=False, indent=2).encode("utf-8")).hexdigest()[
            :16
        ]

        return output_data

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

        # HTML検証
        validation_result = self._validate_html(gutenberg_html)

        # エラーがある場合は失敗として扱う（フォールバック禁止原則）
        if validation_result["errors"]:
            raise ActivityError(f"HTML validation failed for article {article_number}: {validation_result['errors']}")

        # 警告はログのみ（処理は継続）
        if validation_result["warnings"]:
            logger.warning(f"HTML validation warnings for article {article_number}: {validation_result['warnings']}")

        return gutenberg_html

    def _validate_html(self, html_content: str) -> dict[str, Any]:
        """HTML5構文バリデーションを実行.

        Note:
            本実装はタグの整合性（開始・終了タグの対応）をチェックする基本的なバリデーションです。
            完全なW3C準拠バリデーションが必要な場合は、外部バリデータサービス（validator.w3.org）
            との連携が必要ですが、ローカル運用環境では外部依存を避けるため、
            タグ構造の整合性チェックに限定しています。

        Args:
            html_content: 検証するHTMLコンテンツ

        Returns:
            dict with is_valid, warnings, errors
        """
        warnings: list[str] = []
        errors: list[str] = []

        try:
            from html.parser import HTMLParser

            class HTMLValidator(HTMLParser):
                def __init__(self) -> None:
                    super().__init__()
                    self.tag_stack: list[str] = []
                    self.validation_errors: list[str] = []
                    self.validation_warnings: list[str] = []
                    # Self-closing tags that don't need closing
                    self.void_elements = {
                        "area",
                        "base",
                        "br",
                        "col",
                        "embed",
                        "hr",
                        "img",
                        "input",
                        "link",
                        "meta",
                        "param",
                        "source",
                        "track",
                        "wbr",
                    }

                def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                    if tag.lower() not in self.void_elements:
                        self.tag_stack.append(tag.lower())

                def handle_endtag(self, tag: str) -> None:
                    tag_lower = tag.lower()
                    if tag_lower in self.void_elements:
                        return
                    if self.tag_stack and self.tag_stack[-1] == tag_lower:
                        self.tag_stack.pop()
                    elif tag_lower in self.tag_stack:
                        self.validation_warnings.append(f"Unexpected closing tag: </{tag}>")
                    else:
                        self.validation_errors.append(f"Unmatched closing tag: </{tag}>")

                def get_result(self) -> tuple[list[str], list[str]]:
                    if self.tag_stack:
                        self.validation_warnings.append(f"Unclosed tags: {self.tag_stack}")
                    return self.validation_errors, self.validation_warnings

            validator = HTMLValidator()
            # WordPress Gutenberg comments are valid, strip them for validation
            clean_html = re.sub(r"<!--.*?-->", "", html_content, flags=re.DOTALL)
            validator.feed(clean_html)
            errors, warnings = validator.get_result()

        except Exception as e:
            warnings.append(f"HTML validation failed: {e}")

        is_valid = len(errors) == 0
        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
        }

    def _markdown_to_html(self, markdown_content: str) -> str:
        """MarkdownをHTMLに変換（P2: アンカーID付与対応）."""
        html = markdown_content

        # 見出しカウンター for アンカーID
        h2_counter = [0]  # Use list for nonlocal mutation
        h3_counter = [0]

        def add_h2_id(match: re.Match[str]) -> str:
            h2_counter[0] += 1
            h3_counter[0] = 0  # Reset h3 counter for each h2
            title = match.group(1)
            anchor_id = f"section-{h2_counter[0]}"
            return f'<h2 id="{anchor_id}">{title}</h2>'

        def add_h3_id(match: re.Match[str]) -> str:
            h3_counter[0] += 1
            title = match.group(1)
            anchor_id = f"section-{h2_counter[0]}-{h3_counter[0]}"
            return f'<h3 id="{anchor_id}">{title}</h3>'

        # 見出し変換（アンカーID付与）- 順序重要: h3を先に処理
        html = re.sub(r"^### (.+)$", add_h3_id, html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", add_h2_id, html, flags=re.MULTILINE)
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

    def _generate_toc_block(self, html_content: str) -> str:
        """目次（Table of Contents）ブロックを生成（P2）."""
        toc_items = []

        # H2/H3を抽出
        headings = re.findall(r'<h([23]) id="([^"]+)">([^<]+)</h\1>', html_content)
        for level, anchor_id, title in headings:
            indent = "  " if level == "3" else ""
            toc_items.append(f'{indent}<li><a href="#{anchor_id}">{title}</a></li>')

        if not toc_items:
            return ""

        toc_html = f"""<!-- wp:html -->
<nav class="toc" aria-label="目次">
<h2>目次</h2>
<ol>
{"".join(toc_items)}
</ol>
</nav>
<!-- /wp:html -->"""
        return toc_html

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

        article_numberでフィルタリングして、該当記事の画像のみ返す。
        article_numberが指定されていない画像は全記事に適用される。
        """
        article_images = []
        image_idx = 0
        for img_data in images:
            # article_numberでフィルタリング
            img_article_number = img_data.get("article_number")
            if img_article_number is not None and img_article_number != article_number:
                continue

            position_data = img_data.get("position", {})
            section_title = position_data.get("section_title", "") if isinstance(position_data, dict) else ""

            image_idx += 1
            article_images.append(
                ArticleImage(
                    position=section_title,
                    alt_text=img_data.get("alt_text", ""),
                    suggested_filename=f"image_{article_number}_{image_idx}.png",
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

    def _generate_yoast_metadata(
        self,
        title: str,
        meta_description: str,
        keyword: str,
        content: str,
    ) -> YoastSeoMetadata:
        """Yoast SEO メタデータを生成.

        Args:
            title: 記事タイトル
            meta_description: メタディスクリプション
            keyword: フォーカスキーワード
            content: 記事本文

        Returns:
            YoastSeoMetadata
        """
        # SEOタイトル生成（60文字以内推奨）
        seo_title = title[:60] if len(title) > 60 else title

        # メタディスクリプション調整（155文字以内推奨）
        adjusted_description = meta_description
        if len(meta_description) > 155:
            adjusted_description = meta_description[:152] + "..."

        # 可読性スコア算出（簡易実装）
        readability_score = self._calculate_readability_score(content)

        # SEOスコア算出（簡易実装）
        seo_score = self._calculate_seo_score(title, meta_description, keyword, content)

        return YoastSeoMetadata(
            focus_keyword=keyword,
            seo_title=seo_title,
            meta_description=adjusted_description,
            readability_score=readability_score,
            seo_score=seo_score,
        )

    def _calculate_readability_score(self, content: str) -> str:
        """可読性スコアを算出.

        簡易的な日本語可読性評価:
        - 段落の長さ
        - 文の長さ
        - 見出しの頻度

        Args:
            content: 記事本文

        Returns:
            スコア（good/ok/needs_improvement）
        """
        if not content:
            return "needs_improvement"

        # 文の数をカウント（句点で分割）
        sentences = re.split(r"[。！？]", content)
        sentences = [s for s in sentences if s.strip()]
        sentence_count = len(sentences)

        if sentence_count == 0:
            return "needs_improvement"

        # 平均文長を計算
        avg_sentence_length = len(content) / sentence_count

        # 見出しの数をカウント
        heading_count = len(re.findall(r"<h[1-6]>|^#{1,6}\s", content, re.MULTILINE))

        # スコア判定
        # - 平均文長が40-80文字程度が読みやすい
        # - 見出しが適度にある（1000文字に1個以上）
        content_length = len(content)
        expected_headings = max(1, content_length // 1000)

        if 30 <= avg_sentence_length <= 100 and heading_count >= expected_headings:
            return "good"
        elif 20 <= avg_sentence_length <= 150 and heading_count >= expected_headings // 2:
            return "ok"
        else:
            return "needs_improvement"

    def _calculate_seo_score(
        self,
        title: str,
        meta_description: str,
        keyword: str,
        content: str,
    ) -> str:
        """SEOスコアを算出.

        Yoast SEO風のチェック項目:
        - キーワードがタイトルに含まれるか
        - キーワードがメタディスクリプションに含まれるか
        - キーワードが本文に含まれるか（キーワード密度）
        - タイトルの長さ
        - メタディスクリプションの長さ

        Args:
            title: 記事タイトル
            meta_description: メタディスクリプション
            keyword: フォーカスキーワード
            content: 記事本文

        Returns:
            スコア（good/ok/needs_improvement）
        """
        if not keyword:
            return "needs_improvement"

        score_points = 0
        max_points = 5

        # 1. キーワードがタイトルに含まれるか
        if keyword.lower() in title.lower():
            score_points += 1

        # 2. キーワードがメタディスクリプションに含まれるか
        if keyword.lower() in meta_description.lower():
            score_points += 1

        # 3. キーワード密度（0.5-2.5%が理想）
        content_lower = content.lower()
        keyword_lower = keyword.lower()
        if content_lower:
            keyword_count = content_lower.count(keyword_lower)
            content_length = len(content_lower)
            keyword_density = (keyword_count * len(keyword_lower) / content_length) * 100 if content_length > 0 else 0
            if 0.5 <= keyword_density <= 2.5:
                score_points += 1

        # 4. タイトルの長さ（50-60文字が理想）
        if 30 <= len(title) <= 70:
            score_points += 1

        # 5. メタディスクリプションの長さ（120-155文字が理想）
        if 80 <= len(meta_description) <= 160:
            score_points += 1

        # スコア判定
        score_ratio = score_points / max_points
        if score_ratio >= 0.8:
            return "good"
        elif score_ratio >= 0.5:
            return "ok"
        else:
            return "needs_improvement"

    def _generate_structured_data(
        self,
        title: str,
        meta_description: str,
        keyword: str,
        content: str,
        article_number: int,
        faq_data: list[dict[str, Any]] | None = None,
        author_name: str | None = None,
        publisher_name: str | None = None,
        site_url: str | None = None,
        category: str | None = None,
    ) -> StructuredDataBlocks:
        """構造化データブロックを生成（E-E-A-T対応強化版）.

        Args:
            title: 記事タイトル
            meta_description: 記事説明
            keyword: キーワード
            content: 記事本文
            article_number: 記事番号
            faq_data: FAQ データ（あれば）
            author_name: 著者名（E-E-A-T用）
            publisher_name: 発行組織名
            site_url: サイトURL
            category: カテゴリ名（パンくず用）

        Returns:
            StructuredDataBlocks
        """
        from datetime import datetime

        now_iso = datetime.now().isoformat()

        # デフォルト値（実運用時はconfig/DBから取得推奨）
        author_name = author_name or "専門ライター"
        publisher_name = publisher_name or "記事発行元"
        site_url = site_url or "https://example.com"

        # BlogPosting JSON-LD (Article より詳細、E-E-A-T対応)
        article_schema = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": title,
            "description": meta_description,
            "keywords": keyword,
            "articleBody": content[:1000] + "..." if len(content) > 1000 else content,
            "datePublished": now_iso,
            "dateModified": now_iso,
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": f"{site_url}/articles/{article_number}",
            },
            "author": {
                "@type": "Person",
                "name": author_name,
                "url": f"{site_url}/authors/{author_name.replace(' ', '-').lower()}",
            },
            "publisher": {
                "@type": "Organization",
                "name": publisher_name,
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{site_url}/logo.png",
                },
            },
            "image": {
                "@type": "ImageObject",
                "url": f"{site_url}/images/article-{article_number}.jpg",
                "width": 1200,
                "height": 630,
            },
            "wordCount": len(content),
            "inLanguage": "ja-JP",
        }
        article_json = json.dumps(article_schema, ensure_ascii=False, indent=2)

        # FAQ JSON-LD（データがあれば）
        faq_json = None
        if faq_data:
            faq_schema = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": faq.get("question", ""),
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": faq.get("answer", ""),
                        },
                    }
                    for faq in faq_data
                    if faq.get("question") and faq.get("answer")
                ],
            }
            if faq_schema["mainEntity"]:
                faq_json = json.dumps(faq_schema, ensure_ascii=False, indent=2)

        # BreadcrumbList JSON-LD
        breadcrumb_schema = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "ホーム",
                    "item": site_url,
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": category or "記事",
                    "item": f"{site_url}/category/{(category or 'articles').replace(' ', '-').lower()}",
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": title,
                    "item": f"{site_url}/articles/{article_number}",
                },
            ],
        }
        breadcrumb_json = json.dumps(breadcrumb_schema, ensure_ascii=False, indent=2)

        return StructuredDataBlocks(
            article_schema=article_json,
            faq_schema=faq_json,
            breadcrumb_schema=breadcrumb_json,
        )

    def _collect_gutenberg_block_types(self, gutenberg_html: str) -> list[str]:
        """使用されているGutenbergブロックタイプを収集.

        Args:
            gutenberg_html: Gutenbergブロック形式HTML

        Returns:
            ブロックタイプ名のリスト（重複なし）
        """
        # <!-- wp:blocktype --> 形式のブロックを抽出
        pattern = r"<!-- wp:(\w+)"
        matches = re.findall(pattern, gutenberg_html)

        # 重複を除去して並び替え
        unique_types = sorted(set(matches))
        return unique_types


@activity.defn(name="step12_wordpress_html_generation")
async def step12_wordpress_html_generation(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 12."""
    step = Step12WordPressHtmlGeneration()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args.get("config", {}),
    )
