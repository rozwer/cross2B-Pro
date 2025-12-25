# SEO記事自動生成ワークフロー

> **実装計画は `ROADMAP.md` を参照**

---

## 用語対応表

| 日本語               | 英語       | 説明                             |
| -------------------- | ---------- | -------------------------------- |
| 工程（step）         | step       | ワークフローの処理単位           |
| 成果物（artifact）   | artifact   | 各工程の出力ファイル             |
| 承認（approval）     | approval   | 人間による確認・許可             |
| 却下（rejection）    | rejection  | 人間による差し戻し               |
| 再実行（retry）      | retry      | 同一条件での工程再試行           |
| 部分再実行（resume） | resume     | 特定工程からの再開               |
| 検証（validation）   | validation | 出力の妥当性確認                 |
| フォールバック       | fallback   | 代替手段への自動切替（**禁止**） |

---

## 全体フロー

```
【半自動フロー】人間確認あり
工程-1 → 工程0 → 工程1 → 工程1.5 → 工程2 → 工程3A/3B/3C（並列）
                                                ↓
                                          [承認待ち]
                                                ↓
【全自動フロー】一気通貫実行
工程3.5 → 工程4 → 工程5 → 工程6 → 工程6.5 → 工程7A → 工程7B → 工程8 → 工程9 → 工程10 → 工程11 → 工程12
                                                                                    ↑          ↑
                                                                             4記事生成   画像生成   WP形式
```

## 工程一覧

| 工程  | 名称                    | AI         | 出力                     | 詳細                            |
| ----- | ----------------------- | ---------- | ------------------------ | ------------------------------- |
| -1    | 絶対条件ヒアリング      | 手動/UI    | スプレッドシート相当     | DB管理テンプレート対応          |
| 0     | キーワード選定          | Gemini     | `step0_keyword.json`     |                                 |
| 1     | 競合記事本文取得        | GAS/Tool   | `step1_competitors.csv`  | @backend/api.md#tools           |
| 1.5   | 競合記事品質スコア付与  | Gemini     | `step1_5_scored.json`    | 競合記事の品質評価              |
| 2     | CSV読み込み・検証       | Gemini     | （検証のみ）             |                                 |
| 3A    | クエリ分析・ペルソナ    | Gemini     | `step3a_query.json`      | 並列                            |
| 3B    | 共起語・関連KW抽出      | Gemini     | `step3b_keywords.json`   | 並列・**心臓部**                |
| 3C    | 競合分析・差別化        | Gemini     | `step3c_competitor.json` | 並列                            |
|       | **[承認待ち]**          |            |                          | @backend/temporal.md#approval   |
| 3.5   | Human Touch要素生成     | Gemini     | `step3_5_human.json`     | 感情分析・体験談・共感要素      |
| 4     | 戦略的アウトライン      | Claude     | `step4_outline.json`     | step3_5必須入力                 |
| 5     | 一次情報収集            | Gemini+Web | `step5_sources.json`     | @backend/api.md#tools           |
| 6     | アウトライン強化版      | Claude     | `step6_enhanced.json`    |                                 |
| 6.5   | 統合パッケージ化        | Claude     | `step6_5_package.md`     | **ファイル集約**                |
| 7A    | 本文生成 初稿           | Claude     | `step7a_draft.md`        |                                 |
| 7B    | ブラッシュアップ        | Gemini     | `step7b_polished.md`     |                                 |
| 8     | ファクトチェック・FAQ   | Gemini+Web | `step8_factcheck.json`   |                                 |
| 9     | 最終リライト            | Claude     | `step9_final.md`         |                                 |
| 10    | 最終出力（4記事）       | Claude     | `article_1-4.md/html`    | **4バリエーション生成**         |
| 11    | 画像生成                | Gemini+API | `step11_images.json`     | オプション（enable_images）     |
| 12    | WordPress形式変換       | Claude     | `step12_wp.html`         | Gutenbergブロック形式           |

### 工程10: 4記事バリエーション

| 記事番号 | タイプ     | ターゲット読者                   |
| -------- | ---------- | -------------------------------- |
| 1        | メイン記事 | SEOに関心があるすべての読者      |
| 2        | 初心者向け | SEO初心者、これから学び始める人  |
| 3        | 実践編     | 実践的なノウハウを求める中級者   |
| 4        | まとめ     | 要点だけを素早く把握したい人     |

