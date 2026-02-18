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

高品質なSEO記事を自動生成するワークフローです。**4種類のバリエーション記事**を一度に生成します。

### フロー概要図

```
┌─────────────────────────────────────────────────────────┐
│  【前半】人間確認あり（約15〜20分）                       │
│                                                         │
│  工程0 → 工程1 → 工程1.5 → 工程2 → 工程3A/3B/3C（並列） │
│  [KW選定] [競合取得] [スコア付与] [検証]  [分析3種]      │
│                                         ↓               │
│                                    ★承認待ち★          │
└─────────────────────────────────────────────────────────┘
                          ↓ 承認後
┌─────────────────────────────────────────────────────────┐
│  【後半】一気通貫実行（約40〜50分）                       │
│                                                         │
│  工程3.5 → 工程4 → 工程5 → 工程6 → 工程6.5              │
│  [Human要素] [戦略]  [一次情報] [強化]  [統合]           │
│                          ↓                              │
│  工程7A → 工程7B → 工程8 → 工程9 → 工程10               │
│  [初稿]   [推敲]   [ファクト] [最終] [4記事生成]         │
│                          ↓                              │
│  工程11（オプション）→ 工程12                           │
│  [画像生成]            [WordPress形式変換]              │
└─────────────────────────────────────────────────────────┘
```

### 所要時間の目安

| 条件 | 総所要時間 | 備考 |
|------|-----------|------|
| 標準（承認即時） | 約60分 | 承認待ち時間除く |
| 画像生成あり | +10〜15分 | 画像枚数による |
| 混雑時 | 最大90分 | API応答遅延時 |

### ステータス一覧

| ステータス | 意味 | 次のアクション |
|-----------|------|---------------|
| **実行中** | 工程処理中 | 完了を待つ |
| **承認待ち** | 人間の確認が必要 | レビューして承認/却下 |
| **完了** | 全工程終了 | ダウンロード可能 |
| **失敗** | エラー発生 | エラー確認後、再試行 |

### トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| 工程が長時間止まる | API応答遅延 | 10分待っても進まなければ再試行 |
| 承認後に進まない | Signal未送信 | ページ再読込後、再度承認 |
| 全工程失敗 | APIキー問題 | 設定画面でAPIキーを確認 |',
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

工程3では3つの分析を**同時並列**で実行します。この工程完了後に**承認待ち**となります。

### 並列実行の図解

```
        ┌─────────────┐
        │  工程2完了   │
        └──────┬──────┘
               │
       ┌───────┼───────┐
       ↓       ↓       ↓
   ┌───────┐┌───────┐┌───────┐
   │  3A   ││  3B   ││  3C   │  ← 同時実行（約3分）
   │トーン ││ FAQ  ││統計   │
   └───┬───┘└───┬───┘└───┬───┘
       └───────┼───────┘
               ↓
        ┌─────────────┐
        │ ★承認待ち★ │
        └─────────────┘
```

### 3A: トーン分析

競合記事から最適な文体・トーンを分析します。

**出力例:**
```json
{
  "formality": "やや丁寧（です・ます調）",
  "expertise_level": "中級者向け",
  "voice": "第三者視点、客観的"
}
```

### 3B: FAQ抽出

検索意図から想定される質問と回答を生成します。

**出力例:**
- Q: 〇〇と△△の違いは？
- Q: 初心者でも使えますか？
- Q: 料金はいくらですか？

### 3C: 統計データ収集

記事の信頼性を高める数値データを収集します。

**出力例:**
- 「〇〇市場は2024年に△△億円規模（出典: XX調査）」
- 「導入企業の85%が効果を実感（出典: YY白書）」

### 所要時間

| 条件 | 時間 |
|------|------|
| 標準 | 約3分 |
| API混雑時 | 最大5分 |

### トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| 1つだけ失敗 | API一時エラー | 失敗した工程のみ再試行 |
| 全て失敗 | APIキー問題 | 設定画面で確認 |
| 結果が薄い | 競合データ不足 | 工程1の結果を確認 |',
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
    '承認・却下の操作方法',
    '## 承認フローの詳細ガイド

工程3（並列分析：3A/3B/3C）が完了すると、ワークフローは「承認待ち」状態で一時停止します。この段階で人間が内容を確認し、次の工程に進むかどうかを判断します。

