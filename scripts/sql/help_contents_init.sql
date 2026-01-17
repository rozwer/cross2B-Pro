-- ============================================================================
-- help_contents テーブル作成・初期データ投入
-- ============================================================================
-- 実行方法:
--   psql -U seo -d seo_common -f scripts/sql/help_contents_init.sql
-- ============================================================================

-- テーブル作成（IF NOT EXISTS で冪等性を担保）
CREATE TABLE IF NOT EXISTS help_contents (
    id SERIAL PRIMARY KEY,
    help_key VARCHAR(128) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,  -- Markdown対応
    category VARCHAR(64),
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- インデックス作成（IF NOT EXISTS で冪等性を担保）
CREATE INDEX IF NOT EXISTS ix_help_contents_help_key ON help_contents(help_key);
CREATE INDEX IF NOT EXISTS ix_help_contents_category ON help_contents(category);

-- ============================================================================
-- 初期データ投入（ON CONFLICT DO UPDATE で冪等性を担保）
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Category: wizard（ワークフロー作成ウィザード）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'wizard.step1.business',
    '事業情報の入力',
    '## 事業情報とは

ワークフローで生成される記事の基盤となる情報です。

### 入力項目

- **事業名・サービス名**: 記事内で言及される正式名称
- **事業概要**: 何を提供しているか（100〜300文字推奨）
- **強み・特徴**: 競合との差別化ポイント
- **ターゲット市場**: 想定する顧客層

### ポイント

具体的に書くほど、生成される記事の品質が向上します。
曖昧な表現（「良いサービス」など）は避け、数値や具体例を含めてください。',
    'wizard',
    10
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'wizard.step1.target',
    'ターゲット読者',
    '## ターゲット読者の設定

記事を読んでほしい人物像を明確にします。

### 設定項目

- **年齢層**: 20代、30〜40代、シニアなど
- **職業・役職**: 経営者、マーケター、エンジニアなど
- **課題・悩み**: どんな問題を抱えているか
- **検索意図**: なぜこのキーワードで検索するか

### なぜ重要か

ターゲットが明確だと：
- 適切なトーン・語彙で記事が生成される
- 読者のニーズに沿った構成になる
- コンバージョンにつながりやすい

「誰にでも」向けた記事は、結局誰にも刺さりません。',
    'wizard',
    20
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'wizard.step2.keyword',
    'キーワード選定',
    '## キーワード選定

SEO記事の核となるキーワードを設定します。

### 入力方法

1. **メインキーワード**: 記事の主軸となる検索語（必須）
2. **サブキーワード**: 関連する補助的なキーワード（任意）
3. **除外キーワード**: 避けたい表現やNG語（任意）

### 選定のコツ

- 検索ボリュームと競合度のバランスを考慮
- ロングテールキーワードも有効
- ユーザーの検索意図を想像する

### AI提案機能

「キーワード提案」ボタンで、事業情報を基にしたキーワード候補を取得できます。',
    'wizard',
    30
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- Category: workflow（ワークフロー実行）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.overview',
    '全体フロー',
    '## SEO記事生成ワークフロー

全13工程で高品質なSEO記事を自動生成します。

### 工程一覧

| 工程 | 内容 | 所要時間目安 |
|------|------|-------------|
| 0 | キーワード選定・調査 | 1〜2分 |
| 1 | 競合分析 | 2〜3分 |
| 2 | 構成案作成 | 1〜2分 |
| 3A | トーン分析 | 1分 |
| 3B | FAQ抽出 | 1分 |
| 3C | 統計データ収集 | 1分 |
| 4 | 詳細アウトライン | 2〜3分 |
| 5〜10 | 本文執筆（セクション別） | 各1〜2分 |
| 11 | 画像生成（オプション） | 2〜5分 |
| 12 | WordPress形式変換 | 30秒 |

### ステータス

- **実行中**: 工程処理中
- **承認待ち**: 人間の確認が必要
- **完了**: 全工程終了
- **失敗**: エラー発生（再試行可能）',
    'workflow',
    10
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step3',
    '並列分析（3A/3B/3C）',
    '## 並列分析工程

工程3では3つの分析を同時に実行します。

### 3A: トーン分析

競合記事から最適な文体・トーンを分析：
- フォーマル度
- 専門用語の使用頻度
- 読者への呼びかけ方

### 3B: FAQ抽出

想定される質問と回答を生成：
- 検索意図から推測される疑問
- 「よくある質問」セクション用

### 3C: 統計データ収集

記事の信頼性を高めるデータ：
- 業界統計
- 調査結果
- 引用可能な数値

### 並列実行のメリット

3工程を同時処理することで、全体の所要時間を短縮しています。',
    'workflow',
    20
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.approval',
    '承認・却下',
    '## 承認フロー

工程3（並列分析）完了後、人間による確認ステップがあります。

### 承認時の確認ポイント

1. **アウトラインの妥当性**: 構成が論理的か
2. **キーワードの配置**: SEO観点で適切か
3. **ターゲットとの整合**: 想定読者に合っているか

### 操作方法

- **承認**: 次の工程（本文生成）に進む
- **却下**: 理由を入力して差し戻し
- **修正依頼**: 特定の工程のみ再実行

### 却下後の流れ

却下理由を踏まえて、指定工程から再実行されます。
却下履歴は監査ログに記録されます。',
    'workflow',
    30
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- Category: github（GitHub連携）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'github.issue',
    'Issue作成',
    '## GitHub Issue連携

生成した記事に関するIssueを自動作成できます。

### 用途

- 記事のレビュー依頼
- 修正タスクの管理
- 公開スケジュールの追跡

### 作成されるIssue

```
タイトル: [記事] {キーワード} - レビュー依頼
本文:
- 記事概要
- 生成日時
- ワークフローへのリンク
- チェックリスト
```

### 設定

事前にGitHubリポジトリとの連携設定が必要です。
設定画面でリポジトリURLとアクセストークンを登録してください。',
    'github',
    10
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'github.pr',
    'PR管理',
    '## Pull Request管理

記事をMarkdownファイルとしてPRを作成できます。

### 機能

- **自動ブランチ作成**: `article/{keyword}-{date}` 形式
- **ファイル配置**: 指定ディレクトリに記事を追加
- **PR本文生成**: 記事情報を含むテンプレート

### ワークフロー例

1. 記事生成完了
2. 「PRを作成」ボタンをクリック
3. 確認画面でタイトル・本文を編集
4. PRが作成される
5. レビュー後マージ

### 注意事項

- 連携リポジトリへの書き込み権限が必要
- ブランチ保護ルールがある場合、直接マージ不可の場合あり',
    'github',
    20
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- Category: review（レビュー機能）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'review.types',
    'レビュータイプ',
    '## レビュータイプ

生成された記事に対して、複数の観点からレビューを実行できます。

### 利用可能なレビュータイプ

| タイプ | 説明 | 確認ポイント |
|--------|------|-------------|
| **SEO** | 検索最適化 | キーワード密度、メタ情報、構造化 |
| **読みやすさ** | ユーザビリティ | 文章の長さ、専門用語、段落構成 |
| **事実確認** | 正確性 | 統計データ、引用、主張の根拠 |
| **ブランド** | 一貫性 | トーン、メッセージ、表現 |

### 使い方

1. 記事詳細画面で「レビュー」タブを選択
2. 実行したいレビュータイプを選択
3. 「レビュー実行」をクリック
4. 結果を確認し、必要に応じて修正

### 結果の見方

- **スコア**: 0〜100点で評価
- **指摘事項**: 改善が必要な箇所のリスト
- **改善案**: 具体的な修正提案',
    'review',
    10
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ============================================================================
-- 確認用クエリ
-- ============================================================================
-- SELECT help_key, title, category, display_order FROM help_contents ORDER BY category, display_order;
