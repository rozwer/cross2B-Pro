#!/usr/bin/env python3
"""Demo script to test each workflow step individually.

This script tests the LLM-based steps without requiring the full
Temporal/Tools infrastructure.
"""

import asyncio
import json
import os
import sys
from typing import Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_section(title: str, char: str = "=") -> None:
    """Print a section header."""
    print(f"\n{char * 60}")
    print(f" {title}")
    print(f"{char * 60}\n")


async def test_step2_csv_validation() -> dict[str, Any]:
    """Test Step 2: CSV Validation (no LLM required)."""
    print_section("Step 2: CSV Validation")

    from apps.api.validation.schemas import ValidationSeverity

    # Simulate step1 competitor data
    competitors = [
        {
            "url": "https://example.com/article1",
            "title": "SEO記事の書き方完全ガイド",
            "content": "SEO記事を書く際には、まずキーワード選定が重要です。" * 10,
        },
        {
            "url": "https://example.com/article2",
            "title": "2024年のSEOトレンド",
            "content": "最新のSEOトレンドについて解説します。" * 15,
        },
        {
            "url": "https://example.com/article3",
            "title": "",  # Empty title - should generate warning
            "content": "短い",  # Too short - should generate warning
        },
    ]

    # Validation logic (inline from step2)
    validated_records = []
    validation_issues = []
    required_fields = ["url", "title", "content"]

    for idx, competitor in enumerate(competitors):
        record_issues = []

        for field in required_fields:
            if field not in competitor or not competitor[field]:
                record_issues.append({
                    "field": field,
                    "issue": "missing_or_empty",
                    "severity": ValidationSeverity.ERROR.value,
                })

        content = competitor.get("content", "")
        if len(content) < 100:
            record_issues.append({
                "field": "content",
                "issue": "content_too_short",
                "severity": ValidationSeverity.WARNING.value,
                "value": len(content),
            })

        if record_issues:
            validation_issues.append({
                "index": idx,
                "url": competitor.get("url", "unknown"),
                "issues": record_issues,
            })
        else:
            validated_records.append(competitor)

    result = {
        "step": "step2",
        "is_valid": len(validated_records) > 0,
        "total_records": len(competitors),
        "valid_records": len(validated_records),
        "validation_issues": validation_issues,
    }

    print(f"✅ Total records: {result['total_records']}")
    print(f"✅ Valid records: {result['valid_records']}")
    print(f"⚠️  Issues found: {len(validation_issues)}")
    for issue in validation_issues:
        print(f"   - Record {issue['index']} ({issue['url']}): {len(issue['issues'])} issues")

    return result


async def test_step3a_query_analysis() -> dict[str, Any]:
    """Test Step 3A: Query Analysis using Gemini."""
    print_section("Step 3A: Query Analysis (Gemini)")

    from apps.api.llm import GeminiClient
    from apps.api.llm.schemas import LLMRequestConfig

    client = GeminiClient()
    keyword = "AI活用SEO記事作成"

    prompt = f"""以下のキーワードに関する検索クエリ分析を行ってください。

キーワード: {keyword}

以下の項目について分析してください：
1. 検索意図（情報収集、比較検討、購入意図など）
2. ターゲットペルソナ（年齢層、職業、課題）
3. 関連するサブクエリ（5つ）
4. コンテンツで解決すべき課題

JSON形式で回答してください。"""

    config = LLMRequestConfig(max_tokens=2000, temperature=0.7)
    response = await client.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a search query analysis expert.",
        config=config,
    )

    result = {
        "step": "step3a",
        "keyword": keyword,
        "query_analysis": response.content[:500] + "..." if len(response.content) > 500 else response.content,
        "model": response.model,
        "tokens": {
            "input": response.token_usage.input,
            "output": response.token_usage.output,
        },
    }

    print(f"✅ Model: {result['model']}")
    print(f"✅ Tokens: input={result['tokens']['input']}, output={result['tokens']['output']}")
    print(f"\n📝 Analysis preview:\n{result['query_analysis'][:400]}...")

    return result