### 画面の見方

ワークフロー詳細画面の上部に、オレンジ色の「承認待ち」バッジが表示されます。画面中央には、工程3の出力サマリー（トーン分析結果・FAQ候補・収集された統計データ）がタブ形式で並び、それぞれの内容をプレビューできます。画面下部に「承認」（緑色）と「却下」（赤色）の2つのボタンが配置されています。

### 承認の判断基準

以下の観点で出力内容を確認してください：

| 確認観点 | チェックポイント |
|---------|----------------|
| **トーン（3A）** | ターゲット読者に適した文体か、専門用語の量は適切か |
| **FAQ（3B）** | 想定される質問が網羅されているか、回答が的確か |
| **統計（3C）** | 信頼できる出典か、数値は最新か、記事との関連性 |

### 操作手順

**承認する場合**：
1. 各タブの内容を確認
2. 「承認」ボタン（緑色、画面右下）をクリック
3. 確認ダイアログで「承認して続行」を選択
4. 工程4（詳細アウトライン）が自動的に開始

**却下する場合**：
1. 「却下」ボタン（赤色）をクリック
2. 却下理由を入力（必須、50文字以上推奨）
3. 再実行する工程を選択（デフォルト：工程3全体）
4. 「却下を確定」をクリック

### ベストプラクティス

- **迷ったら却下**：品質に疑問があれば再実行する方が最終品質は高まります
- **具体的な理由を記載**：「トーンが硬すぎる」より「30代女性向けなので、もう少し親しみやすい表現に」と具体的に
- **部分再実行を活用**：3Aのみ問題なら3Aだけ再実行し、3B/3Cは維持できます',
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
    'レビュータイプと品質管理サイクル',
    '## レビュータイプと品質管理

レビュー機能は、記事の品質を担保するための**最終防衛ライン**です。公開前に必ず実行し、品質基準を満たしているか確認してください。

### ワークフロー全体での位置づけ

レビューは「工程10」に相当し、生成（工程7）→ファクトチェック（工程8）→品質向上（工程9）を経た記事の最終確認を行います。ここでOKが出れば公開準備へ進みます。

### レビュータイプの使い分け

| タイプ | いつ重要か | 見落としがちな問題 |
|--------|-----------|-------------------|
| **SEO** | 検索流入を狙う記事 | メタディスクリプション不足 |
| **読みやすさ** | 一般読者向け記事 | 専門用語の過多 |
| **事実確認** | データを扱う記事 | 出典リンク切れ |
| **ブランド** | 企業公式コンテンツ | トーンの不一致 |

### 効率的なレビュー運用

1. **全タイプ一括実行**: 最初は全観点でレビュー
2. **弱点集中**: 過去に指摘が多い観点を重点確認
3. **定期的な基準見直し**: 月次で品質基準を更新

### チーム運用での品質基準

複数人で運用する場合は、「公開OK」の基準を明文化しておいてください。例：「SEOスコア70以上 AND Critical指摘ゼロ」など。',
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
    '記事タイプの選び方',
    '## 記事タイプの選び方

**読者の検索意図**に最適なタイプを選ぶことで、記事の効果が大きく変わります。

### タイプ別の特徴と具体例

| タイプ | 向いているキーワード例 | 生成される記事イメージ |
|--------|----------------------|---------------------|
| **網羅型** | 「SEOとは」「確定申告 やり方」 | 基礎から応用まで体系的に解説 |
| **深掘り型** | 「React Hooks 使い方」「投資信託 リスク」 | 1つのテーマを徹底的に掘り下げ |
| **比較型** | 「WordPress vs Wix」「転職サイト おすすめ」 | 複数の選択肢をメリデメ比較 |
| **ハウツー型** | 「YouTube 始め方」「確定申告 書き方」 | STEP1→2→3の手順形式 |
| **リスト型** | 「副業 おすすめ10選」「時短家電 ランキング」 | 箇条書き・番号付きで整理 |

### よくある間違い

| 状況 | 間違った選択 | 正しい選択 |
|------|------------|-----------|
| 「〇〇 比較」で検索されるKW | 網羅型 | **比較型** |
| 「〇〇 やり方」で検索されるKW | リスト型 | **ハウツー型** |
| 初心者向けの入門記事 | 深掘り型 | **網羅型** |

