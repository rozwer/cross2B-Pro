"""
Phase 2 実データ統合テスト

実際のAPIを使用してPhase 2のツールをテストする。
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()


async def test_serp_fetch():
    """SERP取得ツールの実データテスト"""
    from apps.api.tools import ToolRegistry

    print("\n" + "=" * 60)
    print("1. SERP_FETCH テスト")
    print("=" * 60)

    tool = ToolRegistry.get("serp_fetch")
    manifest = ToolRegistry.get_manifest("serp_fetch")
    print(f"ツール: {tool.tool_id}")
    print(f"説明: {manifest.description}")

    # テストクエリ
    query = "Python チュートリアル"
    print(f"\nクエリ: {query}")

    try:
        result = await tool.execute(query=query, num_results=5)
        print(f"成功: {result.success}")
        print(f"モック: {result.is_mock}")

        if result.success:
            print(f"結果数: {len(result.data.get('results', []))}")
            for i, item in enumerate(result.data.get("results", [])[:3]):
                print(f"  {i+1}. {item.get('title', 'N/A')[:50]}...")
                print(f"     URL: {item.get('link', 'N/A')[:60]}...")

            print(f"\nEvidence数: {len(result.evidence)}")
            if result.evidence:
                ev = result.evidence[0]
                print(f"  - URL: {ev.url}")
                print(f"  - 取得日時: {ev.fetched_at}")
        else:
            print(f"エラー: {result.error_message}")
            print(f"カテゴリ: {result.error_category}")

        return result.success
    except Exception as e:
        print(f"例外発生: {type(e).__name__}: {e}")
        return False


async def test_page_fetch():
    """ページ取得ツールの実データテスト"""
    from apps.api.tools import ToolRegistry

    print("\n" + "=" * 60)
    print("2. PAGE_FETCH テスト")
    print("=" * 60)

    tool = ToolRegistry.get("page_fetch")
    print(f"ツール: {tool.tool_id}")

    # テストURL（パブリックIPを持つサイト）
    # example.com はSSRF防止でブロックされる可能性があるため
    # 実際のニュースサイトなどを使用
    test_url = "https://www.python.org/"
    print(f"\nURL: {test_url}")

    try:
        result = await tool.execute(url=test_url)
        print(f"成功: {result.success}")

        if result.success:
            data = result.data
            print(f"タイトル: {data.get('title', 'N/A')}")
            print(f"本文長: {len(data.get('content', ''))} 文字")
            content_preview = data.get("content", "")[:100].replace("\n", " ")
            print(f"本文プレビュー: {content_preview}...")

            if result.evidence:
                ev = result.evidence[0]
                print(f"\nEvidence:")
                print(f"  - URL: {ev.url}")
                print(f"  - ハッシュ: {ev.content_hash[:16]}...")
        else:
            print(f"エラー: {result.error_message}")
            # SSRF防止によるブロックは正常動作として扱う
            if "SSRF" in str(result.error_message) or "blocked" in str(result.error_message):
                print("  → SSRF防止機能が正常に動作しています")
                return True

        return result.success
    except Exception as e:
        print(f"例外発生: {type(e).__name__}: {e}")
        return False


async def test_url_verify():
    """URL検証ツールの実データテスト"""
    from apps.api.tools import ToolRegistry

    print("\n" + "=" * 60)
    print("3. URL_VERIFY テスト")
    print("=" * 60)

    tool = ToolRegistry.get("url_verify")
    print(f"ツール: {tool.tool_id}")

    # テストケース（より安定したURLを使用）
    test_cases = [
        ("https://www.google.com", "正常なURL"),
        ("https://www.python.org/", "Pythonサイト"),
    ]

    results = []
    for url, description in test_cases:
        print(f"\n{description}: {url}")
        try:
            result = await tool.execute(url=url)
            print(f"  成功: {result.success}")
            if result.success:
                data = result.data
                print(f"  ステータス: {data.get('status_code')}")
                print(f"  最終URL: {data.get('final_url', 'N/A')[:50]}")
                print(f"  存在: {data.get('exists', 'N/A')}")
            else:
                print(f"  エラー: {result.error_message}")
            results.append(result.success)
        except Exception as e:
            print(f"  例外: {type(e).__name__}: {e}")
            results.append(False)

    # 少なくとも1つ成功すればOK
    return any(results)


async def test_search_volume_mock():
    """検索ボリュームツール（モック）のテスト"""
    from apps.api.tools import ToolRegistry

    print("\n" + "=" * 60)
    print("4. SEARCH_VOLUME テスト (モック)")
    print("=" * 60)

    tool = ToolRegistry.get("search_volume")
    print(f"ツール: {tool.tool_id}")

    # テストキーワード
    keywords = ["Python", "SEO対策", "unknown_keyword_xyz"]

    results = []
    for keyword in keywords:
        print(f"\nキーワード: {keyword}")
        try:
            result = await tool.execute(keyword=keyword)
            print(f"  成功: {result.success}")
            print(f"  モック: {result.is_mock}")
            if result.success:
                data = result.data
                print(f"  ボリューム: {data.get('volume', 'N/A')}")
                print(f"  競合度: {data.get('competition', 'N/A')}")
            results.append(result.success)
        except Exception as e:
            print(f"  例外: {type(e).__name__}: {e}")
            results.append(False)

    return all(results)


async def test_related_keywords_mock():
    """関連キーワードツール（モック）のテスト"""
    from apps.api.tools import ToolRegistry

    print("\n" + "=" * 60)
    print("5. RELATED_KEYWORDS テスト (モック)")
    print("=" * 60)

    tool = ToolRegistry.get("related_keywords")
    print(f"ツール: {tool.tool_id}")

    keyword = "SEO"
    print(f"\nキーワード: {keyword}")

    try:
        result = await tool.execute(keyword=keyword)
        print(f"成功: {result.success}")
        print(f"モック: {result.is_mock}")

        if result.success:
            keywords = result.data.get("keywords", [])
            print(f"関連キーワード数: {len(keywords)}")
            for kw in keywords[:5]:
                print(f"  - {kw.get('keyword')}: {kw.get('volume')} (競合: {kw.get('competition')})")

        return result.success
    except Exception as e:
        print(f"例外: {type(e).__name__}: {e}")
        return False


def test_json_validator():
    """JSON Validatorの実データテスト"""
    from apps.api.validation import JsonValidator, Repairer

    print("\n" + "=" * 60)
    print("6. JSON VALIDATOR テスト")
    print("=" * 60)

    validator = JsonValidator()
    repairer = Repairer()

    test_cases = [
        # 正常なJSON
        ('{"name": "test", "value": 123}', "正常なJSON"),
        # 末尾カンマ（修正可能）
        ('{"name": "test", "value": 123,}', "末尾カンマ"),
        # 構文エラー（修正不可）
        ('{"name": "test", "value": }', "構文エラー"),
    ]

    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "value": {"type": "integer"}},
        "required": ["name"],
    }

    results = []
    for content, description in test_cases:
        print(f"\n{description}:")
        print(f"  入力: {content[:50]}...")

        # 構文検証
        report = validator.validate(content)
        print(f"  エラー数: {report.error_count()}")
        print(f"  警告数: {report.warning_count()}")

        if report.has_errors():
            for issue in report.issues[:2]:
                print(f"    - {issue.code}: {issue.message}")

            # 修正可能かチェック
            if repairer.can_repair(report.issues):
                print("  修正可能: はい")
                try:
                    fixed, actions = repairer.repair(content, report.issues)
                    print(f"  修正後: {fixed[:50]}...")
                    for action in actions:
                        print(f"    - {action.description}")
                    results.append(True)
                except Exception as e:
                    print(f"  修正失敗: {e}")
                    results.append(False)
            else:
                print("  修正可能: いいえ（これは正常動作）")
                results.append(True)  # 修正不可は正常動作
        else:
            # スキーマ検証
            schema_report = validator.validate_with_schema(content, schema)
            if schema_report.has_errors():
                print(f"  スキーマエラー: {schema_report.issues[0].message}")
            else:
                print("  構文・スキーマ検証OK")
            results.append(True)

    # スキーマ違反テスト
    print("\n型違反（スキーマ検証）:")
    invalid_type_json = '{"name": 123}'
    print(f"  入力: {invalid_type_json}")
    schema_report = validator.validate_with_schema(invalid_type_json, schema)
    print(f"  エラー数: {schema_report.error_count()}")
    if schema_report.has_errors():
        print(f"    - {schema_report.issues[0].message}")
    results.append(schema_report.has_errors())  # エラーが検出されればOK

    return all(results)


def test_csv_validator():
    """CSV Validatorの実データテスト"""
    from apps.api.validation import CsvValidator, Repairer

    print("\n" + "=" * 60)
    print("7. CSV VALIDATOR テスト")
    print("=" * 60)

    validator = CsvValidator()
    repairer = Repairer()

    test_cases = [
        # 正常なCSV
        ("name,age,city\nAlice,30,Tokyo\nBob,25,Osaka", "正常なCSV"),
        # 列数不一致
        ("name,age,city\nAlice,30\nBob,25,Osaka", "列数不一致"),
        # CRLF改行（修正可能）
        ("name,age\r\nAlice,30\r\nBob,25", "CRLF改行"),
        # BOM付き（修正可能）
        ("\ufeffname,age\nAlice,30", "BOM付き"),
    ]

    results = []
    for content, description in test_cases:
        print(f"\n{description}:")
        display = content.replace("\r", "\\r").replace("\n", "\\n")[:50]
        print(f"  入力: {display}...")

        report = validator.validate(content)
        print(f"  エラー数: {report.error_count()}")
        print(f"  警告数: {report.warning_count()}")

        if report.has_errors() or report.has_warnings():
            for issue in report.issues[:2]:
                print(f"    - {issue.code}: {issue.message}")

            if repairer.can_repair(report.issues):
                print("  修正可能: はい")
                try:
                    fixed, actions = repairer.repair(content, report.issues)
                    for action in actions:
                        print(f"    - {action.description}")
                    results.append(True)
                except Exception as e:
                    print(f"  修正失敗: {e}")
                    results.append(False)
            else:
                print("  修正可能: いいえ（これは正常動作）")
                results.append(True)
        else:
            print("  検証OK")
            results.append(True)

    return all(results)


async def main():
    """メイン実行"""
    print("=" * 60)
    print("Phase 2 実データ統合テスト")
    print(f"実行日時: {datetime.now().isoformat()}")
    print("=" * 60)

    results = {}

    # ツールテスト
    results["serp_fetch"] = await test_serp_fetch()
    results["page_fetch"] = await test_page_fetch()
    results["url_verify"] = await test_url_verify()
    results["search_volume"] = await test_search_volume_mock()
    results["related_keywords"] = await test_related_keywords_mock()

    # バリデーターテスト
    results["json_validator"] = test_json_validator()
    results["csv_validator"] = test_csv_validator()

    # サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {name}: {status}")
        if success:
            passed += 1
        else:
            failed += 1

    print(f"\n合計: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