async def test_step3b_cooccurrence() -> dict[str, Any]:
    """Test Step 3B: Co-occurrence Extraction using Gemini."""
    print_section("Step 3B: Co-occurrence Extraction (Gemini)")

    from apps.api.llm import GeminiClient
    from apps.api.llm.schemas import LLMRequestConfig

    client = GeminiClient()
    keyword = "AI活用SEO記事作成"

    # Simulated competitor content
    competitors = [
        {"title": "AIでSEO記事を自動生成する方法", "content_preview": "ChatGPTやGeminiを活用して、SEO最適化された記事を効率的に作成する手法について解説します。"},
        {"title": "2024年SEO記事の書き方ガイド", "content_preview": "検索エンジン最適化の最新トレンドと、AIツールを活用した効果的な記事作成のポイント。"},
    ]

    prompt = f"""以下のキーワードと競合記事から共起語・関連キーワードを抽出してください。

キーワード: {keyword}

競合記事:
{json.dumps(competitors, ensure_ascii=False, indent=2)}

以下を抽出してください：
1. 主要共起語（5-10個）
2. LSIキーワード（潜在意味キーワード）
3. 関連する専門用語
4. ユーザーが一緒に検索しそうな語句

JSON形式で回答してください。"""

    config = LLMRequestConfig(max_tokens=2000, temperature=0.5)
    response = await client.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a co-occurrence keyword analysis expert.",
        config=config,
    )

    result = {
        "step": "step3b",
        "keyword": keyword,
        "cooccurrence_analysis": response.content[:500] + "..." if len(response.content) > 500 else response.content,
        "model": response.model,
        "tokens": {
            "input": response.token_usage.input,
            "output": response.token_usage.output,
        },
    }

    print(f"✅ Model: {result['model']}")
    print(f"✅ Tokens: input={result['tokens']['input']}, output={result['tokens']['output']}")
    print(f"\n📝 Co-occurrence preview:\n{result['cooccurrence_analysis'][:400]}...")

    return result


async def test_step3c_competitor_analysis() -> dict[str, Any]:
    """Test Step 3C: Competitor Analysis using Gemini."""
    print_section("Step 3C: Competitor Analysis (Gemini)")

    from apps.api.llm import GeminiClient
    from apps.api.llm.schemas import LLMRequestConfig

    client = GeminiClient()
    keyword = "AI活用SEO記事作成"

    competitors = [
        {"url": "https://example.com/ai-seo-1", "title": "AIでSEO記事を作る", "content_length": 3500},
        {"url": "https://example.com/ai-seo-2", "title": "ChatGPT記事作成術", "content_length": 4200},
        {"url": "https://example.com/ai-seo-3", "title": "SEO記事自動化ガイド", "content_length": 2800},
    ]

    prompt = f"""以下のキーワードと競合記事を分析し、差別化戦略を提案してください。

キーワード: {keyword}

競合記事:
{json.dumps(competitors, ensure_ascii=False, indent=2)}

以下を分析してください：
1. 競合の強み・弱み
2. 差別化ポイント（3-5つ）
3. コンテンツギャップ（競合が扱っていないトピック）
4. 推奨コンテンツ戦略

JSON形式で回答してください。"""

    config = LLMRequestConfig(max_tokens=2000, temperature=0.7)
    response = await client.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a competitor analysis expert.",
        config=config,
    )

    result = {
        "step": "step3c",
        "keyword": keyword,
        "competitor_analysis": response.content[:500] + "..." if len(response.content) > 500 else response.content,
        "model": response.model,
        "tokens": {
            "input": response.token_usage.input,
            "output": response.token_usage.output,
        },
    }

    print(f"✅ Model: {result['model']}")
    print(f"✅ Tokens: input={result['tokens']['input']}, output={result['tokens']['output']}")
    print(f"\n📝 Competitor analysis preview:\n{result['competitor_analysis'][:400]}...")

    return result


async def test_step5_primary_sources() -> dict[str, Any]:
    """Test Step 5: Primary Source Collection (simulated)."""
    print_section("Step 5: Primary Source Collection (Simulated)")

    # Since we don't have actual SERP tools, simulate the output
    sources = [
        {
            "url": "https://research.google/blog/ai-content-quality",
            "title": "Google Research on AI Content Quality",
            "excerpt": "Latest research on how AI-generated content is evaluated...",
            "verified": True,
        },
        {
            "url": "https://searchengineland.com/seo-best-practices-2024",
            "title": "SEO Best Practices 2024",
            "excerpt": "Comprehensive guide to SEO optimization techniques...",
            "verified": True,
        },
    ]

    result = {
        "step": "step5",
        "keyword": "AI活用SEO記事作成",
        "sources": sources,
        "search_queries": ["AI SEO research statistics", "SEO content quality studies"],
        "total_collected": len(sources),
        "total_verified": len([s for s in sources if s.get("verified")]),
    }

    print(f"✅ Sources collected: {result['total_collected']}")
    print(f"✅ Sources verified: {result['total_verified']}")
    for s in sources:
        print(f"   - {s['title']}")

    return result