### プロのコツ

1. **検索結果を確認**: 上位記事がどのタイプか見てみる
2. **読者の次のアクション**: 読後に何をしてほしいかで選ぶ
3. **迷ったら網羅型**: 最も汎用性が高い

### 複合タイプの活用

2つまで組み合わせ可能。例：
- 「網羅型＋ハウツー型」→ 基礎知識＋実践手順
- 「比較型＋リスト型」→ 複数商品の比較ランキング',
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
    'CTAの設計と配置',
    '## CTA（Call To Action）の設計

**CTA = 読者に起こしてほしい具体的なアクション**。記事のゴールを達成するための重要な要素です。

### CTAタイプと具体例

| CTAタイプ | 具体例 | 向いている記事 |
|----------|-------|--------------|
| **資料請求** | 「無料ホワイトペーパーをダウンロード」 | BtoB、専門性の高い記事 |
| **問い合わせ** | 「無料相談を予約する」 | サービス紹介、比較記事 |
| **会員登録** | 「30日間無料で試す」 | SaaS、ツール紹介記事 |
| **購入** | 「今すぐ購入」「カートに入れる」 | EC、商品レビュー記事 |
| **メルマガ** | 「最新情報を受け取る」 | ブログ、情報系記事 |

### 配置位置の効果

| 位置 | 効果 | クリック率目安 |
|------|------|--------------|
| 記事冒頭（導入後） | 即決ユーザー向け | 低（1-2%） |
| 記事中盤 | 興味が高まった瞬間 | 中（2-3%） |
| **記事末尾** | 読了者向け、最も効果的 | **高（3-5%）** |
| 複数配置 | 機会損失を防ぐ | 合計で最大化 |

### よくある間違い

- **CTAと記事内容のミスマッチ**: 「SEOとは」の記事に「今すぐ購入」
- **押しつけがましいCTA**: 記事より目立つボタン、過度な繰り返し
- **行動が不明確**: 「詳しくはこちら」→何が起きるか分からない

### ベストプラクティス

1. **1記事1ゴール**: メインCTAは1種類に絞る
2. **価値を先に**: 「無料で〇〇がわかる」のように得られるものを明示
3. **ハードルを下げる**: 「1分で完了」「クレカ登録不要」

### CTAを設定しない方がいい場合

- 純粋な情報提供記事（用語解説など）
- ブランド認知目的の記事
- まだ信頼関係が築けていない初期接点の記事',
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
    '文字数の決め方',
    '## 文字数の決め方

**「何文字書くか」ではなく「読者が必要とする情報量」**で考えるのがポイントです。

### キーワード別の文字数目安

| キーワードの特徴 | 文字数目安 | 理由 |
|----------------|-----------|------|
| 「〇〇とは」（入門） | 2,000〜3,000字 | 基本情報を簡潔に |
| 「〇〇 やり方」（実践） | 3,000〜5,000字 | 手順+補足説明 |
| 「〇〇 比較」（検討） | 4,000〜6,000字 | 複数項目の詳細比較 |
| 「〇〇 おすすめ」（まとめ） | 5,000〜8,000字 | 複数選択肢の紹介 |
| 専門的な解説 | 6,000〜10,000字 | 深い情報+事例 |

### よくある間違い

| 間違い | なぜダメか | 改善策 |
|--------|----------|--------|
| 「長いほどSEOに強い」 | 冗長な記事は離脱率UP | **競合の平均文字数を参考に** |
| 「短く簡潔に」 | 情報不足で検索意図を満たせない | **読者の疑問を網羅する** |
| 「きっちり〇〇文字」 | 文字数稼ぎで質が下がる | **内容優先、文字数は結果** |

### プロの決め方

1. **競合記事を3〜5本チェック**: 上位表示されている記事の文字数を確認
2. **検索意図から逆算**: 「この疑問に答えるには何が必要？」
3. **足りない情報を追加**: 競合にない独自価値を加える

### 文字数別の記事イメージ

```
1,500字以下 → ニュースや速報（読了1-2分）
2,000〜3,000字 → 標準的なブログ記事（読了3-5分）
4,000〜5,000字 → しっかり解説記事（読了7-10分）
6,000字以上 → 完全ガイド・長編解説（読了10分以上）
```

