"""記事画像生成サービス

記事データから適切な画像を生成し、埋め込むためのサービス。
Step9.5用（LangGraph統合前のスタンドアロン実装）。

処理フロー:
1. 記事を分析して適切な画像挿入ポイントを特定（3箇所程度）
2. 各ポイント用の画像生成プロンプトを作成
3. Gemini画像生成APIで画像を生成
4. 生成結果を返却
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from apps.api.llm import (
    GeminiClient,
    LLMCallMetadata,
    LLMRequestConfig,
    NanoBananaClient,
    ImageGenerationResult,
)

logger = logging.getLogger(__name__)


@dataclass
class ImageInsertionPoint:
    """画像挿入ポイント"""

    section_title: str  # 挿入先のセクションタイトル（h2/h3）
    section_index: int  # セクションのインデックス
    position: str  # "before" | "after" - セクションの前後どちらに挿入するか
    description: str  # なぜこの位置に画像が必要かの説明
    image_prompt: str  # 画像生成用プロンプト
    alt_text: str  # 画像のalt属性用テキスト


@dataclass
class GeneratedImage:
    """生成された画像"""

    insertion_point: ImageInsertionPoint
    image_data: bytes  # 画像バイナリ
    image_base64: str  # Base64エンコード済み
    mime_type: str = "image/png"


@dataclass
class ArticleImageGenerationResult:
    """記事画像生成結果"""

    article_title: str
    keyword: str
    images: list[GeneratedImage] = field(default_factory=list)
    analysis_summary: str = ""
    total_images: int = 0
    success: bool = True
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return {
            "article_title": self.article_title,
            "keyword": self.keyword,
            "total_images": self.total_images,
            "success": self.success,
            "error_message": self.error_message,
            "analysis_summary": self.analysis_summary,
            "images": [
                {
                    "section_title": img.insertion_point.section_title,
                    "section_index": img.insertion_point.section_index,
                    "position": img.insertion_point.position,
                    "description": img.insertion_point.description,
                    "alt_text": img.insertion_point.alt_text,
                    "image_prompt": img.insertion_point.image_prompt,
                    "mime_type": img.mime_type,
                    "image_base64": img.image_base64,
                }
                for img in self.images
            ],
        }


# 画像挿入ポイント分析用のJSONスキーマ
IMAGE_INSERTION_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis_summary": {
            "type": "string",
            "description": "記事全体の分析サマリー（どのような記事で、どのような画像が適切か）",
        },
        "insertion_points": {
            "type": "array",
            "description": "画像挿入ポイントのリスト（3箇所）",
            "items": {
                "type": "object",
                "properties": {
                    "section_title": {
                        "type": "string",
                        "description": "挿入先のセクションタイトル（h2またはh3の見出しテキスト）",
                    },
                    "section_index": {
                        "type": "integer",
                        "description": "セクションのインデックス（0始まり）",
                    },
                    "position": {
                        "type": "string",
                        "enum": ["before", "after"],
                        "description": "セクションの前後どちらに挿入するか",
                    },
                    "description": {
                        "type": "string",
                        "description": "なぜこの位置に画像が必要かの説明",
                    },
                    "image_prompt": {
                        "type": "string",
                        "description": "画像生成用の詳細なプロンプト（英語、具体的な描写）",
                    },
                    "alt_text": {
                        "type": "string",
                        "description": "画像のalt属性用テキスト（日本語、簡潔）",
                    },
                },
                "required": [
                    "section_title",
                    "section_index",
                    "position",
                    "description",
                    "image_prompt",
                    "alt_text",
                ],
            },
        },
    },
    "required": ["analysis_summary", "insertion_points"],
}


class ArticleImageGenerator:
    """記事画像生成サービス

    記事データを分析し、適切な位置に挿入する画像を生成する。
    """

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
        image_client: NanoBananaClient | None = None,
        target_image_count: int = 3,
    ):
        """初期化

        Args:
            gemini_client: テキスト分析用のGeminiクライアント
            image_client: 画像生成用のNanoBananaクライアント
            target_image_count: 生成する画像数（デフォルト3）
        """
        self._gemini_client = gemini_client or GeminiClient()
        self._image_client = image_client or NanoBananaClient()
        self._target_image_count = target_image_count

    async def generate_images_for_article(
        self,
        article_data: dict[str, Any],
        metadata: LLMCallMetadata | None = None,
    ) -> ArticleImageGenerationResult:
        """記事用の画像を生成

        Args:
            article_data: 記事データ（test.json形式）
            metadata: 追跡用メタデータ

        Returns:
            ArticleImageGenerationResult: 生成結果
        """
        article_title = article_data.get("article_title", "")
        keyword = article_data.get("keyword", "")
        markdown_content = article_data.get("markdown_content", "")

        if not markdown_content:
            return ArticleImageGenerationResult(
                article_title=article_title,
                keyword=keyword,
                success=False,
                error_message="記事コンテンツが空です",
            )

        logger.info(
            f"Starting image generation for article: {article_title}",
            extra={"keyword": keyword},
        )

        try:
            # 1. 記事を分析して画像挿入ポイントを特定
            insertion_points = await self._analyze_article(
                markdown_content=markdown_content,
                article_title=article_title,
                keyword=keyword,
                metadata=metadata,
            )

            if not insertion_points:
                return ArticleImageGenerationResult(
                    article_title=article_title,
                    keyword=keyword,
                    success=False,
                    error_message="画像挿入ポイントを特定できませんでした",
                )

            # 2. 各ポイント用の画像を生成
            generated_images = await self._generate_images(
                insertion_points=insertion_points["insertion_points"],
                metadata=metadata,
            )

            return ArticleImageGenerationResult(
                article_title=article_title,
                keyword=keyword,
                images=generated_images,
                analysis_summary=insertion_points.get("analysis_summary", ""),
                total_images=len(generated_images),
                success=True,
            )

        except Exception as e:
            logger.error(f"Failed to generate images: {e}", exc_info=True)
            return ArticleImageGenerationResult(
                article_title=article_title,
                keyword=keyword,
                success=False,
                error_message=str(e),
            )

    async def _analyze_article(
        self,
        markdown_content: str,
        article_title: str,
        keyword: str,
        metadata: LLMCallMetadata | None = None,
    ) -> dict[str, Any]:
        """記事を分析して画像挿入ポイントを特定

        Args:
            markdown_content: 記事のMarkdownコンテンツ
            article_title: 記事タイトル
            keyword: キーワード
            metadata: 追跡用メタデータ

        Returns:
            dict: 分析結果（insertion_points含む）
        """
        # セクション構造を抽出
        sections = self._extract_sections(markdown_content)
        sections_text = "\n".join(
            [f"[{i}] {s['level']}: {s['title']}" for i, s in enumerate(sections)]
        )

        system_prompt = f"""あなたはSEO記事の画像配置を最適化する専門家です。

