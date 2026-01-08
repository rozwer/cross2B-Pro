# 工程12: WordPress用HTML生成

## 入力スキーマ

```json
{
  "step0_output": "object - キーワード情報",
  "step6_5_output": "object - 構成案",
  "step10_output": "object - 最終記事",
  "step11_output": "object - 画像提案",
  "tenant_id": "string",
  "run_id": "string"
}
```

## 出力スキーマ（既存）

```python
class Step12Output(BaseModel):
    step: str = "step12"
    articles: list[WordPressArticle]  # article_number, filename, html_content, gutenberg_blocks
    common_assets: CommonAssets
    generation_metadata: GenerationMetadata
    output_path: str
    output_digest: str
    warnings: list[str]
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| Gutenberg対応 | あり | 同等 |
| 画像統合 | あり | 同等 |
| メタデータ | 基本 | Yoast SEO対応強化 |

### 追加フィールド
```json
{
  "yoast_seo_metadata": {
    "focus_keyword": "string",
    "seo_title": "string",
    "meta_description": "string",
    "readability_score": "string - good/ok/needs_improvement",
    "seo_score": "string - good/ok/needs_improvement"
  },
  "gutenberg_block_types_used": "string[] - 使用ブロックタイプ一覧",
  "structured_data_blocks": {
    "article_schema": "string - JSON-LDブロック",
    "faq_schema": "string | null"
  }
}
```

## 実装タスク

### 1. スキーマ拡張（schemas/step12.py）

- [x] `YoastSeoMetadata` モデル追加
- [x] `StructuredDataBlocks` モデル追加
- [x] `WordPressArticle` に以下フィールド追加:
  - `yoast_seo_metadata: YoastSeoMetadata | None`
  - `gutenberg_block_types_used: list[str]`
  - `structured_data_blocks: StructuredDataBlocks | None`

### 2. Activity実装（step12.py）

- [x] `_generate_yoast_metadata()` メソッド追加
  - SEOタイトル生成（60文字以内）
  - メタディスクリプション調整（155文字以内）
  - 可読性スコア算出
  - SEOスコア算出
- [x] `_calculate_readability_score()` メソッド追加
  - 文の長さ、見出しの頻度で評価
- [x] `_calculate_seo_score()` メソッド追加
  - キーワード含有、密度、タイトル/メタ長で評価
- [x] `_generate_structured_data()` メソッド追加
  - Article JSON-LD生成
  - FAQ JSON-LD生成（step8データ連携）
- [x] `_collect_gutenberg_block_types()` メソッド追加
  - 使用ブロックタイプを抽出
- [x] `execute()` に集計ロジック統合

### 3. プロンプト更新（将来）

- [ ] Yoast SEO最適化を意識した生成指示

## テスト計画

### 単体テスト（tests/unit/worker/test_step12_analysis.py）

- [x] `YoastSeoMetadata` / `StructuredDataBlocks` のバリデーション
- [x] `_generate_yoast_metadata()` のタイトル/メタ調整
- [x] `_calculate_readability_score()` のスコアリング
- [x] `_calculate_seo_score()` のスコアリング
- [x] `_generate_structured_data()` のJSON-LD生成
- [x] `_collect_gutenberg_block_types()` のブロック抽出

### 統合テスト

- [ ] step10 → step12 のデータフロー確認
- [ ] 生成HTMLのWordPress互換性確認

## フロー変更の必要性

**なし**

---

## 工程13（将来検討）

**WordPress自動投稿** - セキュリティ考慮が必要なため、現時点では実装対象外。

flow-issues.mdに記録済み。