### 設定のコツ

- **初めてなら3,000〜4,000字**: 最もバランスが良い
- **実際は±20%の変動あり**: 内容の充実度を優先
- **読了時間も意識**: 長すぎると離脱率が上がる',
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
    'CTA詳細設定のコツ',
    '## CTA詳細設定

CTAの効果を最大化するための具体的な設定方法です。

### CTAテキストの書き方

**良い例と悪い例**

| NG例 | なぜダメか | 改善例 |
|------|----------|--------|
| 「こちら」 | 何が起きるか不明 | 「無料資料をダウンロード」 |
| 「送信」 | 冷たい印象 | 「無料で相談する」 |
| 「登録」 | メリットが不明 | 「30日間無料で試す」 |
| 「クリック」 | 価値が伝わらない | 「特典を受け取る」 |

### 効果的なCTAの公式

```
[動詞] + [得られるもの] + [ハードル軽減]

例：
「無料で」+「SEOガイドを」+「今すぐダウンロード」
「3分で」+「見積もりを」+「取得する」
「登録なしで」+「デモを」+「体験する」
```

### 訴求ポイントのパターン

| パターン | 具体例 | 効果 |
|---------|-------|------|
| **限定性** | 「今週末まで」「先着100名」 | 緊急性を演出 |
| **無料** | 「0円」「無料」「タダ」 | 心理的ハードルを下げる |
| **簡単** | 「1分で完了」「入力3項目」 | 面倒くささを解消 |
| **安心** | 「しつこい営業なし」「いつでも解約OK」 | 不安を払拭 |
| **実績** | 「10,000社導入」「満足度98%」 | 信頼性を向上 |

### リンク先URLの注意点

- **専用LP推奨**: 記事から直接トップページはNG
- **遷移を最小化**: フォームは記事のすぐ次のページに
- **モバイル対応**: スマホで見やすいか必ず確認

### CTA周辺の文章（リードコピー）

CTAボタンの直前に置く説得文も重要：

```
悪い例：
「お問い合わせはこちら」

良い例：
「ここまで読んでいただいた方限定で、
SEO診断レポートを無料でプレゼント中。
サイトの改善ポイントが3分でわかります。」
```

### チェックリスト

- [ ] CTAテキストに動詞が含まれている
- [ ] 得られる価値が明確
- [ ] ハードルを下げる要素がある
- [ ] 記事内容とCTAが一致している
- [ ] モバイルでもタップしやすいサイズ',
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
    '最終確認のチェックポイント',
    '## 最終確認画面

**ワークフロー開始前の最後の砦**。ここで見逃すと、やり直しにコストがかかります。

### 必ず確認すべき5項目

| 確認項目 | よくあるミス | チェック方法 |
|---------|------------|------------|
| **キーワード** | 誤字脱字、表記ゆれ | 声に出して読む |
| **ターゲット** | 抽象的すぎる | 「この人は実在する？」と問う |
| **記事タイプ** | 検索意図と不一致 | 競合上位を再確認 |
| **文字数** | 多すぎ/少なすぎ | 競合の平均と比較 |
| **CTA** | 記事内容とミスマッチ | 読者の次の行動を想像 |

### 見落としやすいポイント

**1. キーワードの表記ゆれ**
```
NG: 「引越し」と「引っ越し」が混在
OK: どちらかに統一（検索ボリュームで判断）
```

**2. 事業情報の具体性**
```
NG: 「良いサービスを提供」
OK: 「導入企業の95%が1年以上継続利用」
```

**3. ターゲットの絞り込み**
```
NG: 「ビジネスマン全般」
OK: 「経理経験3年未満の中小企業担当者」
```

### 見積もり情報の見方

| 項目 | 目安 | 超えている場合 |
|------|------|--------------|
| 所要時間 | 10〜20分 | 文字数を減らす検討 |
| APIコスト | 50〜100円 | 文字数・画像枚数を見直し |
| 画像枚数 | 3〜5枚 | 本当に必要か再検討 |

### 修正が必要な場合

- **「編集」ボタン**: 各セクションから直接戻れる
- **「戻る」ボタン**: 1ステップずつ戻る
- **最初から**: 大幅な変更なら新規作成がおすすめ