以下の記事を分析し、読者の理解を助け、記事の価値を高めるための画像挿入ポイントを**正確に{self._target_image_count}箇所**特定してください。

## 画像挿入の基準

1. **概念の視覚化**: 抽象的な概念を図解で説明できる箇所
2. **プロセスの説明**: 手順やフローを視覚的に示せる箇所
3. **比較・対比**: 複数の要素を比較している箇所
4. **重要なポイント**: 読者が特に注目すべき重要な内容

## 画像プロンプトの作成ガイドライン

- 英語で記述（画像生成AIは英語プロンプトが最も効果的）
- 具体的で詳細な描写（色、構図、スタイルを明記）
- SEO記事に適した、プロフェッショナルでクリーンなデザイン
- 日本人読者向けのビジュアル（テキストは入れない方が良い）
- フラットデザイン、インフォグラフィック風、またはイラスト風のスタイルを推奨

## 出力形式

JSON形式で出力してください。insertion_pointsは必ず{self._target_image_count}個にしてください。
"""

        user_message = f"""# 記事情報

**タイトル**: {article_title}
**キーワード**: {keyword}

## セクション構造

{sections_text}

## 記事本文

{markdown_content[:8000]}

---

上記の記事を分析し、最適な画像挿入ポイントを{self._target_image_count}箇所特定してください。
"""

        config = LLMRequestConfig(
            temperature=0.3,
            max_tokens=4096,
        )

        result = await self._gemini_client.generate_json(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
            schema=IMAGE_INSERTION_SCHEMA,
            config=config,
            metadata=metadata,
        )

        logger.info(
            f"Article analysis completed: {len(result.get('insertion_points', []))} insertion points found"
        )

        return result

    async def _generate_images(
        self,
        insertion_points: list[dict[str, Any]],
        metadata: LLMCallMetadata | None = None,
    ) -> list[GeneratedImage]:
        """画像を生成

        Args:
            insertion_points: 画像挿入ポイントのリスト
            metadata: 追跡用メタデータ

        Returns:
            list[GeneratedImage]: 生成された画像リスト
        """
        generated_images: list[GeneratedImage] = []

        for point in insertion_points:
            try:
                # 画像生成プロンプトを拡張
                enhanced_prompt = self._enhance_image_prompt(point["image_prompt"])

                logger.info(
                    f"Generating image for section: {point['section_title']}",
                    extra={"prompt": enhanced_prompt[:100]},
                )

                # 画像生成
                result: ImageGenerationResult = await self._image_client.generate_image(
                    prompt=enhanced_prompt,
                    metadata=metadata,
                )

                if result.images:
                    insertion_point = ImageInsertionPoint(
                        section_title=point["section_title"],
                        section_index=point["section_index"],
                        position=point["position"],
                        description=point["description"],
                        image_prompt=point["image_prompt"],
                        alt_text=point["alt_text"],
                    )

                    generated_image = GeneratedImage(
                        insertion_point=insertion_point,
                        image_data=result.images[0],
                        image_base64=result.get_base64_images()[0],
                        mime_type="image/png",
                    )

                    generated_images.append(generated_image)
                    logger.info(f"Image generated successfully for: {point['section_title']}")
                else:
                    logger.warning(f"No image generated for: {point['section_title']}")

            except Exception as e:
                logger.error(
                    f"Failed to generate image for section '{point['section_title']}': {e}"
                )
                # 個別の画像生成失敗は続行（フォールバックではなく、スキップ）
                continue

        return generated_images

    def _extract_sections(self, markdown_content: str) -> list[dict[str, Any]]:
        """Markdownから見出し構造を抽出

        Args:
            markdown_content: Markdownコンテンツ

        Returns:
            list: セクション情報のリスト
        """
        sections = []
        # 見出しパターン（h1〜h3）
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

    def _enhance_image_prompt(self, base_prompt: str) -> str:
        """画像生成プロンプトを拡張

        Args:
            base_prompt: 基本プロンプト

        Returns:
            str: 拡張されたプロンプト
        """
        # プロンプトの品質向上のための追加指示
        style_suffix = """