各記事は`article_number`で識別され、WebSocket進捗イベントで記事単位の生成状況を通知。
監査ログには記事ごとの`output_digest`が記録される。

### 工程11: 画像生成（Human-in-the-loop）

工程11は画像生成のオプション工程で、APIを通じたHuman-in-the-loopフローで実行される。

#### フェーズ

| フェーズ | API エンドポイント                   | 説明                               |
| -------- | ------------------------------------ | ---------------------------------- |
| 11A      | `GET /step11/{run_id}/settings`      | 画像生成設定の取得                 |
| 11B      | `POST /step11/{run_id}/positions`    | 画像挿入位置の自動提案             |
| 11C      | `POST /step11/{run_id}/approve`      | 挿入位置の承認                     |
| 11D      | `POST /step11/{run_id}/instructions` | 各画像の生成指示を送信             |
| 11E      | `POST /step11/{run_id}/finalize`     | 画像をBase64エンコードして記事統合 |

#### 状態遷移（Temporal Signal）

```
[工程10完了] → waiting_image_input → [11A-11E API操作] → step11_skip signal → [工程12へ]
```

- `step11_phase`: `pending` → `waiting_image_input` → `skipped`
- API `finalize` が `step11/output.json` を保存後、`step11_skip` signalを送信
- Workflow側の `step11_mark_skipped` は既存データをチェックし、画像ありの場合は上書きしない（冪等性保証）

#### 出力スキーマ

```json
{
  "step": "step11",
  "enabled": true,
  "image_count": 2,
  "images": [
    {
      "article_number": 1,
      "position": "section_2",
      "alt_text": "画像の説明",
      "base64_data": "data:image/png;base64,..."
    }
  ],
  "markdown_with_images": "# タイトル\n\n![画像](data:image/png;base64,...)\n\n本文...",
  "html_with_images": "<h1>タイトル</h1><img src=\"data:image/png;base64,...\" alt=\"画像の説明\">..."
}
```

### 工程12: WordPress形式変換

工程12は工程10/11の成果物をWordPress Gutenbergブロック形式のHTMLに変換する。

#### 入力依存

| 依存工程 | 取得データ               |
| -------- | ------------------------ |
| step0    | キーワード設定           |
| step6_5  | 統合パッケージ（メタ）   |
| step10   | 4記事のMarkdown/HTML     |
| step11   | 画像データ（オプション） |

#### 処理フロー

1. 依存工程データの読み込み（`load_step_data`）
2. step11の画像データをarticleに統合（`images`配列）
3. 各記事をWordPress Gutenbergブロック形式に変換
4. `step12/output.json`として保存

#### 出力スキーマ

```json
{
  "step": "step12",
  "articles": [
    {
      "article_number": 1,
      "title": "記事タイトル",
      "slug": "article-slug",
      "category": "SEO",
      "tags": ["キーワード1", "キーワード2"],
      "meta_description": "メタディスクリプション",
      "wordpress_html": "<!-- wp:heading --><h1>タイトル</h1><!-- /wp:heading -->...",
      "images": [
        {
          "position": "section_2",
          "alt_text": "画像の説明",
          "base64_data": "data:image/png;base64,..."
        }
      ],
      "word_count": 3500,
      "seo_score": 85
    }
  ]
}
```

#### Gutenbergブロック形式

```html
<!-- wp:heading {"level":1} -->
<h1>タイトル</h1>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>本文テキスト</p>
<!-- /wp:paragraph -->

<!-- wp:image -->
<figure class="wp-block-image">
  <img src="data:image/png;base64,..." alt="画像の説明"/>
</figure>
<!-- /wp:image -->
```

## AI割り当てパターン

- **Gemini**: 分析、検索、自然な表現
- **Claude**: 構造化、統合、品質制御

詳細は @backend/llm.md を参照。

## 成果物パス規約

```
storage/{tenant_id}/{run_id}/{step}/output.json
```

詳細は @backend/database.md#storage を参照。

## 承認フロー

工程3（3A/3B/3C）完了後、工程4開始前に人間確認を挟む。

