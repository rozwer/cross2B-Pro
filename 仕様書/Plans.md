# Claudeレビュー＆編集機能

> **作成日**: 2026-01-14
> **目的**: プレビュー画面に Claude による記事レビュー＆編集機能を追加

---

## 概要

- **対象**: 生成された記事の品質チェック（事実確認・SEO・文章品質）
- **方式**: GitHub Issue + @claude メンション → 非同期レビュー
- **出力**: review.json ファイル + Issue コメント

---

## フェーズ1: バックエンド API `cc:完了` (2026-01-14)

### 1.1 レビュー Issue 作成 API `[feature:tdd]` `[feature:security]`

- [x] `POST /api/github/review/{run_id}/{step}` エンドポイント
- [x] レビュープロンプトテンプレート（3観点 + 統合）
- [x] tenant_id 検証
- [x] テスト: `tests/unit/test_github_review.py` (17 passed)

### 1.2 レビュー結果保存 API `[feature:tdd]`

- [x] `POST /api/github/review-result/{run_id}/{step}` エンドポイント
- [x] MinIO 保存: `{tenant_id}/{run_id}/{step}/review.json`
- [x] Issue コメント投稿

### 1.3 レビューステータス取得 API

- [x] `GET /api/github/review-status/{run_id}/{step}` エンドポイント
- [x] ステータス: `pending` | `in_progress` | `completed` | `failed`

---

## フェーズ2: フロントエンド UI `cc:完了` (2026-01-14)

### 2.1 プレビュー画面 `[feature:a11y]`

- [x] レビューボタン追加（全観点 / 観点別ドロップダウン）
- [x] `ReviewResultPanel.tsx` 新規作成
- [x] ポーリングによるステータス更新

### 2.2 編集ボタン配置

- [x] レビュー結果パネル内に編集ボタン追加
- [x] レビュー結果からの編集指示プリセット（クリップボードコピー）

---

## フェーズ3: GitHub 連携 `cc:完了` (2026-01-14)

- [x] `apps/api/services/review_prompts.py` 新規作成
- [x] Issue コメント投稿機能（レビュー結果保存時）

---

## ファイル変更一覧

| ファイル | 変更 |
|----------|------|
| `apps/api/routers/github.py` | レビュー API 追加 |
| `apps/api/services/github.py` | レビューメソッド追加 |
| `apps/api/services/review_prompts.py` | **新規** |
| `apps/ui/src/app/runs/[id]/preview/page.tsx` | ボタン追加 |
| `apps/ui/src/components/review/ReviewResultPanel.tsx` | **新規** |
| `apps/ui/src/lib/api.ts` | API クライアント追加 |

---

## 完了サマリー

すべてのフェーズが完了しました。

**実装内容:**
1. バックエンド: 3つのAPIエンドポイント（レビュー作成/結果保存/ステータス取得）
2. フロントエンド: プレビュー画面にレビューボタンと結果パネル追加
3. GitHub連携: Issueコメント投稿、@claude メンションによる非同期レビュー

**使い方:**
1. プレビュー画面で「Claude でレビュー」ボタンをクリック
2. レビュー種別を選択（総合/ファクトチェック/SEO/文章品質）
3. GitHub Issue が作成され、Claude がレビューを実行
4. 結果はパネルに表示、各問題から編集指示を生成可能
