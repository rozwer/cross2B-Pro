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

-- ----------------------------------------------------------------------------
-- Category: wizard（追加分）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'wizard.step1.strategy',
    '記事戦略の選択',
    '## 記事戦略

生成する記事の全体戦略を選択します。

### 標準（単一記事）

- 1つのキーワードに対して1記事を生成
- シンプルなSEO記事に最適
- 初めての方におすすめ

### トピッククラスター

- メインキーワードを中心に、関連記事群を設計
- 内部リンク構造を自動生成
- 中〜大規模なコンテンツ戦略向け

### 選択の基準

| 状況 | 推奨戦略 |
|------|----------|
| 単発の記事が必要 | 標準 |
| サイト全体のSEOを強化したい | トピッククラスター |
| 特定テーマで権威性を確立したい | トピッククラスター |
| 試しに使ってみたい | 標準 |

### 注意点

トピッククラスターは複数記事を生成するため、処理時間とコストが増加します。',
    'wizard',
    15
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'wizard.step2.related',
    '関連キーワードの活用',
    '## 関連キーワード

メインキーワードと一緒に使用する関連語句です。

### 関連キーワードの種類

- **共起語**: メインキーワードと一緒に検索されやすい語
- **類義語**: 同じ意味を持つ別の表現
- **派生語**: メインキーワードから派生した語句
- **ロングテール**: より具体的な検索フレーズ

### 設定方法

1. 「関連キーワードを追加」をクリック
2. キーワードを入力（カンマ区切りで複数可）
3. AI提案機能も活用可能

### 活用のコツ

- 5〜10個程度が目安
- 無理に詰め込まない（自然な文章が優先）
- 検索意図が異なるものは避ける

### 記事への反映

関連キーワードは本文中に自然な形で組み込まれます。
無理な詰め込みはせず、読みやすさを優先します。',
    'wizard',
    35
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'wizard.step2.volume',
    '検索ボリュームの見方',
    '## 検索ボリューム

キーワードが月間でどれくらい検索されているかの指標です。

### ボリュームの目安

| ボリューム | 評価 | 特徴 |
|-----------|------|------|
| 10,000以上 | 高 | 競合が激しい、上位表示が難しい |
| 1,000〜10,000 | 中 | バランスが良い、狙い目 |
| 100〜1,000 | 低〜中 | ロングテール、コンバージョン率高め |
| 100未満 | 低 | ニッチ、特定ニーズ向け |

### 注意点

- ボリュームだけで判断しない
- 競合度も合わせて確認
- ビジネスとの関連性を重視

### トレンドの確認

検索ボリュームは季節や時事によって変動します。
表示されるデータは過去12ヶ月の平均値です。

### 推奨する選び方

- 最初は中〜低ボリュームから始める
- 実績を積んでから高ボリュームに挑戦
- ニッチキーワードの積み重ねも有効',
    'wizard',
    40
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'wizard.step3.type',
    '記事タイプの選択',
    '## 記事タイプ

生成する記事の形式・構成パターンを選択します。

### 利用可能なタイプ

| タイプ | 特徴 | 適したケース |
|--------|------|-------------|
| **網羅型** | トピックを幅広くカバー | 初心者向け解説、入門記事 |
| **深掘り型** | 特定テーマを詳細に解説 | 専門家向け、技術記事 |
| **比較型** | 複数の選択肢を比較 | 製品比較、サービス選び |
| **ハウツー型** | 手順を順序立てて説明 | 操作ガイド、チュートリアル |
| **リスト型** | 箇条書き中心の構成 | まとめ記事、ランキング |

### 選択のポイント

- 検索意図に合わせる
- ターゲット読者の期待を考える
- 競合記事のタイプも参考に

### 複合タイプ

必要に応じて、複数のタイプを組み合わせることも可能です。
例：「網羅型＋ハウツー型」で広く解説しつつ実践的な内容も含める',
    'wizard',
    50
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'wizard.step3.cta',
    'CTAの基本設定',
    '## CTA（Call To Action）

読者に取ってほしい行動を促す要素です。

### CTAの役割

- 記事の目的を達成する
- コンバージョンにつなげる
- 読者の次のステップを案内

### 基本設定項目

| 項目 | 説明 | 例 |
|------|------|-----|
| **CTAタイプ** | 誘導先の種類 | 資料請求、問い合わせ、購入 |
| **配置位置** | 記事内の場所 | 末尾、中間、複数箇所 |
| **優先度** | 強調の度合い | 高・中・低 |

### 設定のコツ