### 開始前の最終チェックリスト

- [ ] キーワードに誤字脱字がない
- [ ] 競合上位の記事タイプと一致している
- [ ] ターゲット像が具体的
- [ ] 文字数が妥当（競合比較済み）
- [ ] CTAが記事の目的に合っている
- [ ] 見積もりコストが予算内

### 開始後は変更不可

> ワークフロー開始後は設定変更できません。
> 「なんか違う」と思ったら、ここで止まって見直してください。
> やり直しのコストは、確認のコストよりはるかに大きいです。',
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
    '工程0: キーワード分析',
    '## 工程0: キーワード分析

ワークフローの起点となる工程です。入力されたキーワードを多角的に分析し、記事戦略の土台を構築します。

### 処理フロー図

```
┌──────────────┐
│ キーワード入力 │
└──────┬───────┘
       ↓
┌──────────────┐
│ 検索意図分析  │ ← 4タイプに分類
└──────┬───────┘
       ↓
┌──────────────┐
│ 関連KW拡張   │ ← サジェスト・共起語
└──────┬───────┘
       ↓
┌──────────────┐
│ 出力: 分析JSON│
└──────────────┘
```

### 検索意図の4タイプ

| タイプ | 意味 | 例 |
|--------|------|-----|
| Informational | 情報収集 | 「〇〇とは」「〇〇 やり方」 |
| Navigational | 特定サイト | 「△△ 公式」「□□ ログイン」 |
| Commercial | 比較検討 | 「〇〇 おすすめ」「△△ 比較」 |
| Transactional | 購入・申込 | 「〇〇 購入」「△△ 申し込み」 |

### 出力例

```json
{
  "main_keyword": "クラウド会計 比較",
  "search_intent": "Commercial",
  "related_keywords": ["freee", "マネーフォワード", "弥生"],
  "suggested_headings": ["選び方", "機能比較", "料金比較"]
}
```

### 所要時間と変動要因

| 条件 | 時間 |
|------|------|
| 標準 | 約1〜2分 |
| 関連KW多数 | 最大3分 |

### トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| 関連KWが少ない | ニッチすぎるKW | より一般的なKWを試す |
| 検索意図が不適切 | KWが曖昧 | より具体的なKWに変更 |',
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

検索上位の競合記事をスクレイピングし、分析用データを収集します。

### 処理フロー図

```
┌──────────────┐
│ Google検索   │ ← キーワードで検索
└──────┬───────┘
       ↓
┌──────────────┐
│ 上位10〜20件 │ ← URL・タイトル取得
│ 記事を取得   │
└──────┬───────┘
       ↓
┌──────────────────────┐
│ 各記事をスクレイピング │
│ ・見出し構造(H1〜H4)   │
│ ・本文テキスト        │
│ ・文字数・段落数      │
└──────┬───────────────┘
       ↓
┌──────────────┐
│ 出力: CSV    │
└──────────────┘
```

### 収集される情報

| 項目 | 説明 | 用途 |
|------|------|------|
| URL | 記事のアドレス | 参照用 |
| タイトル | ページタイトル | タイトル設計の参考 |
| 見出し構造 | H1〜H4の階層 | 構成案の参考 |
| 本文 | 記事全文 | トーン・内容分析 |
| 文字数 | 総文字数 | 目標文字数の参考 |

### 出力例（CSV形式）

```
rank,url,title,word_count,h2_count
1,https://example.com/article1,クラウド会計とは,5200,8
2,https://example.com/article2,会計ソフト比較,4800,6
```

### 所要時間と変動要因

| 条件 | 時間 | 理由 |
|------|------|------|
| 標準 | 約2〜3分 | 10記事程度 |
| 記事が長い | 最大5分 | スクレイピング量増加 |
| アクセス制限 | +1〜2分 | リトライ発生 |

### トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| 取得件数が少ない | アクセス制限 | 時間を置いて再試行 |
| 一部記事が空 | JS描画サイト | 分析対象から除外 |
| 文字化け | エンコード問題 | 自動補正あり |',
    'workflow',
    12
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
    '工程2: 競合データ検証',
    '## 工程2: 競合データ検証

工程1で収集した競合データを検証し、記事構成案の素案を作成します。

