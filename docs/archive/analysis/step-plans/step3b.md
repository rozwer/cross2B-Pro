# 工程3B: 共起語・関連KW抽出（心臓部）

## 入力スキーマ

```json
{
  "keyword": "string - step0から",
  "competitor_summaries": "object[] - step2のvalidated_data"
}
```

## 出力スキーマ（既存）

```python
class Step3bOutput(BaseModel):
    primary_keyword: str
    cooccurrence_keywords: list[KeywordItem]  # min_length=5
    lsi_keywords: list[KeywordItem]
    long_tail_variations: list[str]
    keyword_clusters: list[KeywordCluster]
    recommendations: list[str]
    raw_analysis: str
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 共起語数 | 5個〜 | 100-150個 |
| 関連KW | 任意 | 30-50個 |
| 3フェーズ分類 | なし | Phase1/2/3へのKW配分 |
| LLMO最適化 | なし | 質問形式KW抽出 |

### 追加フィールド（必須）
```json
{
  "cooccurrence_count_target": 100,
  "related_count_target": 30,
  "three_phase_distribution": {
    "phase1_keywords": "KeywordItem[] - 不安・課題認識KW",
    "phase2_keywords": "KeywordItem[] - 理解・比較KW",
    "phase3_keywords": "KeywordItem[] - 行動・緊急KW"
  },
  "llmo_optimized_keywords": {
    "question_format": "string[] - 質問形式KW",
    "voice_search": "string[] - 音声検索対応KW"
  },
  "semantic_clusters": {
    "cluster_name": "string",
    "keywords": "string[]",
    "density_score": "number"
  }
}
```

## 実装タスク

- [ ] 共起語抽出数を100-150に拡張
- [ ] 3フェーズ分類ロジック追加
- [ ] LLMO最適化KW抽出追加
- [ ] プロンプト更新（詳細版）
- [ ] セマンティッククラスタリング追加

## テスト計画

- [ ] 100個以上の共起語抽出確認
- [ ] 3フェーズ分類の精度確認
- [ ] step4への引き継ぎ確認

## フロー変更の必要性

**なし** - 並列実行（3A/3B/3C）は既存のまま

## 注意

**心臓部** - 最も重要な工程。品質基準は厳格。