- 記事の内容と関連性のあるCTAを設定
- 押しつけがましくならないよう注意
- 1記事に1〜2種類が目安

### スキップする場合

情報提供のみが目的の記事では、CTAを設定しなくても構いません。',
    'wizard',
    55
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'wizard.step4.wordcount',
    '文字数設定の目安',
    '## 文字数設定

生成する記事の目標文字数を設定します。

### 推奨文字数

| 記事タイプ | 推奨文字数 | 理由 |
|-----------|-----------|------|
| ブログ記事 | 2,000〜4,000字 | 読みやすさとSEOのバランス |
| 詳細解説 | 5,000〜8,000字 | 網羅性を重視 |
| ランディングページ | 1,000〜2,000字 | 簡潔さ重視 |
| 技術記事 | 3,000〜6,000字 | 実用性を確保 |

### 文字数の考え方

- **多ければ良いわけではない**: 冗長な記事は読者離脱の原因
- **キーワードによる**: 競合記事の文字数も参考に
- **読者ニーズ**: 深い情報が必要なら長めに

### 設定範囲

- 最小: 1,000字
- 最大: 15,000字
- 推奨: 3,000〜5,000字

### 実際の生成結果

設定値は目安であり、±20%程度の変動があります。
内容の充実度を優先するため、厳密に一致しない場合があります。',
    'wizard',
    60
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'wizard.step5.cta',
    'CTA詳細設定',
    '## CTA詳細設定

より具体的なCTAの内容を設定します。

### 設定項目

#### CTAテキスト
ボタンやリンクに表示する文言
- 例：「無料で資料をダウンロード」「今すぐ相談する」
- アクションを明確に伝える動詞を使用

#### リンク先URL
CTAクリック時の遷移先
- ランディングページ
- 問い合わせフォーム
- 製品ページ

#### 訴求ポイント
CTAの前後に配置する説得文
- 限定性：「今だけ」「先着100名」
- 価値：「無料」「特典付き」
- 安心感：「1分で完了」「しつこい営業なし」

### CTA配置パターン

| パターン | 配置 | 効果 |
|---------|------|------|
| 末尾のみ | 記事最後 | 自然、押しつけ感なし |
| 複数配置 | 中間+末尾 | 機会増加 |
| サイドバー | 常時表示 | 視認性高い |

### 注意点

- 記事内容との整合性を保つ
- 誇大表現は避ける
- モバイル表示も考慮',
    'wizard',
    70
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'wizard.step6.confirm',
    '確認画面の見方',
    '## 確認画面

ワークフロー開始前の最終確認画面です。

### 表示される情報

#### 基本情報
- 事業情報サマリー
- ターゲット読者
- キーワード（メイン・関連）

#### 記事設定
- 記事タイプ
- 目標文字数
- 記事戦略

#### CTA設定
- CTAタイプ
- テキスト・リンク先

#### 見積もり
- 予想所要時間
- 推定コスト（API使用量）

### 確認のポイント

1. **キーワードの誤字脱字がないか**
2. **事業情報が正確か**
3. **設定値が意図通りか**

### 修正が必要な場合

各セクションの「編集」ボタンで該当ステップに戻れます。
「戻る」ボタンで1つ前のステップにも移動できます。

### 開始後の変更

ワークフロー開始後は設定変更できません。
変更が必要な場合は、新しいワークフローを作成してください。',
    'wizard',
    80
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- Category: workflow（追加分）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step0',
    '工程0: キーワード選定',
    '## 工程0: キーワード選定

ワークフローの最初の工程で、キーワードの詳細分析を行います。

### 処理内容

1. **検索意図の分析**
   - Informational（情報収集）
   - Navigational（特定サイトへ移動）
   - Commercial（比較検討）
   - Transactional（購入・申込）

2. **関連キーワードの拡張**
   - 共起語の抽出
   - サジェストキーワードの収集
   - 関連質問の特定

3. **キーワードマップ作成**
   - メインキーワードと派生語の関係図
   - 記事構成の基礎データ

### 所要時間

約1〜2分

### 出力

- キーワード分析レポート
- 推奨構成案の素案

### エラーが発生した場合

キーワードが不明瞭な場合、エラーとなることがあります。
より具体的なキーワードを設定して再試行してください。',
    'workflow',
    5
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step1',
    '工程1: 競合記事収集',
    '## 工程1: 競合記事収集

検索上位の競合記事を分析します。

### 処理内容

1. **検索結果の取得**
   - 上位10〜20記事を収集
   - タイトル、URL、メタ情報を抽出

