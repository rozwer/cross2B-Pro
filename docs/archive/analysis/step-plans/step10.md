# 工程10: 最終出力

## 入力スキーマ

```json
{
  "final_content": "Step9Output - step9から",
  "keyword": "string - step0から",
  "cta_specification": "object - step0から"
}
```

## 出力スキーマ（既存）

```python
class Step10Output(BaseModel):
    step: str = "step10"
    keyword: str

    # 4記事出力
    articles: list[ArticleVariation]  # article_number, variation_type, title, content, html_content
    metadata: Step10Metadata

    # 後方互換性
    article_title: str
    markdown_content: str
    html_content: str
    meta_description: str
    publication_checklist: str
    html_validation: HTMLValidationResult
    stats: ArticleStats
    publication_readiness: PublicationReadiness
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 記事数 | 4記事 | 1記事（メイン） |
| HTML形式 | 基本 | WordPress Gutenbergブロック |
| 構造化データ | なし | JSON-LD生成 |
| 公開チェック | 基本 | 詳細チェックリスト |

### 追加フィールド
```json
{
  "structured_data": {
    "json_ld": "object - Article schema",
    "faq_schema": "object | null - FAQPage schema"
  },
  "publication_checklist_detailed": {
    "seo_checklist": {
      "title_optimized": "boolean",
      "meta_description_present": "boolean",
      "headings_hierarchy_valid": "boolean",
      "internal_links_present": "boolean",
      "keyword_density_appropriate": "boolean"
    },
    "four_pillars_checklist": {
      "neuroscience_applied": "boolean",
      "behavioral_economics_applied": "boolean",
      "llmo_optimized": "boolean",
      "kgi_cta_placed": "boolean"
    },
    "technical_checklist": {
      "html_valid": "boolean",
      "images_have_alt": "boolean",
      "links_valid": "boolean"
    }
  },
  "word_count_report": {
    "target": "number",
    "achieved": "number",
    "variance": "number",
    "status": "string",
    "section_breakdown": "object"
  }
}
```

## 実装タスク

- [ ] `structured_data` でJSON-LD生成
- [ ] `publication_checklist_detailed` 詳細化
- [ ] `word_count_report` 最終レポート
- [ ] 4本柱チェックリスト統合
- [ ] プロンプト更新

## テスト計画

- [ ] HTML検証確認
- [ ] 構造化データ生成確認
- [ ] 公開チェックリスト確認
- [ ] step11への引き継ぎ確認

## フロー変更の必要性

**なし**

## 注意

既存は4記事生成だが、blog.Systemは1記事。**既存の4記事機能は維持**し、blog.System適用時はメイン記事のみ生成するモードを追加検討。
