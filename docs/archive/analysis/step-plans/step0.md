# 工程0: キーワード選定

## 入力スキーマ

### 既存（config経由）
```json
{
  "keyword": "string (必須)",
  "target_audience": "string (任意)",
  "target_cv": "string (任意)",
  "pack_id": "string (必須)"
}
```

### blog.System追加（工程-1相当、UI/フォーム対応）
```json
{
  // セクション1: 事業内容とターゲット
  "business_description": "string - 事業内容",
  "conversion_goal": "string - 目標CV（問い合わせ/資料DL等）",
  "target_persona": "string - ターゲット読者像",
  "company_strengths": "string - 自社の強み",

  // セクション2: キーワード選定
  "keyword": "string - メインキーワード（必須）",
  "search_volume": "number - 月間検索ボリューム（任意）",
  "competition": "string - 競合性（high/medium/low）",
  "related_keywords": "string[] - 関連キーワード（任意）",

  // セクション3: 記事戦略
  "strategy": "string - standard | topic_cluster",
  "cluster_topics": "string[] - 子記事トピック（topic_clusterの場合）",

  // セクション4: 文字数設定
  "word_count_mode": "string - manual | ai_seo_optimized | ai_readability | ai_balanced",
  "manual_word_count": "number | null - 手動指定時の文字数",

  // セクション5: CTA設定
  "cta_design_type": "string - single | staged",
  "cta_url": "string - CTA URL",
  "cta_text": "string - CTAテキスト",
  "cta_description": "string - 誘導先の説明"
}
```

---

## 出力スキーマ

### 既存（Step0Output）
```python
class Step0Output(BaseModel):
    step: str = "step0"
    keyword: str
    analysis: str  # LLM生テキスト

    # Parsed fields
    search_intent: str = ""
    difficulty_score: int = 5  # 1-10
    recommended_angles: list[str] = []
    target_audience: str = ""
    content_type_suggestion: str = ""

    # Metrics
    model: str = ""
    usage: dict[str, int] = {}
    metrics: dict[str, int] = {}
    quality: dict = {}
    parse_result: dict = {}
```

### blog.System 拡張
```json
{
  "step": "step0",
  "selected_keyword": "string - 選定キーワード",
  "search_volume": "number - 検索ボリューム",
  "competition": "string - high/medium/low",

  // 4本柱評価（新規）
  "four_pillars_evaluation": {
    "neuroscience": {
      "phase": "1 | 2 | 3",
      "brain_activation": "string - 扁桃体/前頭前野/線条体",
      "score": "number (0-100)"
    },
    "behavioral_economics": {
      "applicable_principles": ["string - 損失回避/社会的証明/権威性/一貫性/好意/希少性"],
      "score": "number (0-100)"
    },
    "llmo": {
      "citation_potential": "high | medium | low",
      "score": "number (0-100)"
    },
    "kgi": {
      "expected_cvr": "number (%)",
      "score": "number (0-100)"
    }
  },

  // 記事戦略（新規）
  "article_strategy": {
    "type": "comprehensive_guide | deep_dive | case_study | comparison | news_analysis | how_to",
    "strategy": "standard | topic_cluster",
    "background": {
      "why_now": "string",
      "target_pain": "string",
      "key_message": "string",
      "urgency": "high | medium | low"
    }
  },

  // 文字数設定（新規）
  "word_count_config": {
    "mode": "manual | ai_seo_optimized | ai_readability | ai_balanced",
    "target_word_count": "number | 'TBD_at_step3c'",
    "tolerance": {
      "min": "-300 (基本) / -500 (緩和)",
      "max": "+300"
    }
  },

  // CTA設計（新規）
  "cta_specification": {
    "design_type": "single | staged",
    "placements": {
      "early": { "position": 650, "url": "string", "text": "string" },
      "mid": { "position": 2800, "url": "string", "text": "string" },
      "final": { "position": "target_word_count - 500", "url": "string", "text": "string" }
    }
  },

  // 既存互換
  "analysis": "string - LLM生テキスト",
  "model": "string",
  "usage": {},
  "metrics": {}
}
```

---

## blog.System との差分

### 追加される要素
| 要素 | 説明 | 影響 |
|------|------|------|
| 4本柱評価 | 神経科学・行動経済学・LLMO・KGI | 出力スキーマ拡張 |
| 記事戦略設定 | type, strategy, background | 入出力スキーマ拡張 |
| 文字数モード | 4モード選択、工程3C連携 | 入出力スキーマ拡張 |
| CTA設計 | 3段階配置、CVR目標 | 出力スキーマ拡張 |
| ステップ・バイ・ステップ | タスク分割・承認待ち | プロンプト形式のみ |