2. **コンテンツ分析**
   - 見出し構造（H1〜H4）
   - 文字数・段落数
   - 使用キーワード

3. **ギャップ分析**
   - 競合にあって自社にない要素
   - 差別化ポイントの特定

### 所要時間

約2〜3分

### 出力

- 競合分析レポート
- 上位記事の見出し一覧
- 推奨される差別化ポイント

### 注意点

- 外部サイトへのアクセスが発生します
- 一部サイトはアクセス制限により取得できない場合があります
- 取得できなかった記事は分析対象から除外されます',
    'workflow',
    15
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step2',
    '工程2: CSV読み込み確認',
    '## 工程2: CSV読み込み・構成案作成

競合分析結果を整理し、記事の構成案を作成します。

### 処理内容

1. **データ整理**
   - 競合記事データの正規化
   - 重複・不要データの除去
   - 品質スコアリング

2. **構成案作成**
   - 見出し構造の設計
   - セクション配分の決定
   - キーワード配置計画

3. **カスタマイズ適用**
   - 事業情報の反映
   - ターゲット読者への最適化
   - 記事タイプに応じた調整

### 所要時間

約1〜2分

### 出力

- 整理済み競合データ（CSV形式）
- 記事構成案（見出しリスト）
- 各セクションの概要説明

### 次工程への引き継ぎ

この工程の出力が、並列分析工程（3A/3B/3C）の入力となります。',
    'workflow',
    18
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step4-6',
    '工程4-6: アウトライン生成',
    '## 工程4-6: アウトライン生成フロー

並列分析（3A/3B/3C）の結果を統合し、詳細なアウトラインを作成します。

### 工程4: 統合アウトライン

並列分析の結果を1つの構成案に統合：
- トーン設定の反映
- FAQ要素の組み込み
- 統計データの配置計画

### 工程5: 詳細化

各セクションの詳細を決定：
- 小見出しの追加
- 段落構成の設計
- 引用・事例の配置

### 工程6: 最終調整

SEO最適化と読みやすさの調整：
- キーワード密度の確認
- 見出し階層の最適化
- 文字数配分の微調整

### 承認ポイント

工程3完了後に承認が必要です。
アウトラインを確認し、問題なければ承認してください。

### 修正が必要な場合

却下して、修正理由を記入してください。
指定工程から再実行されます。',
    'workflow',
    40
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step7',
    '工程7: 本文生成',
    '## 工程7: 本文生成

アウトラインに基づいて、記事本文を生成します。

### 処理内容

1. **セクション別生成**
   - 各見出しに対応する本文を作成
   - 前後の文脈を考慮した一貫性確保
   - 指定トーンでの文章生成

2. **要素の組み込み**
   - FAQ（質問と回答）
   - 統計データと出典
   - 事例・具体例

3. **構造化**
   - 段落分け
   - リスト・表の作成
   - 強調・引用の適用

### 所要時間

文字数により変動（3,000字で約2〜3分）

### 出力

- 完成度の高い記事本文
- Markdown形式で構造化
- メタ情報（タイトル、description）

### 品質チェック

生成された本文は次工程でファクトチェック・品質向上が行われます。
この時点では下書き品質とお考えください。',
    'workflow',
    50
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step8-9',
    '工程8-9: ファクトチェック・品質向上',
    '## 工程8-9: ファクトチェック・品質向上

生成された本文の品質を検証・向上させます。

### 工程8: ファクトチェック

事実確認と信頼性の検証：

| チェック項目 | 内容 |
|-------------|------|
| 統計データ | 出典の確認、数値の妥当性 |
| 主張 | 根拠の有無、論理の整合性 |
| 固有名詞 | 正式名称、スペルミス |
| 日付・期間 | 時制の適切性 |

### 工程9: 品質向上

文章品質の改善：

- **可読性向上**: 長文の分割、難解な表現の平易化
- **SEO最適化**: キーワード密度、内部リンク
- **エンゲージメント**: 導入文の改善、結論の強化
- **一貫性**: トーン・表現の統一

### 所要時間

各工程約1〜2分

### 出力

- 検証済み記事本文
- ファクトチェックレポート
- 改善箇所のハイライト

### 問題が見つかった場合

自動修正可能なものは修正されます。
重大な問題は警告として表示されます。',
    'workflow',
    60
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step10',
    '工程10: 最終出力',
    '## 工程10: 最終出力

品質向上済みの記事を最終形式で出力します。

### 処理内容

