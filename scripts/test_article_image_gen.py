#!/usr/bin/env python
"""記事画像生成テストスクリプト

Usage:
    uv run python scripts/test_article_image_gen.py

環境変数:
    GEMINI_API_KEY: Gemini APIキー（必須）
"""

import asyncio
import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from apps.api.services.article_image_generator import (
    ArticleImageGenerator,
    generate_article_images,
)


async def test_article_analysis_only():
    """記事分析のみをテスト（画像生成なし）"""
    print("=" * 60)
    print("テスト1: 記事分析のみ")
    print("=" * 60)

    # テストデータを読み込み
    test_json_path = project_root / "test.json"
    if not test_json_path.exists():
        print(f"Error: {test_json_path} not found")
        return

    with open(test_json_path, "r", encoding="utf-8") as f:
        article_data = json.load(f)

    print(f"記事タイトル: {article_data.get('article_title', 'N/A')}")
    print(f"キーワード: {article_data.get('keyword', 'N/A')}")

    # ArticleImageGeneratorを初期化（分析のみ）
    from apps.api.llm import GeminiClient

    gemini_client = GeminiClient()

    generator = ArticleImageGenerator(
        gemini_client=gemini_client,
        image_client=None,  # 画像生成はスキップ
        target_image_count=3,
    )

    # 分析実行
    print("\n記事を分析中...")
    analysis_result = await generator._analyze_article(
        markdown_content=article_data.get("markdown_content", ""),
        article_title=article_data.get("article_title", ""),
        keyword=article_data.get("keyword", ""),
    )

    print("\n" + "=" * 40)
    print("分析結果")
    print("=" * 40)
    print(f"\nサマリー:\n{analysis_result.get('analysis_summary', 'N/A')}")

    print("\n画像挿入ポイント:")
    for i, point in enumerate(analysis_result.get("insertion_points", []), 1):
        print(f"\n--- {i}. {point.get('section_title', 'N/A')} ---")
        print(f"  位置: セクション {point.get('section_index', 'N/A')} の {point.get('position', 'N/A')}")
        print(f"  説明: {point.get('description', 'N/A')}")
        print(f"  プロンプト: {point.get('image_prompt', 'N/A')[:100]}...")
        print(f"  Alt: {point.get('alt_text', 'N/A')}")

    return analysis_result


async def test_full_generation():
    """画像生成を含むフルテスト"""
    print("\n" + "=" * 60)
    print("テスト2: 画像生成（フル）")
    print("=" * 60)

    test_json_path = project_root / "test.json"
    output_dir = project_root / "generated_images"

    print(f"入力: {test_json_path}")
    print(f"出力: {output_dir}")

    result = await generate_article_images(
        article_json_path=str(test_json_path),
        output_dir=str(output_dir),
    )

    if result.success:
        print(f"\n成功: {result.total_images}枚の画像を生成")
        print(f"サマリー: {result.analysis_summary}")
        for img in result.images:
            print(f"  - {img.insertion_point.section_title}")
            print(f"    Alt: {img.insertion_point.alt_text}")
            print(f"    サイズ: {len(img.image_data)} bytes")
    else:
        print(f"\n失敗: {result.error_message}")

    return result


async def main():
    """メイン処理"""
    import os

    # API キーの確認
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable is not set")
        print("Set it with: export GEMINI_API_KEY=your_api_key")
        sys.exit(1)

    # コマンドライン引数でテストモードを選択
    mode = sys.argv[1] if len(sys.argv) > 1 else "analysis"

    if mode == "analysis":
        # 分析のみ（画像生成なし）
        await test_article_analysis_only()
    elif mode == "full":
        # 画像生成を含むフルテスト
        await test_full_generation()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python scripts/test_article_image_gen.py [analysis|full]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