- Temporal signal で待機/再開
- approve/reject は監査ログ必須

詳細は @backend/temporal.md#approval を参照。

## 4本柱

| 柱         | 説明                                                   |
| ---------- | ------------------------------------------------------ |
| 神経科学   | 認知負荷3概念以内、脳の3領域への訴求                   |
| 行動経済学 | 6原則（損失回避/社会的証明/権威性/希少性/一貫性/好意） |
| LLMO       | 400-600 tokens/section、セクション独立性               |
| KGI        | CTA配置（Early/Mid/Final）                             |

## 用語集

| 用語           | 説明                              |
| -------------- | --------------------------------- |
| CTA            | Call To Action（問い合わせ誘導）  |
| データアンカー | 一次情報の引用                    |
| LLMO           | Large Language Model Optimization |
| 3フェーズ      | Anxiety → Understanding → Action  |

---

## エラーケース網羅

### 全工程共通

| エラーケース          | 期待挙動                                          |
| --------------------- | ------------------------------------------------- |
| LLM API Rate Limit    | exponential backoff で5分間リトライ → 失敗で停止  |
| LLM API タイムアウト  | 同一条件で最大3回リトライ → 失敗で停止            |
| 認証エラー（401/403） | 即座に失敗（NON_RETRYABLE）                       |
| JSON 構文破損         | 決定的修正（末尾カンマ除去等）を試行 → 失敗で停止 |
| スキーマ違反          | 即座に失敗（VALIDATION_FAIL）                     |
| Storage 書き込み失敗  | リトライ → 失敗で停止                             |

### 工程別エラー

| 工程     | エラーケース             | 期待挙動                                               |
| -------- | ------------------------ | ------------------------------------------------------ |
| 1        | SERP 結果 0件            | 即座に失敗（コンテンツなしで続行不可）                 |
| 1        | SERP API 障害            | リトライ3回 → 失敗で停止                               |
| 3A/3B/3C | 一部工程のみ失敗         | 失敗分のみリトライ（詳細は temporal.md#parallel 参照） |
| 5        | 一次情報 URL 全て 404    | 失敗（警告のみで続行は**禁止**）                       |
| 5        | 一部 URL のみ失敗        | 成功分のみで続行（ただしログ必須）                     |
| 8        | ファクトチェック矛盾検出 | 却下推奨フラグを立てる（自動修正は**禁止**）           |
| 10       | HTML バリデーション失敗  | 失敗で停止（壊れた HTML 出力は禁止）                   |
| 11       | 画像生成API失敗          | 画像なしで続行（warnings に記録）                      |
| 11       | step11_mark_skipped競合  | 既存データをチェックし上書きしない（冪等性保証）       |
| 12       | step11データ欠損         | images=[] として続行（画像なしHTML生成）               |
| 12       | HTMLタグ未閉じ検出       | 警告ログ出力、生成続行（バリデーション警告）           |

---

## 非機能要件

### 可用性

| 項目           | 目標値      | 備考                      |
| -------------- | ----------- | ------------------------- |
| システム稼働率 | 95%（月次） | ローカル運用のため控えめ  |
| 障害検知時間   | 5分以内     | ヘルスチェック + アラート |
| 障害復旧目標   | 30分以内    | 手動対応前提              |

### パフォーマンス

| 項目             | 目標値   | 備考                         |
| ---------------- | -------- | ---------------------------- |
| 全工程所要時間   | 60分以内 | 承認待ち時間除く             |
| 工程単体最大時間 | 10分     | 工程7A（長文生成）が最長     |
| 同時実行 run 数  | 10       | 単一 Temporal クラスタの限界 |

### データ保持期間

| 対象     | 保持期間 | 備考          |
| -------- | -------- | ------------- |
| 完了 run | 1年      | 成果物 + ログ |
| 失敗 run | 3ヶ月    | デバッグ用    |
| 監査ログ | 3年      | 削除不可      |

### セキュリティ要件

| 項目           | 要件                               |
| -------------- | ---------------------------------- |
| テナント分離   | 物理的 DB 分離必須                 |
| API キー       | 暗号化保存、平文ログ禁止           |
| 入力サニタイズ | プロンプトインジェクション対策必須 |
| 監査ログ       | 改ざん防止必須                     |
