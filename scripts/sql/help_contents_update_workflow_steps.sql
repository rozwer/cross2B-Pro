-- ============================================================================
-- help_contents 工程ヘルプコンテンツ改良版
-- ============================================================================
-- 実行方法:
--   psql -U seo -d seo_common -f scripts/sql/help_contents_update_workflow_steps.sql
-- ============================================================================
-- 対象help_key:
--   - workflow.step4-6
--   - workflow.step7
--   - workflow.step8-9
--   - workflow.step10
--   - workflow.step11
--   - workflow.step12
-- ============================================================================

-- ----------------------------------------------------------------------------
-- workflow.step4-6: 戦略的アウトライン生成
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step4-6',
    '工程4-6: 戦略的アウトライン生成',
    '## 工程4-6: 戦略的アウトライン生成

並列分析とHuman Touch要素を統合し、4本柱に基づく詳細なアウトラインを作成します。

### 工程4: 戦略的アウトライン（Claude使用）

3フェーズ構成と4本柱（神経科学・行動経済学・LLMO・KGI）を組み込んだアウトラインを生成。

**出力例（主要フィールド）:**
- `three_phase_structure`: Phase1（不安認識15%）/Phase2（理解70%）/Phase3（行動15%）
- `cta_placements`: Early（650字）/Mid（2800字）/Final（末尾-500字）
- `title_metadata`: 32文字前後、数字含有、括弧なし

### 工程5: 一次情報収集（Gemini+Web検索）

外部ソースから信頼性の高いデータを収集。工程6でアウトラインに統合されます。

### 工程6: アウトライン強化版（Claude使用）

一次情報を反映し、データアンカー（引用）を配置。出典形式も設定。

### 品質チェックポイント

| 項目 | 基準 |
|------|------|
| タイトル文字数 | 32文字前後（28-36文字許容） |
| フェーズ配分 | Phase2が65-75%を占める |
| CTA配置 | 3段階（Early/Mid/Final）が設定済み |
| 4本柱設定 | 各H2セクションに設定あり |

### よくあるエラーと対処

- **タイトル超過**: 32文字以内に短縮。括弧を削除、表現を凝縮
- **フェーズ偏り**: Phase2が75%超の場合、工程3からやり直しを検討
- **一次情報取得失敗**: URL無効の場合、代替ソースで再試行',
    'workflow',
    40
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- workflow.step7: 本文生成（初稿＋ブラッシュアップ）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step7',
    '工程7: 本文生成（7A初稿/7Bブラッシュアップ）',
    '## 工程7: 本文生成（2段階処理）

工程7は7A（初稿）と7B（ブラッシュアップ）の2段階で、高品質な記事本文を生成します。

### 工程7A: 本文初稿生成（Claude使用）

アウトラインに基づき、4本柱を実装した本文を生成。

**出力例（主要フィールド）:**
```json
{
  "draft": "# タイトル\n\n## 導入...",
  "section_word_counts": [
    {"section_title": "導入", "target": 500, "actual": 520}
  ],
  "cta_implementation": {"early": true, "mid": true, "final": true}
}
```

### 工程7B: ブラッシュアップ（Gemini使用）

初稿を推敲し、読みやすさと一貫性を向上。

**改善内容:**
- 語尾統一、一文長さ調整（20-35文字目標）
- 接続詞改善、冗長表現削除
- 文字数維持（±5%以内）

### 品質チェックポイント

| 項目 | 基準 |
|------|------|
| 文字数達成 | 目標の±20%以内 |
| セクション独立性 | 各H2が単独で理解可能 |
| CTA配置 | Early/Mid/Finalの3箇所 |
| 4本柱実装 | 各セクションに適用済み |

### カスタマイズによる出力の違い

| 設定 | 出力への影響 |
|------|-------------|
| 文字数多め | 分割生成（3-5パート）で対応 |
| 専門的トーン | 専門用語を残し、解説を追加 |
| CTA強め | 各CTAに説得文を追加 |

### よくあるエラーと対処

- **文字数不足**: 工程6のアウトラインを詳細化して再試行
- **トーン不一致**: 工程3Aのトーン分析を修正して再実行
- **分割生成失敗**: タイムアウトの場合、モデルを高速版に変更',
    'workflow',
    50
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- workflow.step8-9: ファクトチェック・最終リライト
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step8-9',
    '工程8-9: ファクトチェック・最終リライト',
    '## 工程8-9: ファクトチェック・最終リライト

記事の正確性を検証し、SEO最適化された最終版を生成します。

### 工程8: ファクトチェック＋FAQ生成（Gemini+Web検索）

4カテゴリで事実検証し、FAQセクションを生成。

