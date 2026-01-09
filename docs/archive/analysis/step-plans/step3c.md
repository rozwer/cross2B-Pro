# 工程3C: 競合分析・差別化切り口発見

## 入力スキーマ

```json
{
  "keyword": "string - step0から",
  "competitors": "ValidatedCompetitor[] - step2から",
  "word_count_mode": "string - step0から（manual/ai_seo_optimized/ai_readability/ai_balanced）"
}
```

## 出力スキーマ（既存）

```python
class Step3cOutput(BaseModel):
    keyword: str
    competitor_profiles: list[CompetitorProfile]
    market_overview: str
    differentiation_strategies: list[DifferentiationStrategy]
    gap_opportunities: list[GapOpportunity]
    content_recommendations: list[str]
    raw_analysis: str
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 分析深度 | 基本 | 5 Whys深層分析（3軸×5レベル） |
| 文字数分析 | なし | 競合平均→target_word_count算出 |
| 4本柱差別化 | なし | 各柱での差別化戦略 |
| ランキング要因 | なし | 上位表示要因分析（E-E-A-T） |
| 3フェーズ差別化 | なし | Phase1/2/3ごとの戦略 |
| CTA分析 | なし | 競合CTA配置・自社戦略 |

---

## 追加スキーマ（詳細）

### WordCountAnalysis

```python
class WordCountAnalysis(BaseModel):
    """競合記事の文字数分析."""
    mode: str  # word_count_mode をそのまま転記
    analysis_skipped: bool = False  # manual時はtrue
    skip_reason: str = ""
    target_keyword: str

    competitor_statistics: CompetitorStatistics
    article_details: list[ArticleDetail]  # 10件分

    ai_suggestion: AISuggestion | None  # ai_*モード時のみ
    ai_suggested_word_count: int | None  # 後方互換用
    rationale: str = ""  # 後方互換用

    target_word_count_range: WordCountRange | None  # ai_*モード時のみ
    note: str = ""  # 後工程への注意事項

class CompetitorStatistics(BaseModel):
    average_word_count: float
    median_word_count: float
    max_word_count: int
    min_word_count: int
    standard_deviation: float
    data_points: int  # 有効データ数

class ArticleDetail(BaseModel):
    rank: int
    title: str
    url: str
    word_count: int
    notes: str = ""  # 0文字の場合の理由等

class AISuggestion(BaseModel):
    ai_suggested_word_count: int
    suggestion_logic: str  # 算出ロジックの説明
    note: str = ""

class WordCountRange(BaseModel):
    min: int  # ai_suggested - 300
    min_relaxed: int  # ai_suggested - 500（下限緩和）
    max: int  # ai_suggested + 300（厳格）
    target: int  # ai_suggested そのまま
```

### RankingFactorAnalysis（5 Whys深層分析）

```python
class RankingFactorAnalysis(BaseModel):
    """上位表示要因・ユーザー満足深層分析."""
    analysis_summary: str  # 全体サマリー（200字程度）

    top_articles_deep_analysis: list[TopArticleAnalysis]  # 上位3記事

    common_ranking_factors: list[str]  # 共通要因（5-7個）
    satisfaction_patterns: SatisfactionPatterns
    actionable_insights: list[str]  # 後工程活用知見（5-10個）
    implications_for_our_article: ArticleImplications

class TopArticleAnalysis(BaseModel):
    rank: int
    title: str
    url: str
    satisfaction_deep_dive: SatisfactionDeepDive  # 3軸×5 Whys
    google_evaluation_factors: GoogleEvaluationFactors
    user_journey_fulfillment: str

class SatisfactionDeepDive(BaseModel):
    """3軸×5 Whys手法による満足要因の深掘り."""
    cognitive_satisfaction: FiveWhysAnalysis  # 認知的満足（頭で理解）
    emotional_satisfaction: FiveWhysAnalysis  # 感情的満足（心で安心）
    actionable_satisfaction: FiveWhysAnalysis  # 行動的満足（体で動ける）
    root_cause_categories_used: list[str]

