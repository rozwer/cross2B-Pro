# 工程11: 画像生成（Human-in-the-loop）

## 入力スキーマ

```json
{
  "articles": "ArticleVariation[] - step10から",
  "keyword": "string - step0から"
}
```

## 出力スキーマ（既存）

```python
class Step11Output(BaseModel):
    step: str = "step11"
    enabled: bool
    image_count: int
    images: list[GeneratedImage]
    markdown_with_images: str
    html_with_images: str
    model: str
    usage: dict
    warnings: list[str]
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| サブステップ | 11A-11H | 同等 |
| 挿入位置分析 | あり | 記事構造ベース強化 |
| Human-in-the-loop | あり | 同等 |

### 追加フィールド
```json
{
  "position_analysis_enhanced": {
    "content_gap_positions": "EnhancedImageInsertionPosition[] - コンテンツギャップ分析",
    "visual_break_positions": "EnhancedImageInsertionPosition[] - 視覚的ブレーク推奨",
    "data_visualization_positions": "EnhancedImageInsertionPosition[] - データ可視化推奨",
    "total_recommended": "number",
    "analysis_summary": "string"
  },
  "image_purpose_classification": [
    {
      "image_index": "number",
      "purpose": "string - hero/illustration/data_viz/break/cta_support/process/comparison",
      "section_context": "string",
      "target_emotion": "string - 心理フェーズ対応の感情",
      "four_pillar_relevance": "string[] - 関連する4本柱"
    }
  ]
}
```

## 実装タスク

### スキーマ拡張（schemas/step11.py） `cc:完了`

- [x] `ImagePurpose` Enum追加
  - HERO, ILLUSTRATION, DATA_VIZ, BREAK, CTA_SUPPORT, PROCESS, COMPARISON
- [x] `EnhancedImageInsertionPosition` モデル追加
  - category (content_gap/visual_break/data_visualization)
  - priority (1-5)
  - recommendation_reason
- [x] `ImagePurposeClassification` モデル追加
  - image_index, purpose, section_context, target_emotion, four_pillar_relevance
- [x] `PositionAnalysisEnhanced` モデル追加
  - content_gap_positions, visual_break_positions, data_visualization_positions
  - total_recommended, analysis_summary
- [x] `Step11OutputV2` モデル追加（既存 `Step11Output` と並列、後方互換）

### Activity修正（step11.py） `cc:完了`

- [x] V2モード判定（`_is_v2_mode()`）
- [x] 4本柱キーワードパターン定義（`FOUR_PILLARS_PATTERNS`）
- [x] 画像目的キーワードパターン定義（`IMAGE_PURPOSE_PATTERNS`）
- [x] 画像目的分類（`_classify_image_purpose()`）
- [x] 4本柱関連性検出（`_detect_four_pillar_relevance()`）
- [x] 位置カテゴリ判定（`_categorize_position()`）
- [x] 拡張位置分析構築（`_build_position_analysis_enhanced()`）
- [x] 画像目的分類構築（`_build_image_purpose_classifications()`）
- [x] V2モード時の出力拡張

### プロンプト更新 `cc:TODO`

- [ ] `v2_blog_system.json` 用の詳細プロンプト作成
  - 3カテゴリ分類の指示
  - 4本柱関連性の指示

### テスト `cc:完了`

- [x] **スキーマテスト** (29テスト全パス)
  - `ImagePurpose` enumの値検証
  - `EnhancedImageInsertionPosition` のカテゴリ・優先度検証
  - `ImagePurposeClassification` の全フィールド検証
  - `PositionAnalysisEnhanced` の3カテゴリ構造検証
  - `Step11OutputV2` の後方互換性とシリアライズ
  - 既存スキーマの後方互換性検証

## テスト計画（残り）

- [ ] Activity単体テスト（LLMモック使用）
- [ ] 位置分析の精度確認（E2E）
- [ ] Human-in-the-loopフロー確認（E2E）
- [ ] step12への引き継ぎ確認（統合）

## フロー変更の必要性

**なし** - 既存のHuman-in-the-loopフローを維持