1. **最終整形**
   - Markdown形式の最終調整
   - 見出し番号の正規化
   - 空白・改行の整理

2. **メタ情報生成**
   - SEOタイトル（60文字以内）
   - メタディスクリプション（120文字以内）
   - OGP情報

3. **品質スコア算出**
   - 総合スコア
   - 各観点別スコア（SEO、可読性、独自性）

### 所要時間

約30秒〜1分

### 出力形式

- **Markdown**: 記事本文
- **JSON**: メタ情報・スコア
- **HTML**: プレビュー用

### 次のステップ

この後、画像生成（工程11）またはWordPress形式変換（工程12）に進みます。
画像生成をスキップすることも可能です。

### ダウンロード

この時点で記事をダウンロードできます。
形式：Markdown / HTML / JSON',
    'workflow',
    70
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step11',
    '工程11: 画像生成',
    '## 工程11: 画像生成

記事に挿入する画像をAIで生成します（オプション）。

### 概要

- 記事内容に基づいた画像を自動生成
- 挿入位置を指定可能
- 複数の画像スタイルから選択

### 処理フロー

1. **設定確認**: 画像枚数・スタイルを指定
2. **位置提案**: AIが最適な挿入位置を提案
3. **指示入力**: 各画像の生成指示を編集
4. **生成実行**: 画像を生成
5. **レビュー**: 結果を確認、必要に応じて再生成
6. **統合**: 記事に画像を組み込み

### 所要時間

画像1枚あたり約30秒〜1分

### スキップする場合

「画像生成をスキップ」を選択すると、工程12に直接進みます。
後から画像を追加したい場合は、再度工程11を実行できます。

### 詳細設定

詳しくは「画像生成」カテゴリのヘルプを参照してください。',
    'workflow',
    80
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step12',
    '工程12: WordPress HTML',
    '## 工程12: WordPress形式変換

記事をWordPressに投稿可能なHTML形式に変換します。

### 処理内容

1. **HTML変換**
   - Markdown → HTML
   - WordPress互換の構造
   - クラス・ID付与

2. **画像処理**
   - img タグの生成
   - alt 属性の設定
   - キャプション追加

3. **SEO要素**
   - 構造化データ（JSON-LD）
   - Open Graph タグ
   - Twitter Card

### 出力形式

```html
<!-- 記事本文 -->
<article class="seo-article">
  <h1>タイトル</h1>
  <p>本文...</p>
</article>

<!-- メタ情報 -->
<script type="application/ld+json">
  {...}
</script>
```

### ダウンロード

- **HTMLファイル**: そのままWordPressに貼り付け可能
- **画像ファイル**: 別途アップロード用

### 注意事項

- テーマによってはスタイルの調整が必要
- 画像URLは相対パスで出力されます
- カスタムフィールドは手動設定が必要',
    'workflow',
    90
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.retry',
    '工程の再実行',
    '## 工程の再実行

特定の工程のみを再実行する方法です。

### 再実行が必要なケース

- エラーで工程が失敗した
- 出力内容に不満がある
- 設定を変更して再生成したい

### 再実行方法

1. ワークフロー詳細画面を開く
2. 再実行したい工程をクリック
3. 「再実行」ボタンを押す
4. 確認ダイアログで「実行」を選択

### 再実行の範囲

| オプション | 説明 |
|-----------|------|
| この工程のみ | 選択した工程だけ再実行 |
| この工程以降 | 選択した工程から最後まで |

### 注意事項

- 再実行すると、その工程の以前の出力は上書きされます
- 依存関係のある工程は連鎖して再実行されることがあります
- 再実行履歴は監査ログに記録されます

### 再実行できない工程

- 承認済みの工程（承認を取り消す必要あり）
- 現在実行中の工程

### コストについて

再実行にはAPIコストが発生します。
コストは通常実行時と同等です。',
    'workflow',
    100
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.artifacts',
    '成果物の確認方法',
    '## 成果物の確認

各工程で生成された成果物（アーティファクト）の確認方法です。

### 成果物の種類

| 工程 | 成果物 | 形式 |
|------|--------|------|
| 工程0 | キーワード分析 | JSON |
| 工程1 | 競合分析 | JSON/CSV |
| 工程2 | 構成案 | Markdown |
| 工程3A | トーン分析 | JSON |
| 工程3B | FAQ | JSON |
| 工程3C | 統計データ | JSON |
| 工程4-6 | アウトライン | Markdown |
| 工程7 | 記事本文 | Markdown |
| 工程10 | 最終記事 | Markdown/HTML |
| 工程11 | 画像 | PNG/JPG |
| 工程12 | WordPress HTML | HTML |