### 変更される要素
| 要素 | 既存 | 変更後 |
|------|------|--------|
| difficulty_score | 1-10 | 4本柱スコア（各0-100）に分解 |
| content_type_suggestion | 自由記述 | 6タイプから選択 |

---

## 実装タスク

### Phase 1: スキーマ拡張 `cc:TODO`

#### 1.1 入力スキーマの型定義 `[feature:tdd]`
- [ ] `apps/worker/activities/schemas/step0.py` に以下の Pydantic モデルを追加:
  - `BusinessContext`: 事業情報（business_description, conversion_goal, target_persona, company_strengths）
  - `WordCountConfig`: 文字数設定（mode: Literal["manual", "ai_seo_optimized", "ai_readability", "ai_balanced"], manual_word_count: int | None, tolerance: dict）
  - `CTASpecification`: CTA設定（design_type: Literal["single", "staged"], placements: dict）
  - `Step0Input`: 全入力フィールドを統合（keyword, business_context, word_count_config, cta_specification, strategy, related_keywords）

#### 1.2 出力スキーマの拡張 `[feature:tdd]`
- [ ] `apps/worker/activities/schemas/step0.py` の `Step0Output` に以下を追加:
  - `FourPillarsEvaluation`: 4本柱評価モデル
    - `NeuroscienceEvaluation`: phase(1-3), brain_activation(扁桃体/前頭前野/線条体), score(0-100)
    - `BehavioralEconomicsEvaluation`: applicable_principles(list[str]), score(0-100)
    - `LLMOEvaluation`: citation_potential(Literal["high","medium","low"]), score(0-100)
    - `KGIEvaluation`: expected_cvr(float), score(0-100)
  - `ArticleStrategy`: type(6種類から選択), strategy(standard|topic_cluster), background(why_now, target_pain, key_message, urgency)
  - `word_count_config`: WordCountConfig を出力にも含める
  - `cta_specification`: CTASpecification を出力にも含める

#### 1.3 後方互換性の確保
- [ ] 既存フィールド（keyword, analysis, search_intent, difficulty_score, recommended_angles, target_audience, content_type_suggestion, model, usage, metrics, quality, parse_result）は全て残す
- [ ] 新フィールドは全て `Optional` で定義し、デフォルト値を設定
- [ ] `difficulty_score` は deprecated 扱いとし、`four_pillars_evaluation` の各スコアに移行推奨のコメントを追加

### Phase 2: プロンプト更新 `cc:TODO`

#### 2.1 v2プロンプトパック作成
- [ ] `apps/api/prompts/packs/v2_blog_system.json` を新規作成
- [ ] step0 セクションに以下を含める:
  - 4本柱評価の指示（神経科学、行動経済学、LLMO、KGI）
  - 記事タイプ6種類からの選択指示
  - ステップ・バイ・ステップの実行ルール
  - JSON出力形式の厳密な指定

#### 2.2 unified_knowledge対応
- [ ] `apps/api/prompts/loader.py` に `load_unified_knowledge()` メソッド追加
- [ ] `blog.System_prompts/工程0_キーワード選定/unified_knowledge.json` を読み込み、プロンプトに注入するロジック
- [ ] `v2_blog_system.json` に `knowledge_path` フィールド追加

#### 2.3 プロンプト変数の拡張
- [ ] `v2_blog_system.json` の step0.variables に以下を追加:
  - `business_description` (optional)
  - `conversion_goal` (optional)
  - `target_persona` (optional)
  - `company_strengths` (optional)
  - `word_count_mode` (optional, default: "ai_balanced")
  - `cta_design_type` (optional, default: "staged")

### Phase 3: Activity修正 `cc:TODO`

#### 3.1 入力処理の拡張
- [ ] `apps/worker/activities/step0.py` の `execute()` メソッドで:
  - config から新フィールド（business_description 等）を取得
  - `Step0Input` でバリデーション
  - プロンプトテンプレートに新変数を渡す

#### 3.2 出力パース処理の拡張
- [ ] `execute()` メソッド内の JSON パース後に:
  - `four_pillars_evaluation` の各フィールドを抽出
  - `article_strategy` を抽出
  - 欠落時のデフォルト値設定ロジック