class FiveWhysAnalysis(BaseModel):
    article_feature: str  # 分析対象の記事特徴
    level_1: str  # この特徴でユーザーが得られるもの
    level_2: str  # なぜそれが価値か
    level_3: str  # その価値がないとどんな問題か
    level_4: str  # 問題の背景にある課題
    level_5_root: str  # 根本ニーズ（カテゴリから選択）

class GoogleEvaluationFactors(BaseModel):
    experience: str  # E-E-A-Tの体験
    expertise: str  # 専門性
    authoritativeness: str  # 権威性
    trustworthiness: str  # 信頼性
    search_intent_fulfillment: str
    user_experience_signals: str

class SatisfactionPatterns(BaseModel):
    informational_satisfaction: list[str]
    emotional_satisfaction: list[str]
    actionable_satisfaction: list[str]

class ArticleImplications(BaseModel):
    must_include: list[str]  # 必ず含めるべき要素
    differentiation_opportunities: list[str]
    user_journey_design: str
```

### FourPillarsDifferentiation（4本柱差別化）

```python
class FourPillarsDifferentiation(BaseModel):
    """4本柱での差別化設計."""
    neuroscience: NeuroscienceDiff
    behavioral_economics: BehavioralEconomicsDiff
    llmo: LLMODiff
    kgi: KGIDiff

class NeuroscienceDiff(BaseModel):
    """神経科学での差別化（3フェーズ）."""
    phase1_fear_recognition: PhaseDiff  # 不安・課題認識
    phase2_understanding: PhaseDiff  # 理解・納得
    phase3_action: PhaseDiff  # 行動決定

class PhaseDiff(BaseModel):
    competitor_approach: str
    our_differentiation: str
    expected_effect: str  # 例: "扁桃体活性化+30%"

class BehavioralEconomicsDiff(BaseModel):
    """行動経済学6原則での差別化."""
    loss_aversion: PrincipleDiff  # 損失回避
    social_proof: PrincipleDiff  # 社会的証明
    authority: PrincipleDiff  # 権威性
    consistency: PrincipleDiff  # 一貫性
    liking: PrincipleDiff  # 好意
    scarcity: PrincipleDiff  # 希少性

class PrincipleDiff(BaseModel):
    competitor_approach: str
    our_differentiation: str

class LLMODiff(BaseModel):
    """LLMO（AI検索最適化）での差別化."""
    question_headings: QuestionHeadingsDiff
    section_independence: SectionIndependenceDiff
    expected_effect: str  # 例: "AI引用率+35%"

class QuestionHeadingsDiff(BaseModel):
    competitor_count: int  # 競合平均（例: 2個）
    our_target: int  # 自社目標（例: 5個以上）

class SectionIndependenceDiff(BaseModel):
    competitor_issue: str
    our_approach: str

class KGIDiff(BaseModel):
    """KGI（CVR向上）での差別化."""
    cta_placement: CTAPlacementDiff
    cta_appeal: CTAAppealDiff
    expected_effect: str  # 例: "CVR +50%"

class CTAPlacementDiff(BaseModel):
    competitor_average: float  # 競合平均CTA数
    our_strategy: str  # 3段階CTA（Early/Mid/Final）

class CTAAppealDiff(BaseModel):
    competitor_approach: str
    our_differentiation: str
```

### ThreePhaseDifferentiationStrategy（3フェーズ差別化）

```python
class ThreePhaseDifferentiationStrategy(BaseModel):
    """3フェーズごとの差別化戦略."""
    phase1: PhaseStrategy  # 不安・課題認識
    phase2: PhaseStrategy  # 理解・納得
    phase3: PhaseStrategy  # 行動決定

class PhaseStrategy(BaseModel):
    phase_name: str
    user_state: str  # このフェーズでのユーザー心理
    competitor_weakness: str
    our_differentiation: list[str]
    expected_metrics: str  # 期待効果