async def test_step6_enhanced_outline() -> dict[str, Any]:
    """Test Step 6: Enhanced Outline using Anthropic."""
    print_section("Step 6: Enhanced Outline (Anthropic)")

    from apps.api.llm import AnthropicClient
    from apps.api.llm.schemas import LLMRequestConfig

    client = AnthropicClient()
    keyword = "AI活用SEO記事作成"

    # Simulated step4 outline
    basic_outline = """
1. AI×SEO記事作成の概要
2. AIツールの選び方
3. プロンプト設計のコツ
4. SEO最適化のポイント
5. 品質管理の方法
6. 事例紹介
7. まとめ
"""

    sources = [
        {"title": "Google Research on AI", "url": "https://research.google"},
        {"title": "SEO Best Practices", "url": "https://searchengineland.com"},
    ]

    prompt = f"""以下の基本アウトラインを、一次情報を組み込んで強化してください。

キーワード: {keyword}

基本アウトライン:
{basic_outline}

参照可能な一次情報:
{json.dumps(sources, ensure_ascii=False, indent=2)}

以下の点を強化してください：
1. 各セクションに具体的なサブセクションを追加
2. データや統計を引用するポイントを明示
3. 読者の疑問に答える構成
4. E-E-A-T要素の組み込み

強化されたアウトラインを返してください。"""

    config = LLMRequestConfig(max_tokens=3000, temperature=0.6)
    response = await client.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are an SEO content outline specialist.",
        config=config,
    )

    result = {
        "step": "step6",
        "keyword": keyword,
        "enhanced_outline": response.content[:800] + "..." if len(response.content) > 800 else response.content,
        "model": response.model,
        "tokens": {
            "input": response.token_usage.input,
            "output": response.token_usage.output,
        },
    }

    print(f"✅ Model: {result['model']}")
    print(f"✅ Tokens: input={result['tokens']['input']}, output={result['tokens']['output']}")
    print(f"\n📝 Enhanced outline preview:\n{result['enhanced_outline'][:600]}...")

    return result


async def test_step6_5_integration() -> dict[str, Any]:
    """Test Step 6.5: Integration Package using Anthropic."""
    print_section("Step 6.5: Integration Package (Anthropic)")

    from apps.api.llm import AnthropicClient
    from apps.api.llm.schemas import LLMRequestConfig

    client = AnthropicClient()
    keyword = "AI活用SEO記事作成"

    prompt = f"""以下の分析結果を統合し、記事執筆用パッケージを作成してください。

キーワード: {keyword}

キーワード分析: SEO記事作成にAIを活用する方法についての情報収集目的
クエリ分析: マーケター、ブロガー、コンテンツ制作者向け
共起キーワード: ChatGPT, Gemini, プロンプト, 自動生成, 品質管理
競合差別化: 実践的なプロンプト例の提供

以下の形式でJSON出力してください：
{{
    "integration_package": "統合された記事作成ガイド",
    "outline_summary": "アウトラインの要約",
    "section_count": セクション数,
    "total_sources": 参照ソース数
}}"""

    config = LLMRequestConfig(max_tokens=2000, temperature=0.5)
    response = await client.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are an SEO content integration specialist.",
        config=config,
    )

    # Try to parse JSON
    try:
        parsed = json.loads(response.content)
        integration_package = parsed.get("integration_package", "")
        section_count = parsed.get("section_count", 0)
    except json.JSONDecodeError:
        integration_package = response.content[:500]
        section_count = 7

    result = {
        "step": "step6_5",
        "keyword": keyword,
        "integration_package": integration_package[:300] + "..." if len(str(integration_package)) > 300 else integration_package,
        "section_count": section_count,
        "model": response.model,
        "tokens": {
            "input": response.token_usage.input,
            "output": response.token_usage.output,
        },
    }

    print(f"✅ Model: {result['model']}")
    print(f"✅ Sections: {result['section_count']}")
    print(f"✅ Tokens: input={result['tokens']['input']}, output={result['tokens']['output']}")

    return result