#### 3.3 REQUIRED_ELEMENTS の更新
- [ ] `REQUIRED_ELEMENTS` に以下を追加:
  - `four_pillars`: ["4本柱", "神経科学", "行動経済学", "LLMO", "KGI"]
  - `article_type`: ["記事タイプ", "comprehensive_guide", "deep_dive", "case_study"]

### Phase 4: バリデーション `cc:TODO`

#### 4.1 FourPillarsValidator の実装
- [ ] `apps/worker/helpers/validators.py` に `FourPillarsValidator` クラス追加:
  - 各スコアが 0-100 の範囲内か検証
  - phase が 1-3 の範囲内か検証
  - citation_potential が high/medium/low のいずれかか検証

#### 4.2 ArticleStrategyValidator の実装
- [ ] `apps/worker/helpers/validators.py` に `ArticleStrategyValidator` クラス追加:
  - type が 6種類のいずれかか検証
  - strategy が standard/topic_cluster のいずれかか検証
  - urgency が high/medium/low のいずれかか検証

#### 4.3 step0 での統合
- [ ] `apps/worker/activities/step0.py` で新バリデータを使用
- [ ] バリデーション失敗時の適切なエラーハンドリング

---

## テスト計画

### ユニットテスト `cc:TODO`

#### スキーマテスト
- [ ] `tests/unit/worker/activities/schemas/test_step0.py` を作成:
  - `test_step0_output_with_defaults()`: デフォルト値のみで Step0Output が生成できること
  - `test_four_pillars_score_range()`: 各スコアが 0-100 の範囲外で ValidationError
  - `test_neuroscience_phase_range()`: phase が 1-3 の範囲外で ValidationError
  - `test_citation_potential_enum()`: high/medium/low 以外で ValidationError
  - `test_article_type_enum()`: 6種類以外で ValidationError
  - `test_urgency_enum()`: high/medium/low 以外で ValidationError
  - `test_backward_compatibility()`: 既存フィールドのみで Step0Output が生成できること

#### バリデータテスト
- [ ] `tests/unit/worker/helpers/test_validators.py` に追加:
  - `test_four_pillars_validator_valid()`: 正常な4本柱データでパス
  - `test_four_pillars_validator_invalid_score()`: スコア範囲外で失敗
  - `test_article_strategy_validator_valid()`: 正常な記事戦略でパス
  - `test_article_strategy_validator_invalid_type()`: 不正なタイプで失敗

#### Activity テスト
- [ ] `tests/unit/worker/activities/test_step0.py` に追加:
  - `test_execute_with_new_config_fields()`: 新フィールド付き config での実行
  - `test_execute_backward_compatible()`: 従来の config でも動作
  - `test_parse_four_pillars_from_llm_output()`: LLM出力から4本柱を抽出
  - `test_parse_article_strategy_from_llm_output()`: LLM出力から記事戦略を抽出

### 統合テスト `cc:TODO`

#### プロンプト互換性テスト
- [ ] `tests/integration/prompts/test_prompt_packs.py` に追加:
  - `test_default_pack_step0()`: default.json の step0 が動作すること
  - `test_v2_blog_system_pack_step0()`: v2_blog_system.json の step0 が動作すること
  - `test_unified_knowledge_loading()`: unified_knowledge.json が正しく読み込まれること

#### 工程間連携テスト
- [ ] `tests/integration/workflow/test_step0_to_step1.py` を作成:
  - `test_step0_output_passed_to_step1()`: step0 の出力が step1 に正しく渡ること
  - `test_four_pillars_propagation()`: 4本柱評価が後続工程で参照可能なこと
  - `test_cta_specification_propagation()`: CTA設定が後続工程で参照可能なこと

### E2Eテスト `cc:TODO`

- [ ] `tests/e2e/test_workflow_v2.py` に追加:
  - `test_full_workflow_with_v2_pack()`: v2_blog_system パックで全工程が動作すること（step0〜step12）

---

## フロー変更の必要性

**なし** - 工程-1（ヒアリング）はUI/API側で対応。Workflow自体の変更は不要。

ただし以下をflow-issues.mdに記録済み：
- 工程-1: UI側でフォーム追加、config経由でWorkflowに渡す

---

## 参照

- blog.System: `blog.System_prompts/工程0_キーワード選定/instructions.txt`
- blog.System: `blog.System_prompts/工程0_キーワード選定/unified_knowledge.json`
- 既存: `apps/worker/activities/schemas/step0.py`
- 既存: `apps/api/prompts/packs/default.json` (step0セクション)