### 処理フロー図

```
┌────────────────┐
│ 工程1のCSV読込 │
└──────┬─────────┘
       ↓
┌────────────────┐
│ データ品質検証 │
│ ・重複チェック │
│ ・文字数確認   │
│ ・見出し整合性 │
└──────┬─────────┘
       ↓
┌────────────────┐
│ スコアリング   │ ← 各記事に品質スコア付与
└──────┬─────────┘
       ↓
┌────────────────┐
│ 構成案素案作成 │
└────────────────┘
```

### 品質スコアの基準

| スコア | 基準 | 扱い |
|--------|------|------|
| A (80-100) | 文字数十分、見出し構造良好 | 重点参考 |
| B (60-79) | 標準的な品質 | 参考 |
| C (40-59) | 一部データ欠損 | 補助的参考 |
| D (0-39) | 品質不足 | 除外 |

### 出力例

```markdown
## 推奨構成案（素案）

### H2候補
1. クラウド会計とは（競合8/10記事で採用）
2. 主要サービス比較（競合7/10記事で採用）
3. 選び方のポイント（競合6/10記事で採用）
4. 料金プラン（競合5/10記事で採用）

### 推奨文字数: 4,500〜5,500字
（競合平均: 5,100字）
```

### 所要時間

| 条件 | 時間 |
|------|------|
| 標準 | 約1〜2分 |
| データ量多い | 最大3分 |

### トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| スコアが全体的に低い | 競合データ不足 | 工程1を再実行 |
| 構成案が貧弱 | ニッチなKW | 関連KWを追加 |
| 処理が長い | CSV行数過多 | 上位10件に絞る |',
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
    '工程の再実行手順',
    '## 工程再実行の詳細ガイド

エラー発生時や出力品質に問題がある場合、特定の工程だけを再実行できます。全体を最初からやり直す必要はありません。

### 再実行が必要なケース

| 状況 | 原因例 | 対処 |
|------|--------|------|
| エラーで工程が失敗 | APIタイムアウト、一時的な障害 | 同一工程を再実行 |
| 出力内容が不十分 | トーンが合わない、情報不足 | 同一工程を再実行 |
| 前工程の修正が必要 | 構成案の見直し | 該当工程から再実行 |

### 画面操作手順

**Step 1: 工程パネルを開く**
ワークフロー詳細画面で、左側の工程一覧から再実行したい工程をクリックします。選択された工程は青色のハイライトで表示されます。

**Step 2: 再実行ボタンを押す**
工程詳細パネル右上の「再実行」ボタン（円形矢印アイコン、青色）をクリックします。失敗した工程の場合は、ボタンがオレンジ色で強調表示されています。

**Step 3: 再実行範囲を選択**
ダイアログで以下のいずれかを選択：
- **この工程のみ**：選択した工程だけを再実行
- **この工程以降すべて**：選択した工程から最終工程まで再実行

**Step 4: 実行を確定**
「実行」ボタンをクリックすると再実行が開始されます。

### 依存関係の注意点

工程間には依存関係があります。例えば工程2を再実行すると、工程3A/3B/3Cも自動的に再実行対象になります。ダイアログに影響範囲が表示されるので、確認してから実行してください。

### 再実行できない場合

- **実行中の工程**：完了を待つか、キャンセルが必要
- **承認済み工程の前工程**：承認を取り消してから再実行

### コストと履歴

再実行にはAPIコストが発生します（通常実行と同等）。すべての再実行は監査ログに記録され、「履歴」タブで確認できます。',
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
    '成果物の確認とダウンロード',
    '## 成果物（アーティファクト）の確認方法

各工程で生成された成果物は、ワークフロー詳細画面からいつでも確認・ダウンロードできます。

### 成果物の種類と用途

| 工程 | 成果物 | 形式 | 活用シーン |
|------|--------|------|-----------|
| 工程0 | キーワード分析 | JSON | SEO戦略の確認 |
| 工程1 | 競合分析 | JSON/CSV | 競合サイト調査 |
| 工程2 | 構成案 | Markdown | 記事構成の確認 |
| 工程3A | トーン分析 | JSON | 文体の確認 |
| 工程3B | FAQ | JSON | Q&Aセクション素材 |
| 工程3C | 統計データ | JSON | 引用データ確認 |
| 工程7 | 記事本文 | Markdown | 編集・レビュー |
| 工程10 | 最終記事 | Markdown/HTML | 公開前最終確認 |
| 工程11 | 画像 | PNG/JPG | サイト掲載用 |
| 工程12 | WordPress HTML | HTML | CMS投稿用 |