### 確認方法

1. **ワークフロー詳細画面**で工程をクリック
2. **「成果物」タブ**を選択
3. プレビューまたはダウンロード

### プレビュー機能

- Markdown: レンダリング表示
- JSON: シンタックスハイライト
- 画像: サムネイル表示
- HTML: ブラウザプレビュー

### ダウンロード

- 個別ダウンロード: 各成果物の「DL」ボタン
- 一括ダウンロード: 「全てダウンロード」（ZIP形式）

### 保存期間

成果物は30日間保存されます。
必要な場合は早めにダウンロードしてください。',
    'workflow',
    110
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- Category: image（画像生成）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'image.settings',
    '画像設定',
    '## 画像設定

生成する画像の基本設定を行います。

### 設定項目

#### 画像枚数
- 最小: 1枚
- 最大: 10枚
- 推奨: 3〜5枚（記事3,000字あたり）

#### 画像スタイル

| スタイル | 特徴 | 適したケース |
|---------|------|-------------|
| **写真風** | リアルな写真のような画像 | ビジネス記事、事例紹介 |
| **イラスト** | 手描き風のイラスト | 親しみやすい解説記事 |
| **インフォグラフィック** | 図解・データ可視化 | 比較記事、統計解説 |
| **アイコン風** | シンプルなアイコン | 手順説明、リスト記事 |
| **抽象的** | 概念を表す抽象画像 | コンセプト説明 |

#### サイズ

- **横長（16:9）**: アイキャッチ、本文内
- **正方形（1:1）**: SNSシェア用
- **縦長（9:16）**: スマホ向け

### ブランドカラー

指定した色を画像に反映できます。
HEXコード（#FFFFFF形式）で入力してください。',
    'image',
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
    'image.positions',
    '挿入位置の選び方',
    '## 画像挿入位置

記事内のどこに画像を配置するかを決定します。

### AI提案機能

「位置を提案」ボタンで、AIが最適な挿入位置を提案します：
- 見出しの直後
- 概念説明の箇所
- データ・統計の箇所
- 手順の区切り

### 手動選択

記事プレビューで任意の位置をクリックして追加できます。

### 推奨配置

| 位置 | 効果 | 推奨度 |
|------|------|--------|
| アイキャッチ | 第一印象、SNSシェア | ★★★ |
| 導入部後 | 読者の関心維持 | ★★★ |
| 各H2見出し後 | セクション区切り | ★★☆ |
| 手順の合間 | 理解促進 | ★★☆ |
| 結論前 | 印象付け | ★☆☆ |

### 注意点

- 画像が多すぎると読み込み速度に影響
- 文脈に合った位置を選ぶ
- モバイル表示も考慮

### 位置の変更

ドラッグ&ドロップで位置を変更できます。
削除は画像横の「×」ボタンで行えます。',
    'image',
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
    'image.instructions',
    '画像指示の書き方',
    '## 画像生成指示

各画像に対して、生成AIへの指示を編集できます。

### 基本構成

```
[被写体] + [状況・動作] + [スタイル・雰囲気]
```

### 良い指示の例

```
✅ 「オフィスでノートPCを使って仕事をしている30代のビジネスマン、
    明るい自然光、プロフェッショナルな雰囲気」

✅ 「データ分析を示す棒グラフと円グラフ、
    青と緑を基調としたモダンなインフォグラフィック」

✅ 「スマートフォンを操作する手元のクローズアップ、
    白い背景、ミニマルなスタイル」
```

### 避けるべき指示

```
❌ 「いい感じの画像」（曖昧すぎる）
❌ 「〇〇社の製品写真」（著作権の問題）
❌ 「有名人の顔」（肖像権の問題）
```

### 指示のコツ

1. **具体的に**: 抽象的な表現は避ける
2. **視覚的に**: 見た目を詳細に描写
3. **一貫性**: ブランドトーンを維持

### AIの自動補完

空欄の場合、記事内容から自動生成されます。
編集で微調整することを推奨します。',
    'image',
    30
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'image.review',
    '生成画像の確認・リトライ',
    '## 画像のレビュー

生成された画像を確認し、必要に応じて再生成します。

### 確認画面

各画像について以下が表示されます：
- サムネイル画像
- 生成に使用した指示
- 生成日時

### 評価オプション