```

### CompetitorCTAAnalysis

```python
class CompetitorCTAAnalysis(BaseModel):
    """競合CTA分析."""
    cta_deployment_rate: float  # CTA設置率
    average_cta_count: float  # 平均CTA回数
    main_cta_positions: list[str]  # 主なCTA配置位置
    our_differentiation_strategy: str
```

---

## 実装タスク

### 4.1 スキーマ拡張（schemas/step3c.py）

- [ ] `WordCountAnalysis` 関連モデル追加
- [ ] `RankingFactorAnalysis` 関連モデル追加（5 Whys構造）
- [ ] `FourPillarsDifferentiation` 関連モデル追加
- [ ] `ThreePhaseDifferentiationStrategy` モデル追加
- [ ] `CompetitorCTAAnalysis` モデル追加
- [ ] `Step3cOutput` に新フィールド追加（Optional でデフォルト None）

### 4.2 プロンプト更新（default.json の step3c）

- [ ] 文字数統計算出指示を追加
- [ ] 5 Whys深層分析（3軸）の出力指示を追加
- [ ] 4本柱差別化設計の出力指示を追加
- [ ] 3フェーズ差別化戦略の出力指示を追加
- [ ] CTA分析指示を追加
- [ ] JSON出力形式の明示

### 4.3 Activity修正（step3c.py）

- [ ] 入力から `word_count_mode` を取得
- [ ] 文字数統計の算出ロジック実装
  - `ai_seo_optimized`: 平均+20%
  - `ai_readability`: 平均-10%
  - `ai_balanced`: 平均±5%
  - `manual`: スキップ
- [ ] LLM出力のパース処理を拡張（新フィールド対応）
- [ ] `target_word_count` 確定ロジック実装
- [ ] 品質検証に新フィールドのチェックを追加

### 4.4 品質バリデータ更新（Step3CQualityValidator）

- [ ] 4本柱キーワードのチェック追加
- [ ] 5 Whys構造の存在チェック
- [ ] target_word_count の妥当性チェック

---

## テスト計画

### 単体テスト

- [ ] `WordCountAnalysis` スキーマのバリデーション
- [ ] `RankingFactorAnalysis` スキーマのバリデーション
- [ ] `FourPillarsDifferentiation` スキーマのバリデーション
- [ ] 文字数算出ロジックの精度確認（各モード）
- [ ] target_word_count_range の算出確認

### 統合テスト

- [ ] モード別 target_word_count 確定確認
  - `ai_seo_optimized` → 平均+20%
  - `ai_readability` → 平均-10%
  - `ai_balanced` → 平均±5%
  - `manual` → スキップ（analysis_skipped=true）
- [ ] 4本柱差別化の整合性確認
- [ ] step4 への引き継ぎ確認（target_word_count, ranking_factor_analysis）

---

## フロー変更の必要性

**なし** - 並列実行（3A/3B/3C）は既存のまま

---

## 重要ポイント

### target_word_count 確定

- `ai_*` モードの場合、この工程で最終確定される
- 目標範囲: `target ± 300字`（基本）
- 下限緩和: `target - 500字`（冗長になる場合のみ）
- 上限: `target + 300字`（厳格）

### ranking_factor_analysis の後工程活用

この分析結果は以下の工程で参照・活用される：
- **工程4（アウトライン生成）**: 構成設計の根拠
- **工程7A（本文執筆）**: 各セクションの書き方の指針

### 5 Whys 根本原因カテゴリ

Level 5 の回答で使用するカテゴリ：
- 不確実性の解消
- 認知負荷の軽減
- 社会的リスクの回避
- 自己効力感の向上
- 時間/労力の節約
- 意思決定の正当化

---

## 参照ファイル

| ファイル | 用途 |
|---------|------|
| `blog.System_prompts/工程3C_.../instructions.txt` | blog.System の詳細要件 |
| `blog.System_prompts/工程3C_.../unified_knowledge.json` | テンプレート・例・チェックリスト |
| `apps/worker/activities/step3c.py` | 既存実装 |
| `apps/worker/activities/schemas/step3c.py` | 既存スキーマ |