Style: Clean, professional, modern flat design illustration.
Colors: Vibrant but balanced color palette, suitable for blog/web content.
Composition: Clear focal point, good use of negative space.
Quality: High resolution, crisp edges, suitable for web display.
No text or watermarks in the image."""

        return f"{base_prompt}{style_suffix}"


async def generate_article_images(
    article_json_path: str,
    output_dir: str | None = None,
) -> ArticleImageGenerationResult:
    """記事JSONから画像を生成するヘルパー関数

    Args:
        article_json_path: 記事JSONファイルのパス
        output_dir: 画像出力ディレクトリ（省略時は画像は保存しない）

    Returns:
        ArticleImageGenerationResult: 生成結果
    """
    import os
    from pathlib import Path

    # JSONを読み込み
    with open(article_json_path, "r", encoding="utf-8") as f:
        article_data = json.load(f)

    # 画像生成
    generator = ArticleImageGenerator()
    result = await generator.generate_images_for_article(article_data)

    # 出力ディレクトリが指定されていれば画像を保存
    if output_dir and result.success and result.images:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for i, img in enumerate(result.images):
            img_path = output_path / f"image_{i + 1}.png"
            with open(img_path, "wb") as f:
                f.write(img.image_data)
            logger.info(f"Saved image to: {img_path}")

    return result


# CLIエントリポイント
if __name__ == "__main__":
    import sys

    async def main():
        if len(sys.argv) < 2:
            print("Usage: python -m apps.api.services.article_image_generator <article.json> [output_dir]")
            sys.exit(1)

        article_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None

        result = await generate_article_images(article_path, output_dir)

        if result.success:
            print(f"Successfully generated {result.total_images} images")
            print(f"Analysis: {result.analysis_summary}")
            for img in result.images:
                print(f"  - {img.insertion_point.section_title}: {img.insertion_point.alt_text}")
        else:
            print(f"Failed: {result.error_message}")
            sys.exit(1)

    asyncio.run(main())