| 操作 | 説明 |
|------|------|
| **承認** | この画像を採用 |
| **リトライ** | 同じ指示で再生成 |
| **指示変更** | 指示を編集して再生成 |
| **削除** | この画像を使用しない |

### リトライのコツ

同じ指示でも結果は毎回異なります。
気に入らない場合は2〜3回リトライしてみてください。

### 指示変更時のポイント

- 何が気に入らないか明確にする
- 「〜ではなく〜」形式で伝える
- 例：「暗すぎる」→「明るい照明で、白を基調とした背景」

### 一括操作

- 「全て承認」: 全画像を採用
- 「全てリトライ」: 全画像を再生成

### コストについて

リトライ1回につき、1画像分のコストが発生します。',
    'image',
    40
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'image.preview',
    'プレビューの見方',
    '## 画像プレビュー

画像を記事に統合した状態をプレビューで確認できます。

### プレビュー画面

- 記事本文と画像の統合表示
- 実際のWebページに近い見た目
- デスクトップ/モバイル切り替え

### 確認ポイント

1. **配置のバランス**
   - 画像が偏っていないか
   - テキストとのバランス

2. **サイズ感**
   - 大きすぎ/小さすぎないか
   - 画面幅に対する比率

3. **文脈との整合**
   - 前後のテキストと関連しているか
   - 説明として適切か

4. **読み込み体験**
   - スクロール時の画像出現タイミング
   - ページ全体の重さ

### 表示モード

| モード | 説明 |
|--------|------|
| デスクトップ | PC表示（幅1200px） |
| タブレット | タブレット表示（幅768px） |
| モバイル | スマホ表示（幅375px） |

### 問題がある場合

- 位置変更: ドラッグ&ドロップ
- 画像変更: 該当画像の「編集」
- 削除: 該当画像の「×」

### 確定

プレビューで問題なければ「統合を確定」で次に進みます。',
    'image',
    50
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- Category: articles（記事管理）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'articles.list',
    '一覧画面の使い方',
    '## 記事一覧画面

生成された記事の一覧を管理する画面です。

### 表示情報

| カラム | 説明 |
|--------|------|
| タイトル | 記事のSEOタイトル |
| キーワード | メインキーワード |
| ステータス | 生成状況（実行中/完了/失敗） |
| レビュー | レビュー状態（未/済/要修正） |
| 作成日 | ワークフロー開始日時 |
| 更新日 | 最終更新日時 |

### ソート

各カラムのヘッダーをクリックでソート：
- 1回クリック: 昇順
- 2回クリック: 降順
- 3回クリック: ソート解除

### 行の操作

- **クリック**: 詳細画面を開く
- **右クリック**: コンテキストメニュー
  - プレビュー
  - ダウンロード
  - 削除

### ページネーション

- デフォルト: 1ページ20件
- 表示件数変更: 20/50/100件から選択

### キーボードショートカット

- `↑/↓`: 行の選択
- `Enter`: 詳細を開く
- `Delete`: 削除（確認あり）',
    'articles',
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
    'articles.filter',
    '検索・フィルタの活用',
    '## 検索・フィルタ機能

大量の記事から目的の記事を素早く見つける方法です。

### キーワード検索

検索ボックスに入力すると、以下を対象に検索：
- タイトル
- キーワード
- 事業名

### フィルタ項目

#### ステータス
- 実行中
- 承認待ち
- 完了
- 失敗

#### レビュー状態
- 未レビュー
- レビュー済み
- 要修正

#### 期間
- 今日
- 過去7日
- 過去30日
- カスタム範囲

#### 記事タイプ
- 網羅型
- 深掘り型
- 比較型
- その他

### 複合フィルタ

複数のフィルタを組み合わせ可能：
例：「完了」かつ「未レビュー」かつ「過去7日」

### フィルタの保存

よく使うフィルタ条件を保存できます：
1. フィルタを設定
2. 「フィルタを保存」をクリック
3. 名前を付けて保存
4. 次回から1クリックで適用

### フィルタのクリア

「クリア」ボタンで全フィルタを解除します。',
    'articles',
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
    'articles.status',
    'レビューステータスの意味',
    '## レビューステータス

記事のレビュー状況を示すステータスです。

### ステータス一覧

| ステータス | 意味 | 次のアクション |
|-----------|------|---------------|
| **未レビュー** | レビュー未実施 | レビューを実行 |
| **レビュー中** | レビュー処理中 | 完了を待つ |
| **レビュー済み** | 問題なし | 公開準備へ |
| **要修正** | 指摘事項あり | 修正を実施 |
| **修正済み** | 修正完了 | 再レビューへ |