async def test_step7b_brush_up() -> dict[str, Any]:
    """Test Step 7B: Brush Up using Gemini."""
    print_section("Step 7B: Brush Up/Polish (Gemini)")

    from apps.api.llm import GeminiClient
    from apps.api.llm.schemas import LLMRequestConfig

    client = GeminiClient()
    keyword = "AI活用SEO記事作成"

    # Simulated draft from step7a
    draft = """
# AI活用SEO記事作成ガイド

## はじめに
AIを使ってSEO記事を作成する方法を説明します。最近のAI技術の進歩により、効率的に記事を作成できるようになりました。

## AIツールの選び方
ChatGPTやGeminiなど、様々なAIツールがあります。目的に応じて選択することが重要です。

## プロンプトの書き方
良いプロンプトを書くことで、より質の高い記事が生成できます。具体的な指示を出すことがポイントです。
"""

    prompt = f"""以下の記事ドラフトを磨き上げてください。

キーワード: {keyword}

ドラフト:
{draft}

以下の点を改善してください：
1. 自然で読みやすい文章に
2. 専門性を保ちつつ分かりやすく
3. 導入部分を魅力的に
4. 適切な接続詞の使用

JSON形式で回答してください：
{{
    "polished": "磨き上げられた記事",
    "word_count": 文字数,
    "changes_made": ["変更点1", "変更点2"]
}}"""

    config = LLMRequestConfig(max_tokens=4000, temperature=0.8)
    response = await client.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a content polishing expert.",
        config=config,
    )

    # Try to parse JSON
    try:
        parsed = json.loads(response.content)
        polished = parsed.get("polished", "")
        changes = parsed.get("changes_made", [])
    except json.JSONDecodeError:
        polished = response.content[:500]
        changes = ["Natural language improvements", "Flow enhancement"]

    result = {
        "step": "step7b",
        "keyword": keyword,
        "polished_preview": polished[:400] + "..." if len(str(polished)) > 400 else polished,
        "changes_made": changes[:3] if isinstance(changes, list) else ["Improvements made"],
        "model": response.model,
        "tokens": {
            "input": response.token_usage.input,
            "output": response.token_usage.output,
        },
    }

    print(f"✅ Model: {result['model']}")
    print(f"✅ Changes made: {len(result['changes_made'])}")
    print(f"✅ Tokens: input={result['tokens']['input']}, output={result['tokens']['output']}")
    print(f"\n📝 Polished preview:\n{result['polished_preview'][:300]}...")

    return result


async def test_step8_fact_check() -> dict[str, Any]:
    """Test Step 8: Fact Check using Gemini."""
    print_section("Step 8: Fact Check (Gemini)")

    from apps.api.llm import GeminiClient
    from apps.api.llm.schemas import LLMRequestConfig

    client = GeminiClient()
    keyword = "AI活用SEO記事作成"

    content = """
AIを活用したSEO記事作成は、2023年以降急速に普及しています。
ChatGPTやGeminiなどのLLMは、月間数億人のユーザーに利用されています。
Google検索アルゴリズムは、AIで生成されたコンテンツを自動的にペナルティとして扱うわけではありません。
"""

    prompt = f"""以下のコンテンツの事実確認を行い、FAQを生成してください。

キーワード: {keyword}

コンテンツ:
{content}

以下を実施してください：
1. 含まれる主張を抽出
2. 各主張の検証
3. 関連するFAQを3つ生成

回答形式:
CLAIMS: [主張リスト]
VERIFICATION: [検証結果]
FAQ:
Q1: ...
A1: ...
"""

    config = LLMRequestConfig(max_tokens=2500, temperature=0.3)
    response = await client.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You are a fact-checking specialist.",
        config=config,
    )

    has_contradictions = "contradiction" in response.content.lower() or "incorrect" in response.content.lower()

    result = {
        "step": "step8",
        "keyword": keyword,
        "verification_preview": response.content[:400] + "..." if len(response.content) > 400 else response.content,
        "has_contradictions": has_contradictions,
        "model": response.model,
        "tokens": {
            "input": response.token_usage.input,
            "output": response.token_usage.output,
        },
    }

    print(f"✅ Model: {result['model']}")
    print(f"✅ Contradictions found: {result['has_contradictions']}")
    print(f"✅ Tokens: input={result['tokens']['input']}, output={result['tokens']['output']}")
    print(f"\n📝 Verification preview:\n{result['verification_preview'][:350]}...")

    return result


