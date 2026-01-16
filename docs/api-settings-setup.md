# API設定管理機能 セットアップガイド

> APIキー・モデル名をWebUIから設定可能にする機能の初期設定手順

## 概要

この機能により、以下のサービスのAPIキーをWebUIから設定・管理できます：

| サービス | 用途 | 環境変数名 |
|----------|------|------------|
| Gemini | LLM（キーワード分析等） | `GEMINI_API_KEY` |
| OpenAI | LLM | `OPENAI_API_KEY` |
| Anthropic | LLM（本文生成等） | `ANTHROPIC_API_KEY` |
| SERP API | 検索結果取得 | `SERP_API_KEY` |
| Google Ads | キーワード調査 | `GOOGLE_ADS_API_KEY` |
| GitHub | PR/Issue連携 | `GITHUB_TOKEN` |

## 初期設定

### 1. 暗号化キーの生成（必須）

APIキーはAES-256-GCMで暗号化して保存されます。暗号化キーを生成して設定してください。

```bash
# キー生成
python -c "import secrets; import base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

出力例：`3xJ9+Kv5mN2pQ8rS1tU4wX7yZ0aB/cD6eF9gH2iJ=`

### 2. 環境変数の設定

`.env` ファイルに以下を追加：

```env
# API設定暗号化キー（必須）
SETTINGS_ENCRYPTION_KEY=<上記で生成したキー>

# 初期値としての環境変数（任意）
# UIから設定しない場合のフォールバックとして使用
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
SERP_API_KEY=your-serp-key
GITHUB_TOKEN=your-github-token
```

### 3. DBマイグレーション

`api_settings` テーブルが自動作成されます。初回起動時に以下を確認：

```bash
# DBが起動していることを確認
docker compose up -d postgres

# APIサーバー起動（テーブル自動作成）
docker compose up -d api
```

### 4. 動作確認

1. ブラウザで `http://localhost:3000/settings?tab=apikeys` にアクセス
2. 各サービスの設定カードが表示されることを確認
3. 「接続テスト」ボタンで疎通確認

## 使用方法

### Web UIからの設定

1. `/settings?tab=apikeys` にアクセス
2. サービスカードをクリックして展開
3. 「キーを設定」または「キーを変更」をクリック
4. APIキーを入力
5. 「保存」をクリック
6. 「接続テスト」で動作確認

### 設定の優先順位

```
1. DB設定（UIから設定したもの）
2. 環境変数（.envファイル）
3. 未設定（エラー）
```

### Worker/Activityからの使用

```python
from apps.api.llm import get_llm_client_with_settings
from apps.api.db import get_tenant_manager

# DB設定を使用
client = await get_llm_client_with_settings(
    "gemini",
    tenant_id="tenant-123",
    tenant_manager=get_tenant_manager(),
)

# 環境変数のみ使用（従来互換）
client = await get_llm_client_with_settings("gemini")
```

## APIエンドポイント

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/settings` | 全設定一覧（キーはマスク） |
| GET | `/api/settings/{service}` | 個別設定取得 |
| PUT | `/api/settings/{service}` | 設定更新 |
| POST | `/api/settings/{service}/test` | 接続テスト |
| DELETE | `/api/settings/{service}` | 設定削除 |

## セキュリティ

### 暗号化

- アルゴリズム: AES-256-GCM（認証付き暗号）
- キー長: 256ビット（32バイト）
- ナンス: 12バイト（各暗号化で新規生成）

### 表示マスキング

- 通常のAPIキー: 末尾4文字のみ表示（例: `****xyz9`）
- GitHubトークン: 先頭4文字のみ表示（例: `ghp_****`）
  - 理由: GitHubはトークン露出を検知すると自動で無効化するため

### マルチテナント分離

- 全ての設定は `tenant_id` でスコープ
- テナント間での設定参照は不可

## トラブルシューティング

### 「Encryption key not set」エラー

```
EncryptionError: Encryption key not set. Please set SETTINGS_ENCRYPTION_KEY environment variable.
```

**解決策**: `.env` に `SETTINGS_ENCRYPTION_KEY` を設定

### 「Invalid encryption key size」エラー

```
EncryptionError: Invalid encryption key size: expected 32 bytes, got N
```

**解決策**: 正しい方法で32バイトのキーを生成し直す

### 接続テスト失敗

1. APIキーが正しいか確認
2. ネットワーク接続を確認
3. サービスのレート制限を確認

### DB設定が反映されない

1. APIサーバーを再起動
2. キャッシュクリア: `_LLM_CLIENT_CACHE` は tenant_id 単位でキャッシュ

## ファイル構成

```
apps/api/
├── db/
│   └── models.py           # ApiSetting モデル
├── routers/
│   └── settings.py         # 設定APIエンドポイント
├── services/
│   ├── encryption.py       # AES-256-GCM暗号化
│   ├── connection_test.py  # 接続テストサービス
│   └── settings_provider.py # 設定取得の統一インターフェース
└── llm/
    └── base.py             # get_llm_client_with_settings()

apps/ui/src/
├── app/settings/page.tsx   # 設定ページ（APIキータブ追加）
├── components/tabs/
│   └── ApiKeysTab.tsx      # APIキー設定UI
└── lib/
    ├── api.ts              # settings APIクライアント
    └── types.ts            # 型定義
```

## 関連ドキュメント

- [Plans.md](../仕様書/Plans.md) - 実装計画
- [workflow.md](../仕様書/workflow.md) - ワークフロー仕様