### ステータスの遷移

```
未レビュー → レビュー中 → レビュー済み → 公開準備
                    ↓
                 要修正 → 修正済み → 再レビュー
```

### 「要修正」の場合

1. 指摘事項を確認
2. 記事を編集または工程を再実行
3. ステータスを「修正済み」に変更
4. 再度レビューを実行

### 自動ステータス更新

- レビュー実行時: 自動で「レビュー中」に
- レビュー完了時: 結果に応じて自動設定
- 工程再実行時: 「未レビュー」にリセット

### 手動ステータス変更

詳細画面の「ステータス変更」から手動変更も可能です。
変更履歴は監査ログに記録されます。',
    'articles',
    30
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- Category: review（追加分）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'review.results',
    'レビュー結果の読み方',
    '## レビュー結果の読み方

レビュー実行後の結果画面の見方です。

### 総合スコア

0〜100点で記事の品質を評価：

| スコア | 評価 | 推奨アクション |
|--------|------|---------------|
| 90〜100 | 優秀 | そのまま公開可 |
| 70〜89 | 良好 | 軽微な修正推奨 |
| 50〜69 | 要改善 | 指摘箇所の修正必要 |
| 50未満 | 要大幅修正 | 再生成を検討 |

### 観点別スコア

各レビュータイプごとのスコア：
- SEOスコア
- 可読性スコア
- 正確性スコア
- 一貫性スコア

### 指摘事項リスト

| 重要度 | 表示 | 意味 |
|--------|------|------|
| Critical | 🔴 | 必ず修正が必要 |
| Warning | 🟡 | 修正を推奨 |
| Info | 🔵 | 参考情報 |

### 指摘の詳細

各指摘をクリックすると：
- 該当箇所のハイライト
- 問題の説明
- 改善案の提示

### 履歴の確認

過去のレビュー結果を比較できます。
「履歴」タブで以前の結果を参照してください。',
    'review',
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
    'review.action',
    'レビュー後のアクション',
    '## レビュー後のアクション

レビュー結果に基づいて取るべき行動です。

### 問題なしの場合

1. **ステータス確認**: 「レビュー済み」になっているか
2. **最終確認**: プレビューで全体を確認
3. **公開準備**: ダウンロードまたはGitHub PR作成

### 修正が必要な場合

#### 軽微な修正（スコア70以上）

1. 指摘箇所を確認
2. 「編集」モードで直接修正
3. 保存して再レビュー

#### 大幅な修正（スコア70未満）

1. 指摘の傾向を分析
2. 問題の根本原因を特定
3. 該当工程を再実行

### 工程再実行の判断

| 指摘内容 | 再実行する工程 |
|---------|---------------|
| 構成の問題 | 工程4-6（アウトライン） |
| トーンの問題 | 工程3A（トーン分析） |
| 事実誤り | 工程8（ファクトチェック） |
| SEOの問題 | 工程9（品質向上） |

### レビュー結果の活用

- 頻出する指摘は設定の見直しを検討
- 同じキーワードで複数記事を作る際の参考に
- チームで共有して品質基準の統一に活用

### 再レビュー

修正後は必ず再レビューを実行してください。
同じ観点で改善されているか確認します。',
    'review',
    30
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- Category: github（追加分）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'github.branch',
    'ブランチ操作',
    '## ブランチ操作

記事をGitHubで管理する際のブランチ操作です。

### 自動ブランチ命名

記事作成時、自動でブランチが作成されます：

```
article/{keyword}-{YYYYMMDD}
例: article/seo-tools-20250115
```

### 命名ルール

- 日本語キーワードはローマ字変換
- スペースはハイフンに変換
- 特殊文字は除去
- 最大50文字

### 手動でブランチ名を変更

1. PR作成画面で「詳細設定」を開く
2. 「ブランチ名」フィールドを編集
3. 保存

### ブランチの状態

| 状態 | 説明 |
|------|------|
| 作成済み | ブランチ作成完了 |
| プッシュ済み | リモートに反映済み |
| PRオープン | PR作成済み |
| マージ済み | mainに統合完了 |

### ブランチ保護との関係

リポジトリにブランチ保護ルールがある場合：
- 直接pushができない場合があります
- PR経由でのマージが必要です
- CIが必須の場合は通過を待ちます

### ブランチの削除

マージ後、不要になったブランチは：
- PR画面から「ブランチを削除」
- または設定で自動削除を有効化

### 注意事項