**検証カテゴリ:**
| カテゴリ | 検証内容 |
|---------|---------|
| 数値データ | 統計・割合・金額の正確性 |
| 出典正確性 | 組織名・出版物名の確認 |
| 時系列整合性 | 日付・年・順序の整合 |
| 論理整合性 | 比較・文脈・解釈の妥当性 |

**FAQ出力例:**
```json
{
  "faq_items": [
    {
      "question": "SEOツールの費用相場は？",
      "answer": "月額3,000〜50,000円が一般的...",
      "voice_search_optimized": true
    }
  ]
}
```

### 工程9: 最終リライト（Claude使用）

ファクトチェック結果を反映し、SEO最適化。

**出力に含まれる品質スコア（8項目）:**
- 正確性 / 読みやすさ / 説得力 / 網羅性
- 差別化 / 実用性 / SEO最適化 / CTA効果

### 品質チェックポイント

| 項目 | 基準 |
|------|------|
| 検証率 | クレームの80%以上が検証済み |
| 矛盾検出 | 矛盾ゼロ（検出時は要確認フラグ） |
| FAQ数 | 10-15個（音声検索最適化済み） |
| 総合スコア | 0.90以上で公開推奨 |

### 重要な注意点

**自動修正は禁止**: ファクトチェックで矛盾が検出された場合、自動修正せず「要確認」フラグが立ちます。人間によるレビューが必須です。

### よくあるエラーと対処

- **矛盾検出**: 該当箇所を確認し、手動で修正または工程7からやり直し
- **検証率低下**: 一次情報URL無効の場合、工程5を再実行
- **スコア低下**: 指摘箇所を確認し、該当工程を再実行',
    'workflow',
    60
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- workflow.step10: 4記事バリエーション生成
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step10',
    '工程10: 4記事バリエーション生成',
    '## 工程10: 4記事バリエーション生成

1つのキーワードから、ターゲット別の4つの記事バリエーションを生成します。

### 生成される4記事

| 記事 | タイプ | ターゲット | 文字数目安 |
|------|--------|-----------|-----------|
| 1 | メイン記事 | 全読者向け | 5,000-8,000字 |
| 2 | 初心者向け | 基礎から学びたい人 | 3,000-5,000字 |
| 3 | 実践編 | 具体的手順を求める人 | 4,000-6,000字 |
| 4 | まとめ | 要点だけ知りたい人 | 2,000-3,000字 |

### 出力例（各記事）

```json
{
  "article_number": 1,
  "title": "SEOツール完全比較ガイド2025",
  "meta_description": "主要SEOツール10選を...",
  "structured_data": {"@type": "Article", ...},
  "word_count_report": {"target": 6000, "achieved": 5850}
}
```

### 品質チェックポイント

| 項目 | 基準 |
|------|------|
| 文字数達成 | 各記事が目標の±5%以内 |
| 構造化データ | Article/FAQPage schema生成済み |
| 見出し階層 | H1→H2→H3が正しい順序 |
| メタ情報 | title 60文字以内、description 120文字以内 |

### 公開チェックリスト（自動評価）

各記事に対して以下を自動チェック:
- **SEO**: タイトル最適化、キーワード密度、内部リンク
- **4本柱**: 神経科学・行動経済学・LLMO・KGI適用
- **技術**: HTML検証、画像alt属性、リンク有効性

### ダウンロード形式

- **Markdown**: 各記事の.mdファイル
- **HTML**: プレビュー用HTMLファイル
- **JSON**: メタ情報・スコア・構造化データ

### よくあるエラーと対処

- **HTML検証失敗**: タグ未閉じの場合、工程を再実行
- **文字数大幅超過**: Phase2の比率を下げて工程4から再実行
- **構造化データ不備**: メタ情報を確認し、不足があれば手動補完',
    'workflow',
    70
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- workflow.step11: 画像生成（Human-in-the-loop）
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step11',
    '工程11: 画像生成（Human-in-the-loop）',
    '## 工程11: 画像生成（Human-in-the-loop）

記事に挿入する画像をAIで生成します。API経由の対話形式で進行します。

### 処理フロー（8サブステップ）

| フェーズ | 処理内容 | ユーザー操作 |
|---------|---------|-------------|
| 11A | 画像生成確認 | 生成する/スキップを選択 |
| 11B | 設定入力 | 枚数（1-10）、位置リクエスト |
| 11C | 位置分析 | AIが候補を提案（自動） |
| 11D | 位置確認 | 承認/修正/再分析を選択 |
| 11E | 指示入力 | 各画像の生成指示を編集 |
| 11F | 生成＆確認 | 承認/リトライ（最大3回） |
| 11G | 画像挿入 | Markdown/HTMLに統合（自動） |
| 11H | プレビュー | 最終確認 |

### 位置分析の3カテゴリ

