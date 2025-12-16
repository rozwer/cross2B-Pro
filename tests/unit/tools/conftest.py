"""
Tools テスト用のフィクスチャ
"""

import os
import pytest
from unittest.mock import AsyncMock, patch

# テスト用の環境変数設定
os.environ.setdefault("USE_MOCK_GOOGLE_ADS", "true")


@pytest.fixture
def mock_serp_response():
    """SerpApi のモックレスポンス"""
    return {
        "organic_results": [
            {
                "position": 1,
                "title": "SEO対策とは？基本から実践まで解説",
                "link": "https://example.com/seo-guide",
                "snippet": "SEO対策の基本から実践的なテクニックまで詳しく解説します。",
            },
            {
                "position": 2,
                "title": "SEO対策の費用相場と選び方",
                "link": "https://example.com/seo-cost",
                "snippet": "SEO対策を外注する場合の費用相場と、業者の選び方を紹介。",
            },
            {
                "position": 3,
                "title": "SEO対策完全ガイド2024",
                "link": "https://example.com/seo-2024",
                "snippet": "2024年最新のSEO対策手法を網羅的に解説。",
            },
        ]
    }


@pytest.fixture
def mock_html_content():
    """モックHTMLコンテンツ"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>テストページ</title>
        <meta name="description" content="これはテスト用のページです">
    </head>
    <body>
        <header>ヘッダー</header>
        <nav>ナビゲーション</nav>
        <main>
            <h1>メインタイトル</h1>
            <p>これは本文のテキストです。SEO対策について解説しています。</p>
            <p>検索エンジン最適化は重要な施策です。</p>
        </main>
        <footer>フッター</footer>
    </body>
    </html>
    """


@pytest.fixture
def mock_httpx_client():
    """httpx.AsyncClient のモック"""
    with patch("httpx.AsyncClient") as mock:
        yield mock


@pytest.fixture(autouse=True)
def reset_registry():
    """各テスト前にレジストリをリセット"""
    from apps.api.tools.registry import ToolRegistry

    # 現在の状態を保存
    original_tools = ToolRegistry._tools.copy()
    original_manifests = ToolRegistry._manifests.copy()

    yield

    # テスト後に元に戻す
    ToolRegistry._tools = original_tools
    ToolRegistry._manifests = original_manifests