- 同名ブランチが存在する場合はエラーになります
- 日付でユニーク性を確保していますが、同日複数作成時は連番が付きます',
    'github',
    30
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- Category: settings（設定）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'settings.apikeys',
    'APIキー設定',
    '## APIキー設定

各種AIサービスのAPIキーを設定します。

### 必要なAPIキー

| サービス | 用途 | 必須 |
|---------|------|------|
| **Gemini** | 記事生成（メイン） | ○ |
| **OpenAI** | 記事生成（代替） | △ |
| **Anthropic** | 記事生成（代替） | △ |
| **画像生成API** | 画像生成 | △ |

※ 少なくとも1つの記事生成用APIキーが必要

### 設定方法

1. 設定画面で「APIキー」タブを開く
2. 対象サービスの「編集」をクリック
3. APIキーを入力
4. 「保存」をクリック
5. 接続テストで確認

### APIキーの取得

各サービスの公式サイトで取得：
- [Google AI Studio](https://makersuite.google.com/app/apikey)
- [OpenAI Platform](https://platform.openai.com/api-keys)
- [Anthropic Console](https://console.anthropic.com/)

### セキュリティ

- APIキーは暗号化して保存されます
- 画面には一部のみ表示（`sk-***...***`）
- 削除は即時反映されます

### トラブルシューティング

| エラー | 原因 | 対処 |
|--------|------|------|
| Invalid API Key | キーが無効 | 再発行して入力し直す |
| Rate Limit | 制限超過 | 時間をおいて再試行 |
| Quota Exceeded | 使用量超過 | プランをアップグレード |',
    'settings',
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
    'settings.models',
    'モデル選択の基準',
    '## モデル選択

記事生成に使用するAIモデルを選択します。

### 利用可能なモデル

#### Gemini（Google）
| モデル | 特徴 | 推奨用途 |
|--------|------|---------|
| gemini-2.0-flash | 高速・低コスト | 大量生成、テスト |
| gemini-1.5-pro | 高品質・高コスト | 重要な記事 |

#### OpenAI
| モデル | 特徴 | 推奨用途 |
|--------|------|---------|
| gpt-4o | バランス良好 | 汎用的な記事 |
| gpt-4o-mini | 高速・低コスト | 大量生成 |

#### Anthropic
| モデル | 特徴 | 推奨用途 |
|--------|------|---------|
| claude-3.5-sonnet | 自然な文章 | 読みやすさ重視 |
| claude-3-haiku | 高速 | 大量生成 |

### 選択の基準

| 優先事項 | 推奨モデル |
|---------|-----------|
| コスト重視 | gemini-2.0-flash, gpt-4o-mini |
| 品質重視 | gemini-1.5-pro, gpt-4o |
| 速度重視 | gemini-2.0-flash, claude-3-haiku |
| 日本語品質 | claude-3.5-sonnet |

### デフォルト設定

設定画面で各工程のデフォルトモデルを設定できます。
ワークフロー作成時に個別に変更も可能です。

### コスト目安

1記事（3,000字）あたり：
- 低コストモデル: 約10〜30円
- 高品質モデル: 約50〜100円',
    'settings',
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
    'settings.prompts',
    'プロンプト編集の注意点',
    '## プロンプト編集

各工程で使用するプロンプトをカスタマイズできます。

### 編集可能な項目

- システムプロンプト（AIの振る舞い）
- ユーザープロンプト（具体的な指示）
- 出力フォーマット指定

### 変数の使用

プロンプト内で使用できる変数：

```
{keyword}      - メインキーワード
{business}     - 事業情報
{target}       - ターゲット読者
{word_count}   - 目標文字数
{article_type} - 記事タイプ
{tone}         - トーン設定
```

### 編集時の注意

#### やってはいけないこと

- 変数名の変更（`{keyword}` → `{kw}`）
- 必須変数の削除
- 出力形式の大幅な変更

#### 推奨する変更

- トーンの調整
- 具体例の追加
- 禁止事項の追加

### バージョン管理

- 変更は新バージョンとして保存されます
- 過去のバージョンに戻すことが可能
- 本番使用前にテストを推奨

### テスト方法

1. 「プレビュー」で変数展開を確認
2. 「テスト実行」でサンプル生成
3. 問題なければ「公開」

### ロールバック

問題が発生した場合：
1. プロンプト設定画面を開く
2. 「バージョン履歴」をクリック
3. 戻したいバージョンを選択
4. 「このバージョンを適用」

### サポート

プロンプト編集でお困りの場合は、サポートにお問い合わせください。',
    'settings',
    30
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