### 確認手順

**Step 1: 工程を選択**
左側の工程一覧から、確認したい工程をクリックします。完了済みの工程には緑色のチェックマークが表示されています。

**Step 2: 成果物タブを開く**
工程詳細パネルで「成果物」タブ（ファイルアイコン）をクリックします。

**Step 3: プレビューまたはダウンロード**
- **プレビュー**：「目」アイコンをクリック（形式に応じた表示）
- **ダウンロード**：「DL」ボタンをクリック

### プレビュー機能の詳細

| 形式 | プレビュー内容 |
|------|---------------|
| Markdown | レンダリングされた見やすい表示 |
| JSON | シンタックスハイライト付き、折りたたみ可能 |
| HTML | 実際のブラウザ表示に近いプレビュー |
| 画像 | サムネイル表示、クリックで拡大 |

### 一括ダウンロード

画面右上の「全てダウンロード」ボタンで、全工程の成果物をZIP形式で一括取得できます。フォルダ構造は `工程名/ファイル名` の形式です。

### 保存期間と注意事項

成果物は**30日間**保存されます。期限後は自動削除されるため、必要なファイルは早めにダウンロードしてください。ダウンロード履歴は監査ログに記録されます。',
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
    '記事一覧と全体管理',
    '## 記事一覧画面

記事一覧は、SEOコンテンツ制作の**司令塔**となる画面です。ここから全記事の状況を把握し、優先度を決めて作業を進めます。

### ワークフロー全体での位置づけ

一覧画面は「どの記事に今注力すべきか」を判断する起点です。ステータスとレビュー状態を組み合わせて確認し、次のアクションを決定します。

### 表示カラムの活用

| カラム | 確認ポイント |
|--------|-------------|
| ステータス | 「承認待ち」を最優先で対応 |
| レビュー | 「要修正」は早めに対処 |
| 更新日 | 長期間放置されていないか |

### 効率的な管理のコツ

1. **朝一で「承認待ち」を確認**: 工程3完了後の承認作業を溜めない
2. **「失敗」は即対応**: 原因特定→再実行のサイクルを素早く回す
3. **完了記事は週次で棚卸し**: 公開待ちが溜まっていないか確認

### チーム運用時の注意

複数人で運用する場合は、担当者カラムでフィルタして自分の担当記事に集中してください。他者の作業中記事に手を出さないことがトラブル防止の基本です。',
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
    '検索・フィルタで効率化',
    '## 検索・フィルタ機能

記事が増えてくると、目的の記事を探すのに時間がかかります。フィルタ機能を使いこなして、**管理工数を半分以下**に削減してください。

### 日常業務での活用パターン

| 場面 | おすすめフィルタ |
|------|----------------|
| 朝の確認 | ステータス「承認待ち」 |
| レビュー作業 | 「完了」+「未レビュー」 |
| トラブル対応 | ステータス「失敗」 |
| 週次棚卸し | 「完了」+期間「過去7日」 |

### 保存フィルタの活用（時短のコツ）

毎日同じフィルタを設定するのは時間の無駄です。よく使う条件は保存して1クリックで呼び出してください。

**おすすめ保存フィルタ**:
- 「今日の承認待ち」: ステータス「承認待ち」+期間「今日」
- 「レビュー対象」: 「完了」+「未レビュー」
- 「要対応」: ステータス「失敗」OR レビュー「要修正」

### チーム運用でのフィルタ共有

保存したフィルタはチーム内で共有できます。新人が入った際に、まず「おすすめフィルタ」を教えることで立ち上がりが早くなります。

### 大量記事管理のベストプラクティス

100件を超えたら、デフォルト表示を「未完了のみ」に変更することを推奨します。完了済み記事はアーカイブとして別管理する運用も検討してください。',
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
    'ステータス管理と品質サイクル',
    '## ステータス管理の考え方

