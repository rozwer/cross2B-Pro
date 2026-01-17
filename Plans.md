# Plans.md

> **最終更新**: 2026-01-17
> **アーカイブ**: 詳細な修正計画は `.claude/memory/archive/Plans-2026-01-13-full-review.md` を参照

---

## 🎯 コンテキストヘルプ機能（?ボタン）

> **目的**: 各ページ・各機能に「?」ボタンを配置し、モーダルでヘルプを表示。DBで管理し将来的に非エンジニアでも更新可能に。

### 概要
- **表示形式**: モーダル/ダイアログ（クリックで開く）
- **コンテンツ管理**: DB（PostgreSQL）で一元管理
- **対象範囲**: 全画面・全主要機能

---

## 🔴 フェーズ1: 基盤構築 `cc:TODO`

### 1.1 DB: ヘルプコンテンツテーブル
- [ ] `help_contents` テーブル作成
  ```sql
  CREATE TABLE help_contents (
    id SERIAL PRIMARY KEY,
    help_key VARCHAR(128) UNIQUE NOT NULL,  -- 例: "wizard.step1.business"
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,                   -- Markdown対応
    category VARCHAR(64),                    -- ページカテゴリ
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
  );
  ```
- [ ] SQLAlchemy モデル追加 (`apps/api/db/models.py`)
- [ ] 初期データ投入用 SQL/スクリプト作成

### 1.2 API: ヘルプコンテンツ取得
- [ ] `GET /api/help/{help_key}` - 単一ヘルプ取得
- [ ] `GET /api/help?category={category}` - カテゴリ別一覧取得
- [ ] `PUT /api/help/{help_key}` - ヘルプ更新（将来の管理画面用）

### 1.3 FE: 共通コンポーネント
- [ ] `HelpButton` コンポーネント作成
  - `?` アイコンボタン（lucide-react の `HelpCircle`）
  - クリックでモーダル表示
  - props: `helpKey: string`
- [ ] `HelpModal` コンポーネント作成
  - 既存の `ConfirmDialog` パターンを流用
  - Markdown レンダリング対応
  - 閉じるボタン（×）のみ（確認ボタンなし）

---

## 🟡 フェーズ2: ワークフロー作成ウィザード `cc:TODO`

### 2.1 Step1: 事業情報入力
- [ ] `wizard.step1.business` - 事業内容の入力ガイド
- [ ] `wizard.step1.target` - ターゲット読者の設定方法
- [ ] `wizard.step1.strategy` - 記事戦略（標準/トピッククラスター）の違い

### 2.2 Step2: キーワード選定
- [ ] `wizard.step2.keyword` - メインキーワードの選び方
- [ ] `wizard.step2.related` - 関連キーワードの活用法
- [ ] `wizard.step2.volume` - 検索ボリュームの見方

### 2.3 Step3: 戦略設定
- [ ] `wizard.step3.type` - 記事タイプ（網羅/深掘り/比較等）の選択基準
- [ ] `wizard.step3.cta` - CTAの設定方法

### 2.4 Step4-6: 詳細設定
- [ ] `wizard.step4.wordcount` - 文字数設定の目安
- [ ] `wizard.step5.cta` - CTA詳細設定
- [ ] `wizard.step6.confirm` - 確認画面の見方

---

## 🟢 フェーズ3: ワークフロー実行画面 `cc:TODO`

### 3.1 工程説明
- [ ] `workflow.overview` - 全体フローの概要（工程0〜12）
- [ ] `workflow.step0` - キーワード選定（工程0）
- [ ] `workflow.step1` - 競合記事収集（工程1）
- [ ] `workflow.step2` - CSV読み込み確認（工程2）
- [ ] `workflow.step3` - 並列分析（3A/3B/3C）の意味
- [ ] `workflow.step4-6` - アウトライン生成フロー
- [ ] `workflow.step7` - 本文生成
- [ ] `workflow.step8-9` - ファクトチェック・品質向上
- [ ] `workflow.step10` - 最終出力
- [ ] `workflow.step11` - 画像生成
- [ ] `workflow.step12` - WordPress HTML

### 3.2 操作ガイド
- [ ] `workflow.approval` - 承認・却下の操作方法
- [ ] `workflow.retry` - 工程再実行の方法
- [ ] `workflow.artifacts` - 成果物の確認方法

---

## 🔵 フェーズ4: 画像生成ウィザード `cc:TODO`

### 4.1 各フェーズ説明
- [ ] `image.settings` - 画像設定（スタイル、枚数）
- [ ] `image.positions` - 挿入位置の選び方
- [ ] `image.instructions` - 画像指示の書き方
- [ ] `image.review` - 生成画像の確認・リトライ
- [ ] `image.preview` - プレビューの見方

---

## 🟣 フェーズ5: 記事管理・レビュー `cc:TODO`

### 5.1 記事一覧
- [ ] `articles.list` - 一覧画面の使い方
- [ ] `articles.filter` - 検索・フィルタの活用
- [ ] `articles.status` - レビューステータスの意味

### 5.2 レビュー機能
- [ ] `review.types` - レビュータイプ（SEO/ファクトチェック/品質）の違い
- [ ] `review.results` - レビュー結果の読み方
- [ ] `review.action` - レビュー後のアクション

### 5.3 GitHub連携
- [ ] `github.issue` - Issue作成の使い方
- [ ] `github.pr` - PR一覧の見方
- [ ] `github.branch` - ブランチ操作

---

## ⚪ フェーズ6: 設定画面 `cc:TODO`

### 6.1 API設定
- [ ] `settings.apikeys` - APIキー設定方法
- [ ] `settings.models` - モデル選択の基準

### 6.2 プロンプト管理
- [ ] `settings.prompts` - プロンプト編集の注意点

---

## 📊 ヘルプコンテンツ一覧（予定）

| カテゴリ | 件数 | 優先度 |
|---------|------|--------|
| ワークフロー作成 | 12件 | 高 |
| ワークフロー実行 | 15件 | 高 |
| 画像生成 | 5件 | 中 |
| 記事管理・レビュー | 9件 | 中 |
| 設定 | 4件 | 低 |
| **合計** | **45件** | - |

---

## 🔧 技術スタック

| 領域 | 技術 |
|------|------|
| DB | PostgreSQL（`help_contents` テーブル） |
| API | FastAPI |
| FE | React + lucide-react（HelpCircle アイコン）|
| Markdown | react-markdown または既存の MarkdownViewer |

---ka