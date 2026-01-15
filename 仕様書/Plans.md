# LLM/API設定管理

> **作成日**: 2026-01-15
> **目的**: 環境変数で固定されているAPIキー・モデル設定をUI側から変更可能にする

---

## 概要

### 現状の問題点

1. **環境変数固定**: `.env` でAPIキー・モデル名を設定しており、変更にはDockerコンテナ再起動が必要
2. **配布時の障壁**: 他者に渡す際に `.env` ファイルの編集が必要で敷居が高い
3. **疎通確認なし**: 設定変更後にAPIが正常に動作するか事前確認できない

### 改善目標

- **UI設定画面**: アプリ側でAPIキー・モデル名を設定可能に
- **疎通テスト**: 設定変更時に実際のAPIで接続確認
- **DB永続化**: 設定をDBに保存（環境変数は初期値/フォールバック）
- **セキュリティ**: APIキーは暗号化保存、表示時はマスク

### 対象サービス

| サービス | 用途 | 疎通テスト方式 |
|----------|------|----------------|
| Gemini | LLM（キーワード分析等） | 簡易プロンプト送信 |
| OpenAI | LLM | 簡易プロンプト送信 |
| Anthropic | LLM（本文生成等） | 簡易プロンプト送信 |
| SERP API | 検索結果取得 | 軽量クエリ実行 |
| Google Ads | キーワード調査 | API接続確認 |
| GitHub | PR/Issue連携 | ユーザー情報取得（キーマスク必須） |

---

## フェーズ1: バックエンド ✅完了

### 1.1 DBスキーマ（`api_settings`テーブル）

- ✅ `apps/api/db/models.py` に `ApiSetting` モデル追加
- tenant_id, service, api_key_encrypted, default_model, config(JSONB)
- verified_at（疎通確認日時）、is_active
- UNIQUE(tenant_id, service)

### 1.2 APIエンドポイント

| メソッド | パス | 用途 | 状態 |
|----------|------|------|------|
| GET | `/api/settings` | 全設定一覧（キーはマスク） | ✅ |
| GET | `/api/settings/{service}` | 個別設定取得 | ✅ |
| PUT | `/api/settings/{service}` | 設定更新 | ✅ |
| POST | `/api/settings/{service}/test` | 疎通テスト | ✅ |
| DELETE | `/api/settings/{service}` | 設定削除（環境変数にフォールバック） | ✅ |

### 1.3 暗号化

- ✅ `apps/api/services/encryption.py`: AES-256-GCM
- 環境変数: `SETTINGS_ENCRYPTION_KEY`

### 1.4 接続テスト

- ✅ `apps/api/services/connection_test.py`: LLM/SERP/GitHub接続テスト

---

## フェーズ2: フロントエンド ✅完了

### 2.1 設定画面UI（`/settings?tab=apikeys`）

- ✅ `apps/ui/src/components/tabs/ApiKeysTab.tsx` 新規作成
- LLMプロバイダー（Gemini/OpenAI/Anthropic）: APIキー入力、モデル選択、テストボタン
- 外部サービス（SERP/Google Ads/GitHub）: APIキー入力、テストボタン
- 接続状態表示（✓接続確認済み / ⚠未設定）

### 2.2 GitHub Token特別対応

- ✅ 表示: 保存後は `ghp_****` のみ
- ✅ 警告: 「GitHubトークンは露出すると自動で無効化されます」の注意書き

### 2.3 API Client

- ✅ `apps/ui/src/lib/api.ts` に settings API 追加
- ✅ `apps/ui/src/lib/types.ts` に型定義追加

---

## フェーズ3: Worker統合 ✅完了

### 3.1 設定プロバイダー

- ✅ `apps/api/services/settings_provider.py` 新規作成
- 読み込み優先順位: DB → 環境変数
- `SettingsProvider` クラスで統一管理

### 3.2 LLMクライアント連携

- ✅ `apps/api/llm/base.py` に `get_llm_client_with_settings()` 追加
- tenant_id を指定すると DB から設定を取得
- 省略時は環境変数にフォールバック

### 3.3 使用例

```python
from apps.api.llm import get_llm_client_with_settings

# DB設定を使用
client = await get_llm_client_with_settings(
    "gemini",
    tenant_id="tenant-123",
    tenant_manager=get_tenant_manager(),
)

# 環境変数のみ使用（従来互換）
client = await get_llm_client_with_settings("gemini")
```

---

## ファイル変更一覧

| ファイル | 変更 |
|----------|------|
| `apps/api/db/models.py` | ApiSetting モデル追加 |
| `apps/api/routers/settings.py` | **新規** |
| `apps/api/services/encryption.py` | **新規** |
| `apps/api/services/connection_test.py` | **新規** |
| `apps/api/services/settings_provider.py` | **新規** |
| `apps/api/llm/base.py` | get_llm_client_with_settings 追加 |
| `apps/api/llm/__init__.py` | エクスポート追加 |
| `apps/api/main.py` | settings router 登録 |
| `apps/ui/src/app/settings/page.tsx` | APIキータブ追加 |
| `apps/ui/src/components/tabs/ApiKeysTab.tsx` | **新規** |
| `apps/ui/src/lib/api.ts` | settings API 追加 |
| `apps/ui/src/lib/types.ts` | Settings型定義追加 |

---

## 完了済みタスク

> - イベントログ改善: `仕様書/archive/event-log-improvement.md`
> - 成果物アップロード: `仕様書/archive/artifact-upload.md`
