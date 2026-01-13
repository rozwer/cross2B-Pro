# Plans.md

> **最終更新**: 2026-01-13
> **アーカイブ**: 詳細な修正計画は `.claude/memory/archive/Plans-2026-01-13-full-review.md` を参照

---

## 📋 モック挙動・TODO・未実装リストアップ

> **目的**: 本番環境デプロイ前に対応が必要なモック/未実装箇所の可視化

### 🔴 CRITICAL: 認証系（本番環境ブロッカー）`cc:TODO`

| ファイル | 行番号 | 内容 | 対応方針 |
|---------|-------|------|----------|
| `apps/api/auth/middleware.py` | 35, 168-172, 205-213 | `SKIP_AUTH` で認証スキップ、固定の `DEV_TENANT_ID` | 認証プロバイダ統合 |
| `apps/api/routers/auth.py` | 35-55 | ログインが開発環境のみ、本番は `NotImplemented` | JWT/OAuth統合 |
| `apps/api/routers/auth.py` | 92 | `TODO: トークン無効化リスト（Redis等）` | Redis実装 |
| `apps/api/routers/diagnostics.py` | 78-95 | `get_current_user()` が placeholder | 認証連携後に実装 |
| `apps/ui/src/lib/websocket.ts` | 22 | `DEV_TENANT_ID` ハードコード | 認証から取得に変更 |
| `apps/ui/src/lib/auth.ts` | 244 | `TODO: 認証機能実装後に有効化` | 認証UI実装 |
| `apps/ui/src/lib/api.ts` | 4 | 開発段階で認証無効化 | 認証ヘッダー追加 |

### 🟠 MEDIUM: 外部API統合 `cc:TODO`

| ファイル | 行番号 | 内容 | 対応方針 |
|---------|-------|------|----------|
| `apps/api/tools/search.py` | 256-290 | `SearchVolumeTool` がモック実装 | Google Ads API統合 |
| `apps/api/tools/search.py` | 343-374 | `RelatedKeywordsTool` がモック実装 | 同上 |
| `apps/api/tools/search.py` | 295, 379 | `NotImplementedError` | API キー取得後に実装 |

### 🟡 LOW: 開発用設定・将来対応 `cc:TODO`

| ファイル | 行番号 | 内容 | 対応方針 |
|---------|-------|------|----------|
| `apps/api/main.py` | 65-66 | `USE_MOCK_LLM=true` で LLM なし起動 | 本番では無効化 |
| `apps/api/prompts/loader.py` | 219-223 | テスト用 `mock_pack` | テスト用として維持 |
| `apps/worker/workflows/article_workflow.py` | 83 | `TODO: Remove after migration` | マイグレーション後に削除 |
| `apps/api/auth/middleware.py` | 145 | `TODO: VULN-011 監査ログ連携` | 監査ログ実装と連携 |

### ⚪ INFO: 例外クラス・基底クラスの pass（正常）

設計上 `pass` のみで問題なし：
- `apps/api/db/models.py` - 基底クラス
- `apps/api/prompts/loader.py` - 例外クラス
- `apps/api/db/tenant.py` - 例外クラス
- `apps/api/storage/artifact_store.py` - 例外クラス

---

## 📊 サマリー

| 重大度 | 件数 | 対応タイミング |
|--------|------|----------------|
| **CRITICAL** | 7件 | 本番デプロイ前に必須 |
| **MEDIUM** | 3件 | Google Ads API取得後 |
| **LOW** | 4件 | 将来対応/維持 |
| **INFO** | 12件 | 対応不要（正常設計） |

---

## 次のアクション（本番デプロイ向け）

1. **認証プロバイダ選定**: Auth0 / Clerk / Firebase Auth / 自前JWT
2. **Google Ads API申請**: キーワード検索ボリューム取得用
3. **Redis導入検討**: トークン無効化リスト用

---

## アーカイブ（詳細な修正計画）

以下のアーカイブには詳細な修正計画が含まれています：

| ファイル | 内容 |
|---------|------|
| `.claude/memory/archive/Plans-2026-01-13-full-review.md` | 全体コードレビュー修正計画（CRITICAL 25件、HIGH 58件、MEDIUM 28件、LOW 8件） |

アーカイブの計画を実行する場合は該当ファイルを参照してください。
