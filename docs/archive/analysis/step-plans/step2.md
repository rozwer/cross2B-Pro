# 工程2: CSV読み込み・検証

## 入力スキーマ

```json
{
  "competitors": "CompetitorPage[] - step1から",
  "related_competitor_data": "RelatedKeywordData[] | null - step1.5から（オプション）"
}
```

## 出力スキーマ（既存）

```python
class Step2Output(BaseModel):
    step: str = "step2"
    is_valid: bool
    validation_summary: ValidationSummary
    validated_data: list[ValidatedCompetitor]
    rejected_data: list[RejectedRecord]
    validation_issues: list[dict]
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 検証項目 | URL, タイトル, 本文 | +文字数分析, 構造分析 |
| 品質スコア | 単純 | 詳細（4本柱観点） |
| 出力形式 | JSON | 正規化済みCSV + JSON |

### 追加フィールド（Pydantic モデル）

```python
class WordCountAnalysis(BaseModel):
    """競合記事の文字数分析."""
    min: int = Field(..., ge=0, description="最小文字数")
    max: int = Field(..., ge=0, description="最大文字数")
    average: float = Field(..., ge=0, description="平均文字数")
    median: float = Field(..., ge=0, description="中央値文字数")

class StructureAnalysis(BaseModel):
    """競合記事の構造分析."""
    avg_h2_count: float = Field(default=0.0, ge=0, description="平均H2見出し数")
    avg_h3_count: float = Field(default=0.0, ge=0, description="平均H3見出し数")
    common_patterns: list[str] = Field(default_factory=list, description="共通パターン（例: FAQ, まとめ, 比較表）")
```

---

## 実装タスク

### 1. スキーマ拡張（schemas/step2.py）

- [x] `WordCountAnalysis` モデル追加
- [x] `StructureAnalysis` モデル追加
- [x] `Step2Output` に以下を追加:
  ```python
  word_count_analysis: WordCountAnalysis | None = None
  structure_analysis: StructureAnalysis | None = None
  ```

### 2. Activity実装（step2.py）

- [x] `_compute_word_count_analysis()` メソッド追加
  - 既存 `validated_records` の `word_count` から min/max/average/median を算出
  - `statistics.median()` 使用

- [x] `_compute_structure_analysis()` メソッド追加
  - 既存 `headings` フィールドからH2/H3を分類
  - H2: `## ` または `<h2>` で始まるもの
  - H3: `### ` または `<h3>` で始まるもの
  - common_patterns: 50%以上で共通するセクション名を抽出

- [x] `execute()` に集計ロジック統合
  - バリデーション完了後、return前に集計を実行
  - 集計結果を `Step2Output` に追加

### 3. 品質スコア強化（オプション）

- [ ] `_compute_quality_score()` に4本柱観点を追加
  - 現状: word_count, headings, title長のみ
  - 追加検討: 構造の充実度（H2数）、パターン適合度

---

## テスト計画

### 単体テスト（tests/unit/worker/test_step2_analysis.py）

- [x] `WordCountAnalysis` / `StructureAnalysis` のバリデーション
- [x] `_compute_word_count_analysis()` の計算精度
  - 入力: [100, 200, 300, 400, 500] → min=100, max=500, avg=300, median=300
- [x] `_compute_structure_analysis()` のH2/H3分類
  - 入力: ["## はじめに", "### 詳細", "## まとめ"] → avg_h2=2, avg_h3=1
- [x] `_extract_heading_text()` のMarkdown/HTML対応

### 統合テスト

- [ ] step1 → step2 → step3 のデータフロー確認
- [ ] 新フィールドが step3 で参照可能か確認

---

## 実装ポイント

1. **後方互換性**: 新フィールドは `| None = None` でオプショナル
2. **既存ロジック維持**: バリデーション部分は変更なし、集計は追加のみ
3. **パフォーマンス**: 集計は O(n) で十分（競合記事は最大10件程度）

## 依存関係

- **前工程**: step1（competitors）、step1.5（オプション）
- **後工程**: step3a/3b/3c（word_count_analysis を参照可能）

## フロー変更の必要性

**なし**
