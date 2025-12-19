#!/usr/bin/env python
"""Step11 画像生成の単独テストスクリプト.

Usage:
    # 分析のみ（画像生成なし）
    GEMINI_API_KEY=xxx uv run python scripts/test_step11.py analysis

    # フル実行（画像生成含む）
    GEMINI_API_KEY=xxx uv run python scripts/test_step11.py full

    # Step10の出力を使用（storage経由）
    GEMINI_API_KEY=xxx uv run python scripts/test_step11.py step10
"""

import asyncio
import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from apps.api.core.context import ExecutionContext
from apps.api.core.state import GraphState
from apps.worker.activities.step11 import Step11ImageGeneration


async def test_with_test_json():
    """test.jsonを使用したテスト."""
    print("=" * 60)
    print("Step11テスト: test.jsonを使用")
    print("=" * 60)

    # test.jsonを読み込み
    test_json_path = project_root / "test.json"
    if not test_json_path.exists():
        print(f"Error: {test_json_path} not found")
        return

    with open(test_json_path, "r", encoding="utf-8") as f:
        article_data = json.load(f)

    print(f"記事タイトル: {article_data.get('article_title', 'N/A')}")
    print(f"キーワード: {article_data.get('keyword', 'N/A')}")

    # Step11 Activityを初期化
    step11 = Step11ImageGeneration()

    # 挿入位置を分析
    print("\n挿入位置を分析中...")
    position_result = await step11._analyze_positions(
        markdown_content=article_data.get("markdown_content", ""),
        article_title=article_data.get("article_title", ""),
        keyword=article_data.get("keyword", ""),
        image_count=3,
        position_request="",
    )

    print("\n" + "=" * 40)
    print("分析結果")
    print("=" * 40)
    print(f"サマリー: {position_result.analysis_summary[:200]}...")

    print("\n画像挿入ポイント:")
    for i, pos in enumerate(position_result.positions, 1):
        print(f"\n--- {i}. {pos.section_title} ---")
        print(f"  位置: セクション {pos.section_index} の {pos.position}")
        print(f"  説明: {pos.description[:100]}...")
        print(f"  元テキスト: {pos.source_text[:100]}...")

    return position_result


async def test_full_generation():
    """フル画像生成テスト."""
    print("\n" + "=" * 60)
    print("Step11テスト: フル画像生成")
    print("=" * 60)

    # test.jsonを読み込み
    test_json_path = project_root / "test.json"
    with open(test_json_path, "r", encoding="utf-8") as f:
        article_data = json.load(f)

    # Step11 Activityを初期化
    step11 = Step11ImageGeneration()

    # ExecutionContextを作成
    from datetime import datetime
    ctx = ExecutionContext(
        run_id="test-run-001",
        step_id="step11",
        attempt=1,
        tenant_id="test-tenant",
        started_at=datetime.now(),
        timeout_seconds=600,
        config={
            "step11_enabled": True,
            "step11_image_count": 3,
            "step11_position_request": "",
        },
    )

    # GraphStateを作成（step10データを含む）
    state = GraphState(
        run_id="test-run-001",
        tenant_id="test-tenant",
        current_step="step11",
        status="running",
        step_outputs={
            "step10": {
                "markdown_content": article_data.get("markdown_content", ""),
                "html_content": article_data.get("html_content", ""),
                "keyword": article_data.get("keyword", ""),
                "article_title": article_data.get("article_title", ""),
            }
        },
        validation_reports=[],
        errors=[],
        config={},
        metadata={},
    )

    # 挿入位置を分析
    print("\n1. 挿入位置を分析中...")
    position_result = await step11._analyze_positions(
        markdown_content=article_data.get("markdown_content", ""),
        article_title=article_data.get("article_title", ""),
        keyword=article_data.get("keyword", ""),
        image_count=3,
        position_request="",
    )

    print(f"  {len(position_result.positions)}箇所の挿入ポイントを特定")

    # 各位置に対して画像を生成
    print("\n2. 画像を生成中...")
    from apps.worker.activities.schemas.step11 import GeneratedImage, ImageGenerationRequest
    import base64
    import hashlib

    generated_images = []
    for i, pos in enumerate(position_result.positions):
        print(f"\n  [{i + 1}/{len(position_result.positions)}] {pos.section_title}")

        # プロンプト生成
        print("    プロンプトを作成中...")
        image_prompt = await step11._create_image_prompt(
            position=pos,
            article_title=article_data.get("article_title", ""),
            keyword=article_data.get("keyword", ""),
        )
        print(f"    プロンプト: {image_prompt[:80]}...")

        # 画像生成
        print("    画像を生成中...")
        image_result = await step11._generate_image(
            prompt=image_prompt,
            position=pos,
        )

        if image_result:
            print(f"    成功: {len(image_result['image_data'])} bytes")
            generated_image = GeneratedImage(
                request=ImageGenerationRequest(
                    position=pos,
                    generated_prompt=image_prompt,
                    alt_text=image_result.get("alt_text", pos.description),
                ),
                image_path=f"test/images/image_{i + 1}.png",
                image_digest=image_result.get("digest", ""),
                image_base64=image_result.get("base64", ""),
                mime_type="image/png",
                file_size=len(image_result["image_data"]),
                accepted=True,
            )
            generated_images.append(generated_image)

            # 画像を保存
            output_dir = project_root / "generated_images" / "step11"
            output_dir.mkdir(parents=True, exist_ok=True)
            img_path = output_dir / f"image_{i + 1}.png"
            with open(img_path, "wb") as f:
                f.write(image_result["image_data"])
            print(f"    保存: {img_path}")
        else:
            print("    失敗: 画像を生成できませんでした")

    # 画像をMarkdown/HTMLに挿入
    print("\n3. 画像を挿入中...")
    final_markdown = step11._insert_images_to_markdown(
        article_data.get("markdown_content", ""),
        generated_images,
    )
    final_html = step11._insert_images_to_html(
        article_data.get("html_content", ""),
        generated_images,
    )

    # 結果を保存
    output_dir = project_root / "generated_images" / "step11"
    with open(output_dir / "final_article.md", "w", encoding="utf-8") as f:
        f.write(final_markdown)
    with open(output_dir / "final_article.html", "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"\n結果を保存しました: {output_dir}")
    print(f"  - final_article.md")
    print(f"  - final_article.html")
    print(f"  - image_1.png ~ image_{len(generated_images)}.png")

    return {
        "image_count": len(generated_images),
        "positions": position_result.positions,
    }


async def main():
    """メイン処理."""
    import os

    # APIキーの確認
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable is not set")
        sys.exit(1)

    # コマンドライン引数でテストモードを選択
    mode = sys.argv[1] if len(sys.argv) > 1 else "analysis"

    if mode == "analysis":
        await test_with_test_json()
    elif mode == "full":
        await test_full_generation()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python scripts/test_step11.py [analysis|full]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