| カテゴリ | 説明 | 推奨用途 |
|---------|------|---------|
| content_gap | 説明が不足している箇所 | 図解、イラスト |
| visual_break | 長文の区切りポイント | 装飾画像 |
| data_visualization | データ・統計の箇所 | グラフ、チャート |

### 画像目的分類

生成される各画像は以下のいずれかに分類:
- `hero`: アイキャッチ（記事冒頭）
- `illustration`: 概念の図解
- `data_viz`: データ可視化
- `break`: 視覚的休憩ポイント
- `cta_support`: CTA支援画像

### 品質チェックポイント

| 項目 | 基準 |
|------|------|
| 画像解像度 | 1200x800px以上 |
| alt属性 | 日本語で意味のある説明 |
| ファイルサイズ | 500KB以下（自動圧縮） |
| 配置バランス | 1000字あたり1-2枚 |

### スキップする場合

「画像生成をスキップ」を選択すると、画像なしで工程12に進みます。後から画像を追加したい場合は、工程11のみを再実行できます。

### よくあるエラーと対処

- **生成失敗**: 指示を具体的に修正してリトライ
- **著作権懸念**: 特定ブランド・人物を含む指示を避ける
- **サイズ不適合**: 指示に「横長」「16:9」などを追加',
    'workflow',
    80
)
ON CONFLICT (help_key) DO UPDATE SET
    title = EXCLUDED.title,
    content = EXCLUDED.content,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    updated_at = NOW();

-- ----------------------------------------------------------------------------
-- workflow.step12: WordPress Gutenberg形式変換
-- ----------------------------------------------------------------------------

INSERT INTO help_contents (help_key, title, content, category, display_order)
VALUES (
    'workflow.step12',
    '工程12: WordPress Gutenberg形式変換',
    '## 工程12: WordPress Gutenberg形式変換

4記事をWordPress Gutenbergブロック形式のHTMLに変換し、公開可能な状態にします。

### 処理内容

1. **依存データ読み込み**: step0（KW）、step6_5（構成）、step10（4記事）、step11（画像）
2. **Gutenbergブロック変換**: Markdown→WordPress互換HTML
3. **構造化データ付与**: Article/FAQPage JSON-LD
4. **メタデータ生成**: Yoast SEO互換フォーマット

### 出力例（Gutenbergブロック）

```html
<!-- wp:heading {"level":1} -->
<h1>SEOツール完全比較ガイド2025</h1>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>この記事では、主要なSEOツール10選を...</p>
<!-- /wp:paragraph -->

<!-- wp:image -->
<figure class="wp-block-image">
  <img src="data:image/png;base64,..." alt="SEOツール比較表"/>
</figure>
<!-- /wp:image -->
```

### 使用されるGutenbergブロック

| ブロック | 用途 |
|---------|------|
| wp-block-heading | H1-H4見出し |
| wp-block-paragraph | 本文段落 |
| wp-block-image | 画像（Base64埋め込み） |
| wp-block-list | 箇条書きリスト |
| wp-block-quote | 引用ブロック |
| wp-block-table | 比較表 |

### 品質チェックポイント

| 項目 | 基準 |
|------|------|
| HTML検証 | タグ閉じ漏れなし |
| 構造化データ | JSON-LD構文エラーなし |
| 画像alt属性 | 全画像に設定済み |
| WordPress互換 | 6.0+対応 |

### Yoast SEO連携（オプション）

```json
{
  "focus_keyword": "SEOツール 比較",
  "seo_title": "SEOツール完全比較...",
  "meta_description": "主要SEOツール10選を...",
  "readability_score": "good",
  "seo_score": "good"
}
```

### ダウンロード形式

- `article_1.html` 〜 `article_4.html`: 各記事のHTML
- `output.json`: 全記事のメタ情報・構造化データ
- `images/`: 画像ファイル（別途アップロード用）

### WordPressへの貼り付け方法

1. WordPress管理画面で「投稿」→「新規追加」
2. エディタを「コードエディタ」に切り替え
3. 生成されたHTMLを貼り付け
4. 「ビジュアルエディタ」に戻して確認
5. 画像をメディアライブラリにアップロードしURLを差し替え

### よくあるエラーと対処

- **HTMLタグ未閉じ**: 警告ログを確認し、手動で修正
- **画像URL相対パス**: WordPressアップロード後に絶対URLへ変更
- **ブロック認識失敗**: コメント形式（`<!-- wp:xxx -->`）が正しいか確認',
    'workflow',
    90
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
-- SELECT help_key, title, LENGTH(content) as content_length
-- FROM help_contents
-- WHERE help_key IN ('workflow.step4-6', 'workflow.step7', 'workflow.step8-9', 'workflow.step10', 'workflow.step11', 'workflow.step12')
-- ORDER BY display_order;