async def test_step9_final_rewrite() -> dict[str, Any]:
    """Test Step 9: Final Rewrite using Anthropic."""
    print_section("Step 9: Final Rewrite (Anthropic)")

    from apps.api.llm import AnthropicClient
    from apps.api.llm.schemas import LLMRequestConfig

    client = AnthropicClient()
    keyword = "AI活用SEO記事作成"

    polished_content = """
# AI活用SEO記事作成の完全ガイド

AIを活用したSEO記事作成は、コンテンツマーケティングに革命をもたらしています。
本記事では、実践的なノウハウをお伝えします。
"""

    faq = """
Q: AIで作成した記事はGoogleにペナルティを受けますか？
A: いいえ、高品質なコンテンツであれば問題ありません。
"""

    prompt = f"""以下のコンテンツを最終リライトしてください。

キーワード: {keyword}

本文:
{polished_content}

FAQ:
{faq}

JSON形式で以下を出力してください：
{{
    "final_content": "最終版記事",
    "word_count": 文字数,
    "meta_description": "120文字以内のメタディスクリプション",
    "internal_link_suggestions": ["関連記事リンク候補"]
}}"""

    config = LLMRequestConfig(max_tokens=4000, temperature=0.6)
    response = await client.generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="Perform the final rewrite of the article.",
        config=config,
    )

    # Try to parse JSON
    try:
        parsed = json.loads(response.content)
        final_content = parsed.get("final_content", "")
        meta_desc = parsed.get("meta_description", "")
    except json.JSONDecodeError:
        final_content = response.content[:500]
        meta_desc = "AI活用SEO記事作成の実践ガイド"

    result = {
        "step": "step9",
        "keyword": keyword,
        "final_content_preview": final_content[:400] + "..." if len(str(final_content)) > 400 else final_content,
        "meta_description": meta_desc,
        "model": response.model,
        "tokens": {
            "input": response.token_usage.input,
            "output": response.token_usage.output,
        },
    }

    print(f"✅ Model: {result['model']}")
    print(f"✅ Meta description: {result['meta_description'][:80]}...")
    print(f"✅ Tokens: input={result['tokens']['input']}, output={result['tokens']['output']}")
    print(f"\n📝 Final content preview:\n{result['final_content_preview'][:300]}...")

    return result


async def main() -> None:
    """Run all step tests."""
    print_section("SEO Article Generation Workflow - Step Tests", "=")

    results = {}

    # Step 2: CSV Validation (no LLM)
    try:
        results["step2"] = await test_step2_csv_validation()
    except Exception as e:
        print(f"❌ Step 2 failed: {e}")

    # Step 3A: Query Analysis (Gemini)
    try:
        results["step3a"] = await test_step3a_query_analysis()
    except Exception as e:
        print(f"❌ Step 3A failed: {e}")

    # Step 3B: Co-occurrence (Gemini)
    try:
        results["step3b"] = await test_step3b_cooccurrence()
    except Exception as e:
        print(f"❌ Step 3B failed: {e}")

    # Step 3C: Competitor Analysis (Gemini)
    try:
        results["step3c"] = await test_step3c_competitor_analysis()
    except Exception as e:
        print(f"❌ Step 3C failed: {e}")

    # Step 5: Primary Sources (simulated)
    try:
        results["step5"] = await test_step5_primary_sources()
    except Exception as e:
        print(f"❌ Step 5 failed: {e}")

    # Step 6: Enhanced Outline (Anthropic)
    try:
        results["step6"] = await test_step6_enhanced_outline()
    except Exception as e:
        print(f"❌ Step 6 failed: {e}")

    # Step 6.5: Integration (Anthropic)
    try:
        results["step6_5"] = await test_step6_5_integration()
    except Exception as e:
        print(f"❌ Step 6.5 failed: {e}")

    # Step 7B: Brush Up (Gemini)
    try:
        results["step7b"] = await test_step7b_brush_up()
    except Exception as e:
        print(f"❌ Step 7B failed: {e}")

    # Step 8: Fact Check (Gemini)
    try:
        results["step8"] = await test_step8_fact_check()
    except Exception as e:
        print(f"❌ Step 8 failed: {e}")

    # Step 9: Final Rewrite (Anthropic)
    try:
        results["step9"] = await test_step9_final_rewrite()
    except Exception as e:
        print(f"❌ Step 9 failed: {e}")

    # Summary
    print_section("Test Summary", "=")
    print(f"Total steps tested: {len(results)}")
    print(f"Steps: {', '.join(results.keys())}")

    # Calculate total tokens
    total_input = sum(
        r.get("tokens", {}).get("input", 0)
        for r in results.values()
        if isinstance(r.get("tokens"), dict)
    )
    total_output = sum(
        r.get("tokens", {}).get("output", 0)
        for r in results.values()
        if isinstance(r.get("tokens"), dict)
    )

    print(f"\n📊 Total token usage:")
    print(f"   Input tokens: {total_input}")
    print(f"   Output tokens: {total_output}")
    print(f"   Total: {total_input + total_output}")


if __name__ == "__main__":
    asyncio.run(main())
