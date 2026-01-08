#!/usr/bin/env python3
"""
WordPress自動投稿スクリプト
工程12で生成したHTMLをWordPressに自動投稿します。

使用方法:
    python wp_auto_post.py --html "工程12_WordPress用HTML.html" --title "記事タイトル"

オプション:
    --html      : HTMLファイルパス（必須）
    --title     : 記事タイトル（必須）
    --eyecatch  : アイキャッチ画像パス
    --category  : カテゴリID
    --tags      : タグ（カンマ区切り）
    --status    : draft / publish / pending（デフォルト: draft）
    --config    : 設定ファイルパス（デフォルト: config.json）
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("エラー: requestsライブラリがインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("  pip install requests")
    sys.exit(1)


class WordPressAPI:
    """WordPress REST API クライアント"""

    def __init__(self, site_url: str, username: str, app_password: str):
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        self.auth = (username, app_password)
        self.session = requests.Session()
        self.session.auth = self.auth

    def test_connection(self) -> bool:
        """API接続テスト"""
        try:
            response = self.session.get(f"{self.api_base}/users/me")
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ API接続成功: {user_data.get('name', 'Unknown')}")
                return True
            else:
                print(f"❌ API接続失敗: {response.status_code}")
                print(f"   レスポンス: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"❌ 接続エラー: {e}")
            return False

    def upload_media(self, file_path: str, alt_text: str = "") -> dict:
        """画像をメディアライブラリにアップロード"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"画像ファイルが見つかりません: {file_path}")

        # Content-Typeを判定
        ext = file_path.suffix.lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        content_type = content_types.get(ext, 'application/octet-stream')

        headers = {
            'Content-Type': content_type,
            'Content-Disposition': f'attachment; filename="{file_path.name}"'
        }

        with open(file_path, 'rb') as f:
            response = self.session.post(
                f"{self.api_base}/media",
                headers=headers,
                data=f.read()
            )

        if response.status_code == 201:
            media_data = response.json()
            media_id = media_data['id']

            # alt属性を設定
            if alt_text:
                self.session.post(
                    f"{self.api_base}/media/{media_id}",
                    json={'alt_text': alt_text}
                )

            return {
                'id': media_id,
                'url': media_data.get('source_url', ''),
                'success': True
            }
        else:
            return {
                'success': False,
                'error': response.text,
                'status_code': response.status_code
            }

    def create_post(
        self,
        title: str,
        content: str,
        status: str = 'draft',
        categories: list = None,
        tags: list = None,
        featured_media: int = None,
        excerpt: str = "",
        slug: str = ""
    ) -> dict:
        """記事を作成"""

        post_data = {
            'title': title,
            'content': content,
            'status': status
        }

        if categories:
            post_data['categories'] = categories
        if tags:
            post_data['tags'] = tags
        if featured_media:
            post_data['featured_media'] = featured_media
        if excerpt:
            post_data['excerpt'] = excerpt
        if slug:
            post_data['slug'] = slug

        response = self.session.post(
            f"{self.api_base}/posts",
            json=post_data
        )

        if response.status_code == 201:
            post = response.json()
            return {
                'success': True,
                'id': post['id'],
                'link': post['link'],
                'status': post['status'],
                'edit_url': f"{self.site_url}/wp-admin/post.php?post={post['id']}&action=edit",
                'preview_url': f"{post['link']}{'&' if '?' in post['link'] else '?'}preview=true"
            }
        else:
            return {
                'success': False,
                'error': response.text,
                'status_code': response.status_code
            }

    def get_or_create_tag(self, tag_name: str) -> int:
        """タグを取得または作成してIDを返す"""
        # 既存タグを検索
        response = self.session.get(
            f"{self.api_base}/tags",
            params={'search': tag_name}
        )

        if response.status_code == 200:
            tags = response.json()
            for tag in tags:
                if tag['name'].lower() == tag_name.lower():
                    return tag['id']

        # 新規作成
        response = self.session.post(
            f"{self.api_base}/tags",
            json={'name': tag_name}
        )

        if response.status_code == 201:
            return response.json()['id']

        return None


def load_config(config_path: str) -> dict:
    """設定ファイルを読み込む"""
    config_path = Path(config_path)

    if not config_path.exists():
        print(f"❌ 設定ファイルが見つかりません: {config_path}")
        print("\nconfig.jsonを作成してください。例:")
        print(json.dumps({
            "wordpress": {
                "site_url": "https://example.com",
                "username": "your_username",
                "app_password": "xxxx xxxx xxxx xxxx xxxx xxxx"
            },
            "default_settings": {
                "post_status": "draft",
                "category_ids": [1],
                "tag_ids": []
            }
        }, indent=4, ensure_ascii=False))
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_html_content(html_path: str) -> str:
    """HTMLファイルを読み込み、body内のコンテンツを抽出"""
    html_path = Path(html_path)

    if not html_path.exists():
        raise FileNotFoundError(f"HTMLファイルが見つかりません: {html_path}")

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # <body>タグ内のコンテンツを抽出
    body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
    if body_match:
        content = body_match.group(1)

    # コメント（投稿手順など）を除去（オプション）
    # content = re.sub(r'<!--[\s\S]*?-->', '', content)

    return content.strip()


