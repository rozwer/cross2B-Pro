# Plans.md

> **最終更新**: 2026-01-16
> **アーカイブ**: 詳細な修正計画は `.claude/memory/archive/Plans-2026-01-13-full-review.md` を参照

---

## 🎯 作成済み記事一覧ページ & Claude Codeレビュー機能

> **目的**: 完了したrunの記事を一覧表示し、Claude Codeによるレビュー・編集・PR自動化を実現

### 概要
- **対象**: 完了した記事（completed runs）
- **流用**: 既存の成果物ページロジック（ArtifactViewer, GitHubActions）
- **新機能**: SEOレビュー、Claude Code編集、PR/マージ自動化

---

## ✅ フェーズ1: 記事一覧ページ基盤 `cc:DONE`

### 1.1 API: 完了記事一覧エンドポイント
- [x] `GET /api/articles` - 完了した記事一覧を取得
  - フィルタ: status=completed
  - キーワード検索
  - ページネーション対応
- [x] `GET /api/articles/{run_id}` - 記事詳細取得（step10/step12の成果物含む）

### 1.2 FE: 記事一覧ページ
- [x] `apps/ui/src/app/articles/page.tsx` - 一覧ページ作成
  - キーワード検索
  - レビューステータスフィルタ（すべて/レビュー済み/未レビュー）
- [x] `apps/ui/src/app/articles/[id]/page.tsx` - 記事詳細ページ
  - 概要タブ: メタデータ、成果物一覧
  - プレビュータブ: iframe表示、レビューパネル
  - GitHubタブ: Claude Code編集、PR管理

---

## ✅ フェーズ2: Claude Codeレビュー機能強化 `cc:DONE`

### 2.1 レビュー機能拡張（既存コード流用）
- [x] 既存の `PreviewPage` のレビュー機能を記事詳細に組み込み
  - `ReviewResultPanel` コンポーネント流用
  - レビュータイプ: SEO最適化、ファクトチェック、文章品質
- [x] レビュー結果の永続化と表示
  - MinIO に保存済み（review.json）
  - 一覧でレビューステータス表示

### 2.2 Claude Code編集連携
- [x] Issue作成機能の流用（GitHubActions）
  - 記事詳細ページから編集依頼Issue作成
  - `@claude` メンション付きIssue
- [x] 編集完了通知
  - GitHub Issue/PRのステータス監視（10秒ポーリング）
  - 完了時にPR情報表示

---

## ✅ フェーズ3: PR表示と管理 `cc:DONE`

### 3.1 PR表示
- [x] PR一覧表示
  - サイドバーにオープンPRサマリー表示
  - GitHubタブで詳細なPR一覧（作成者、ブランチ、追加/削除行数）
- [x] 未PRブランチ表示
  - Claude Code編集後のブランチ一覧
  - 比較リンク

### 3.2 PR作成
- [x] ブランチ→PR自動作成（GitHubActionsコンポーネント内）
- ~~マージ自動化~~ （ユーザー要望により除外 - PRまで）

---

## 📊 コンポーネント流用マップ

| 既存コンポーネント | 流用先 | 変更点 |
|------------------|-------|--------|
| `ArtifactViewer` | 記事詳細ページ | 記事向けUIカスタマイズ |
| `GitHubActions` | 記事詳細ページ | PR/マージUI追加 |
| `ReviewResultPanel` | 記事詳細ページ | そのまま流用 |
| `PreviewPage` | 記事プレビュー | ルーティング変更 |
| `HtmlPreview` | 記事プレビュー | そのまま流用 |

---

## 🔧 技術スタック

| 領域 | 技術 |
|------|------|
| API | FastAPI（既存） |
| DB | PostgreSQL（既存） |
| Storage | MinIO（既存） |
| GitHub連携 | GitHubService（既存） |
| FE | Next.js + React（既存） |

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

## 完了状況

✅ **全フェーズ完了** (2026-01-16)

実装した機能:
- 記事一覧API・ページ（検索、フィルタ対応）
- 記事詳細ページ（概要/プレビュー/GitHubタブ）
- Claudeレビュー機能（SEO、ファクトチェック、品質）
- GitHub連携（Issue作成、PR一覧、ブランチ管理）

---

## アーカイブ（詳細な修正計画）

以下のアーカイブには詳細な修正計画が含まれています：

| ファイル | 内容 |
|---------|------|
| `.claude/memory/archive/Plans-2026-01-13-full-review.md` | 全体コードレビュー修正計画（CRITICAL 25件、HIGH 58件、MEDIUM 28件、LOW 8件） |

アーカイブの計画を実行する場合は該当ファイルを参照してください。