ステータスは記事の「健康状態」を示す指標です。適切に管理することで、**公開事故を防ぎ**、チーム全体の生産性を向上させます。

### ステータスとワークフローの関係

| ステータス | ワークフロー上の意味 | 注意点 |
|-----------|---------------------|--------|
| 未レビュー | 工程10未実施 | 公開前に必ずレビュー |
| 要修正 | 品質基準未達 | 放置するとボトルネックに |
| レビュー済み | 公開準備OK | 速やかに次工程へ |

### ステータス別の対応優先度

1. **最優先**: 「要修正」→ 品質問題を放置しない
2. **高**: 「未レビュー」→ 溜めると作業が滞留
3. **中**: 「レビュー済み」→ 公開タイミングを計画

### チーム運用のベストプラクティス

- **日次で「要修正」ゼロを目指す**: 翌日に持ち越さない文化づくり
- **ステータス更新はリアルタイムで**: 作業完了後すぐに変更
- **手動変更は理由をメモ**: 監査ログで追跡可能に

### よくある問題と対処法

| 問題 | 原因 | 対処 |
|------|------|------|
| 「要修正」が溜まる | 担当者不明 | 担当者を明確に割り当て |
| 同じ指摘が繰り返される | 根本原因未対応 | プロンプト設定を見直し |
| ステータスが古い | 更新忘れ | 日次確認をルーティン化 |',
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
    'レビュー結果の活用と改善サイクル',
    '## レビュー結果の読み方

レビュー結果は単なる「点数表」ではありません。**次のアクションを決める判断材料**として活用してください。

### ワークフローでの位置づけ

レビュー結果は「工程10」の出力です。この結果を元に「公開」「修正」「再生成」の判断を下します。ここでの判断が最終品質を決定します。

### 総合スコアと判断基準

| スコア | 評価 | 推奨アクション |
|--------|------|---------------|
| 90〜100 | 優秀 | 即公開OK |
| 70〜89 | 良好 | 軽微修正→公開 |
| 50〜69 | 要改善 | 該当工程を再実行 |
| 50未満 | 要大幅修正 | 設定見直し→再生成 |

### 効率的な結果分析のコツ

1. **Critical（🔴）を最優先**: まずCriticalがゼロかを確認
2. **傾向を把握**: 同じ種類の指摘が複数あれば根本原因を疑う
3. **スコア推移を確認**: 再レビュー時は前回比較で改善度を確認

### チーム運用での基準統一

「公開OK」の基準をチームで明文化してください。例えば「SEOスコア75以上 AND Criticalゼロ」など。曖昧な基準は品質のばらつきを生みます。

### よくある分析の落とし穴

- スコアだけ見て指摘内容を確認しない
- Info（🔵）を無視して同じ指摘を繰り返す
- 履歴を見ずに同じ修正を何度もやる',
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
    'レビュー後のアクションと改善サイクル',
    '## レビュー後のアクション

レビュー結果を受けて「何をするか」を迅速に判断することが、**制作効率と品質の両立**につながります。

### ワークフローでの位置づけ

レビュー後のアクションは「工程10」から「工程11（画像生成）または公開準備」への橋渡しです。ここで適切な判断を下さないと、後工程で手戻りが発生します。

### 判断フローチャート

1. **Criticalゼロ？** → No: 該当箇所を修正
2. **スコア70以上？** → No: 該当工程を再実行
3. **全観点クリア？** → No: 弱い観点を改善
4. **すべてYes** → 次の工程へ進む

### 効率的な修正アプローチ

| 指摘の傾向 | 効率的な対応 |
|-----------|-------------|
| 同じ種類が3件以上 | 根本原因を特定→工程再実行 |
| 散発的な軽微指摘 | 個別に手動修正 |
| SEO関連が多い | プロンプト設定を見直し |

### チーム運用での効率化

- **週次レビュー会**: 頻出指摘をチームで共有し、プロンプトを改善
- **ナレッジ蓄積**: 効果的だった修正パターンを記録
- **担当者ローテ**: 特定の人に修正が集中しないよう分散

### よくある非効率パターン

- スコアだけ見て「OK」と判断→Critical見落とし
- 毎回同じ指摘を手動修正→設定を見直すべき
- 全指摘を一人で対応→チームで分担すべき',
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
