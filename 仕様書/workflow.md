# SEO記事自動生成ワークフロー

> **実装計画は `ROADMAP.md` を参照**

## 全体フロー

```
【半自動フロー】人間確認あり
工程-1 → 工程0 → 工程1 → 工程2 → 工程3A/3B/3C（並列）
                                    ↓
                              [承認待ち]
                                    ↓
【全自動フロー】一気通貫実行
工程4 → 工程5 → 工程6 → 工程6.5 → 工程7A → 工程7B → 工程8 → 工程9 → 工程10
```

## 工程一覧

| 工程 | 名称 | AI | 出力 | 詳細 |
|------|------|-----|------|------|
| -1 | 絶対条件ヒアリング | 手動/UI | スプレッドシート相当 | |
| 0 | キーワード選定 | Gemini | `step0_keyword.json` | |
| 1 | 競合記事本文取得 | GAS/Tool | `step1_competitors.csv` | @backend/api.md#tools |
| 2 | CSV読み込み・検証 | Gemini | （検証のみ） | |
| 3A | クエリ分析・ペルソナ | Gemini | `step3a_query.json` | 並列 |
| 3B | 共起語・関連KW抽出 | Gemini | `step3b_keywords.json` | 並列・**心臓部** |
| 3C | 競合分析・差別化 | Gemini | `step3c_competitor.json` | 並列 |
| | **[承認待ち]** | | | @backend/temporal.md#approval |
| 4 | 戦略的アウトライン | Claude | `step4_outline.json` | |
| 5 | 一次情報収集 | Gemini+Web | `step5_sources.json` | @backend/api.md#tools |
| 6 | アウトライン強化版 | Claude | `step6_enhanced.json` | |
| 6.5 | 統合パッケージ化 | Claude | `step6_5_package.md` | **ファイル集約** |
| 7A | 本文生成 初稿 | Claude | `step7a_draft.md` | |
| 7B | ブラッシュアップ | Gemini | `step7b_polished.md` | |
| 8 | ファクトチェック・FAQ | Gemini+Web | `step8_factcheck.json` | |
| 9 | 最終リライト | Claude | `step9_final.md` | |
| 10 | 最終出力 | Claude | `final_article.*` | |

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

| 柱 | 説明 |
|----|------|
| 神経科学 | 認知負荷3概念以内、脳の3領域への訴求 |
| 行動経済学 | 6原則（損失回避/社会的証明/権威性/希少性/一貫性/好意） |
| LLMO | 400-600 tokens/section、セクション独立性 |
| KGI | CTA配置（Early/Mid/Final） |

## 用語集

| 用語 | 説明 |
|------|------|
| CTA | Call To Action（問い合わせ誘導） |
| データアンカー | 一次情報の引用 |
| LLMO | Large Language Model Optimization |
| 3フェーズ | Anxiety → Understanding → Action |
