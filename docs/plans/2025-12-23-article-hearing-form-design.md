# 工程-1：記事絶対条件ヒアリングフォーム設計

## 概要

ワークフロー開始前の入力フォームを「工程-1：記事絶対条件ヒアリング」として再設計する。
既存の簡易入力（keyword, target_audience, competitor_urls, additional_requirements）を完全置換し、
6セクション構成の詳細ヒアリングフォームに移行する。

## 決定事項

| 項目 | 決定 |
|------|------|
| 既存入力との関係 | 完全置換 |
| キーワード未定時のフロー | 同期フロー（フォーム内でLLM呼び出し→10候補表示→選択） |
| 競合URL取得 | 工程内でAI自動取得（将来的にGoogle Ads API連携） |
| CTA挿入位置 | 3モード切り替え可能（固定位置/比率動的/AI任せ） |
| UI形式 | ウィザード形式（ステップバイステップ） |
| DB保存形式 | セクション別グループ化したフラット構造 |
| キーワード候補生成 | 固定モデル（高速）+ 検索ボリューム推定表示 |

## フォーム構成

### セクション1：事業内容とターゲット

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| business_description | string | ○ | 事業内容の詳細 |
| target_cv | enum | ○ | 目標CV（inquiry/document_request/free_consultation/other） |
| target_cv_other | string | △ | target_cv="other"の場合のみ |
| target_audience | string | ○ | ターゲット読者像 |
| company_strengths | string | ○ | 自社の強み |

### セクション2：キーワード選定

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| keyword_status | enum | ○ | decided（決定済）/ undecided（未定） |
| main_keyword | string | △ | keyword_status="decided"の場合のみ |
| monthly_search_volume | string | △ | 月間検索ボリューム（例: "100-200"） |
| competition_level | enum | △ | high/medium/low |
| theme_topics | string | △ | keyword_status="undecided"の場合、書きたいテーマ |
| selected_keyword | object | △ | LLM候補から選択した結果 |
| related_keywords | array | - | 関連キーワード一覧（任意） |

### セクション3：記事戦略

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| article_style | enum | ○ | standalone（標準）/ topic_cluster（親子構成） |
| child_topics | array | △ | article_style="topic_cluster"の場合、子記事トピック |

### セクション4：文字数設定

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| word_count_mode | enum | ○ | manual/ai_seo_optimized/ai_readability/ai_balanced |
| target_word_count | number | △ | word_count_mode="manual"の場合、文字数上限 |

### セクション5：CTA設定

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| cta_type | enum | ○ | single（単一）/ staged（段階的） |
| cta_position_mode | enum | ○ | fixed（固定位置）/ ratio（比率）/ ai（AI任せ） |
| single_cta | object | △ | cta_type="single"の場合 |
| staged_cta | object | △ | cta_type="staged"の場合 |

#### single_cta構造
```json
{
  "url": "https://...",
  "text": "CTAテキスト",
  "description": "誘導先の説明"
}
```

#### staged_cta構造
```json
{
  "early": { "url": "...", "text": "...", "description": "...", "position": 650 },
  "mid": { "url": "...", "text": "...", "description": "...", "position": 2800 },
  "final": { "url": "...", "text": "...", "description": "..." }
}
```

### セクション6：最終確認

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| confirmed | boolean | ○ | 入力内容の確認 |

## DB保存形式（input_data JSONB）

```json
{
  "business": {
    "description": "派遣社員向けeラーニングサービス",
    "target_cv": "inquiry",
    "target_cv_other": null,
    "target_audience": "派遣会社の教育担当者、人事部長、30〜40代",
    "company_strengths": "中小企業特化、低予算での教育プラン提供"
  },
  "keyword": {
    "status": "decided",
    "main_keyword": "派遣社員 教育方法",
    "monthly_search_volume": "100-200",
    "competition_level": "medium",
    "theme_topics": null,
    "selected_keyword": null,
    "related_keywords": [
      { "keyword": "派遣社員 研修プログラム", "volume": "50-100" }
    ]
  },
  "strategy": {
    "article_style": "standalone",
    "child_topics": null
  },
  "word_count": {
    "mode": "ai_balanced",
    "target": null
  },
  "cta": {
    "type": "single",
    "position_mode": "fixed",
    "single": {
      "url": "https://cross-learning.jp/",
      "text": "クロスラーニングの詳細を見る",
      "description": "クロスラーニング広報サイトのTOPページ"
    },
    "staged": null
  },
  "confirmed": true
}
```

## API設計

### 1. キーワード候補生成エンドポイント

```
POST /api/keywords/suggest
```

**Request:**
```json
{
  "theme_topics": "派遣社員の教育方法について知りたい\n派遣社員の定着率を高める方法",
  "business_description": "派遣社員向けeラーニングサービス",
  "target_audience": "派遣会社の教育担当者"
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "keyword": "派遣社員 教育方法",
      "estimated_volume": "100-200",
      "estimated_competition": "medium",
      "relevance_score": 0.95
    },
    ...
  ],
  "model_used": "gemini-2.0-flash",
  "generated_at": "2025-12-23T12:00:00Z"
}
```

### 2. Run作成エンドポイント（更新）

```
POST /api/runs
```

**Request（新形式）:**
```json
{
  "input": {
    "business": { ... },
    "keyword": { ... },
    "strategy": { ... },
    "word_count": { ... },
    "cta": { ... },
    "confirmed": true
  },
  "model_config": { ... },
  "step_configs": [ ... ],
  "tool_config": { ... },
  "options": { ... }
}
```

## フロントエンド設計

### コンポーネント構成

```
components/runs/
├── RunCreateWizard.tsx          # ウィザードコンテナ
├── wizard/
│   ├── WizardProgress.tsx       # プログレスバー
│   ├── WizardNavigation.tsx     # 戻る/次へボタン
│   ├── steps/
│   │   ├── Step1Business.tsx    # セクション1
│   │   ├── Step2Keyword.tsx     # セクション2
│   │   ├── Step3Strategy.tsx    # セクション3
│   │   ├── Step4WordCount.tsx   # セクション4
│   │   ├── Step5CTA.tsx         # セクション5
│   │   └── Step6Confirm.tsx     # セクション6
│   └── KeywordSuggestion.tsx    # キーワード候補生成UI
└── RunCreateForm.tsx            # 既存（削除対象）
```

### 状態管理

```typescript
interface WizardState {
  currentStep: number;
  formData: ArticleHearingInput;
  keywordSuggestions: KeywordSuggestion[] | null;
  isLoadingSuggestions: boolean;
  validationErrors: Record<string, string>;
}
```

## 実装順序

1. **バックエンド: スキーマ定義**
   - `ArticleHearingInput` Pydanticモデル作成
   - 既存 `RunInput` を置換

2. **バックエンド: キーワード候補API**
   - `/api/keywords/suggest` エンドポイント追加
   - Gemini Flash でキーワード生成

3. **フロントエンド: ウィザードコンポーネント**
   - `RunCreateWizard.tsx` 作成
   - プログレスバー、ナビゲーション実装

4. **フロントエンド: 各ステップ実装**
   - Step1〜6の個別コンポーネント
   - 条件分岐ロジック

5. **フロントエンド: キーワード候補UI統合**
   - API呼び出し
   - 候補表示・選択UI

6. **統合テスト**
   - フォーム送信〜ワークフロー開始の確認

## マイグレーション

既存の `input_data` との互換性：
- 新形式には `input.business.description` に `keyword` が含まれる想定
- 既存データは読み取り専用として維持
- 新規作成は全て新形式を使用