def extract_alt_text_from_html(html_path: str) -> str:
    """HTMLからアイキャッチ画像のalt属性を抽出"""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # アイキャッチ画像設定のコメントからalt属性を探す
    alt_match = re.search(r'alt属性:\s*(.+)', content)
    if alt_match:
        return alt_match.group(1).strip()

    return ""


def main():
    parser = argparse.ArgumentParser(
        description='WordPress自動投稿スクリプト',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python wp_auto_post.py --html "工程12_WordPress用HTML.html" --title "記事タイトル"
  python wp_auto_post.py --html "article.html" --title "タイトル" --eyecatch "image.jpg" --status draft
        """
    )

    parser.add_argument('--html', required=True, help='HTMLファイルパス')
    parser.add_argument('--title', required=True, help='記事タイトル')
    parser.add_argument('--eyecatch', help='アイキャッチ画像パス')
    parser.add_argument('--category', type=int, help='カテゴリID')
    parser.add_argument('--tags', help='タグ（カンマ区切り）')
    parser.add_argument('--status', default='draft', choices=['draft', 'publish', 'pending', 'private'], help='投稿ステータス')
    parser.add_argument('--config', default='config.json', help='設定ファイルパス')
    parser.add_argument('--test', action='store_true', help='接続テストのみ実行')

    args = parser.parse_args()

    # 設定読み込み
    config = load_config(args.config)
    wp_config = config.get('wordpress', {})
    default_settings = config.get('default_settings', {})

    # APIクライアント初期化
    api = WordPressAPI(
        site_url=wp_config.get('site_url', ''),
        username=wp_config.get('username', ''),
        app_password=wp_config.get('app_password', '')
    )

    # 接続テスト
    print("\n📡 WordPress API接続テスト...")
    if not api.test_connection():
        print("\n設定を確認してください:")
        print(f"  - サイトURL: {wp_config.get('site_url', '未設定')}")
        print(f"  - ユーザー名: {wp_config.get('username', '未設定')}")
        print("  - アプリパスワード: ****")
        sys.exit(1)

    if args.test:
        print("\n✅ 接続テスト完了")
        sys.exit(0)

    # HTML読み込み
    print(f"\n📄 HTMLファイル読み込み: {args.html}")
    try:
        content = load_html_content(args.html)
        print(f"   コンテンツ長: {len(content)} 文字")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # アイキャッチ画像アップロード
    featured_media_id = None
    if args.eyecatch:
        print(f"\n🖼️  アイキャッチ画像アップロード: {args.eyecatch}")
        alt_text = extract_alt_text_from_html(args.html)
        result = api.upload_media(args.eyecatch, alt_text)

        if result['success']:
            featured_media_id = result['id']
            print(f"   ✅ アップロード成功")
            print(f"   メディアID: {result['id']}")
            print(f"   URL: {result['url']}")
        else:
            print(f"   ⚠️ アップロード失敗: {result.get('error', 'Unknown error')}")

    # タグ処理
    tag_ids = default_settings.get('tag_ids', [])
    if args.tags:
        print(f"\n🏷️  タグ処理: {args.tags}")
        for tag_name in args.tags.split(','):
            tag_name = tag_name.strip()
            if tag_name:
                tag_id = api.get_or_create_tag(tag_name)
                if tag_id:
                    tag_ids.append(tag_id)
                    print(f"   タグ '{tag_name}' → ID: {tag_id}")

    # カテゴリ
    category_ids = default_settings.get('category_ids', [])
    if args.category:
        category_ids = [args.category]

    # 記事投稿
    print(f"\n📝 記事投稿中...")
    print(f"   タイトル: {args.title}")
    print(f"   ステータス: {args.status}")

    result = api.create_post(
        title=args.title,
        content=content,
        status=args.status,
        categories=category_ids if category_ids else None,
        tags=tag_ids if tag_ids else None,
        featured_media=featured_media_id
    )

    if result['success']:
        print("\n" + "=" * 50)
        print("✅ WordPress自動投稿完了")
        print("=" * 50)
        print(f"""
投稿結果:
├─ 投稿ID: {result['id']}
├─ ステータス: {result['status']}
├─ 編集URL: {result['edit_url']}
└─ プレビューURL: {result['preview_url']}
""")
        if featured_media_id:
            print(f"""アイキャッチ画像:
├─ メディアID: {featured_media_id}
└─ 設定済み: ✅
""")

        print("""次のステップ:
1. 編集URLを開いて内容を確認
2. 画像プレースホルダーを実際の画像に置換
3. プレビューで最終確認
4. 公開
""")
    else:
        print("\n" + "=" * 50)
        print("❌ 投稿失敗")
        print("=" * 50)
        print(f"エラー: {result.get('error', 'Unknown error')}")
        print(f"ステータスコード: {result.get('status_code', 'N/A')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
