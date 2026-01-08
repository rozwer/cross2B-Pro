# 工程3A: クエリ分析・ペルソナ深掘り

## 概要

検索キーワードの背後にある「真の疑問」を解明し、検索者のペルソナを詳細に描き出す工程。
blog.System Ver8.3 では行動経済学6原則と3フェーズ心理マッピングが追加され、記事全体の方向性を決定づける最重要工程となる。

## 入力スキーマ

```json
{
  "keyword": "string - step0から",
  "keyword_analysis": "object - step0のfour_pillars_evaluation",
  "competitor_count": "number - step2のvalidated_data.length",
  "competitor_data": "object[] - step2のvalidated_data（本文・見出し含む）"
}
```

## 出力スキーマ（既存）

```python
class SearchIntent(BaseModel):
    primary: Literal["informational", "navigational", "transactional", "commercial"]
    secondary: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

class UserPersona(BaseModel):
    name: str
    demographics: str = ""
    goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    search_context: str = ""

class Step3aOutput(BaseModel):
    keyword: str
    search_intent: SearchIntent
    personas: list[UserPersona] = Field(default_factory=list)
    content_expectations: list[str] = Field(default_factory=list)
    recommended_tone: str = ""
    raw_analysis: str
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 核心的疑問 | なし | core_question（メインQ + 派生Q） |
| ペルソナ深度 | 基本情報のみ | 詳細プロファイル + 感情状態 + 情報処理スタイル |
| 行動経済学 | なし | 6原則（損失回避〜希少性）の心理プロファイル |
| 3フェーズ | なし | Phase1/2/3心理マッピング + 脳活性領域 |
| CVR目標 | なし | Early/Mid/Final CTA別のCVR設定 |

---

## 追加スキーマ（詳細）

### 1. CoreQuestion（核心的疑問）

```python
class CoreQuestion(BaseModel):
    """検索者の核心的な疑問."""
    primary: str = Field(..., max_length=50, description="メインQuestion（50字以内）")
    underlying_concern: str = Field(..., max_length=100, description="根底にある懸念・欲求")
    time_sensitivity: Literal["high", "medium", "low"] = Field(default="medium")
    urgency_reason: str = Field(default="", description="緊急度の理由")
    sub_questions: list[str] = Field(default_factory=list, min_length=3, max_length=5)
```

### 2. QuestionHierarchy（疑問の階層構造）

```python
class QuestionHierarchy(BaseModel):
    """疑問の階層構造."""
    level_1_primary: list[str] = Field(..., min_length=3, max_length=5, description="一次的疑問")
    level_2_secondary: dict[str, list[str]] = Field(
        default_factory=dict,
        description="二次的疑問（一次疑問をキーに、各2-3個）"
    )
```

### 3. BehavioralEconomicsPrinciple（行動経済学原則）

```python
class BehavioralEconomicsPrinciple(BaseModel):
    """行動経済学の個別原則."""
    trigger: str = Field(..., description="トリガーとなる要素")
    examples: list[str] = Field(default_factory=list, min_length=2, max_length=5)
    content_strategy: str = Field(..., description="コンテンツでの活用方法")

class BehavioralEconomicsProfile(BaseModel):
    """行動経済学6原則のプロファイル."""
    loss_aversion: BehavioralEconomicsPrinciple  # 損失回避
    social_proof: BehavioralEconomicsPrinciple   # 社会的証明
    authority: BehavioralEconomicsPrinciple      # 権威性
    consistency: BehavioralEconomicsPrinciple    # 一貫性
    liking: BehavioralEconomicsPrinciple         # 好意
    scarcity: BehavioralEconomicsPrinciple       # 希少性
```

### 4. ThreePhaseMapping（3フェーズ心理マッピング）

```python
class PhaseState(BaseModel):
    """各フェーズの心理状態."""
    emotions: list[str] = Field(..., min_length=2, max_length=5)
    brain_trigger: str = Field(..., description="脳活性化トリガー")
    content_needs: list[str] = Field(default_factory=list)
    content_strategy: str = Field(default="")

class Phase1Anxiety(PhaseState):
    """Phase 1: 不安・課題認識（扁桃体活性）."""
    pass

class Phase2Understanding(PhaseState):
    """Phase 2: 理解・納得（前頭前野活性）."""
    logic_points: list[str] = Field(default_factory=list)
    comparison_needs: list[str] = Field(default_factory=list)

class Phase3Action(PhaseState):
    """Phase 3: 行動決定（線条体活性）."""
    action_barriers: list[str] = Field(default_factory=list)
    urgency_factors: list[str] = Field(default_factory=list)
    cvr_targets: dict[str, float] = Field(
        default_factory=lambda: {"early_cta": 3.0, "mid_cta": 4.0, "final_cta": 5.0}
    )

class ThreePhaseMapping(BaseModel):
    """3フェーズ心理マッピング."""
    phase1_anxiety: Phase1Anxiety
    phase2_understanding: Phase2Understanding
    phase3_action: Phase3Action
```

### 5. DetailedPersona（拡張ペルソナ）

```python
class SearchScenario(BaseModel):
    """検索シーン."""
    trigger_event: str
    search_timing: str
    device: str
    prior_knowledge: str
    expected_action: str
    conversion_likelihood: float = Field(ge=0, le=100)

class EmotionalState(BaseModel):
    """感情状態."""
    anxiety_level: Literal["high", "medium", "low"]
    anxiety_sources: list[str] = Field(default_factory=list)
    urgency: Literal["high", "medium", "low"]
    motivation_type: Literal["loss_aversion", "gain_seeking", "curiosity"]
    motivation_detail: str = ""
    openness_to_external_help: Literal["high", "medium", "low"] = "medium"

class DetailedPersona(BaseModel):
    """拡張ペルソナ."""
    # 基本情報（既存UserPersonaを拡張）
    name: str
    age: int = Field(ge=20, le=70)
    job_title: str
    company_size: str
    experience_years: int = Field(ge=0, le=40)
    department: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    # 課題・目標（既存を拡張）
    pain_points: list[str] = Field(default_factory=list, min_length=3, max_length=7)
    goals: list[str] = Field(default_factory=list, min_length=3, max_length=5)
    constraints: list[str] = Field(default_factory=list)
    # 新規追加
    search_scenario: SearchScenario
    emotional_state: EmotionalState
```

### 6. Step3aOutputV2（拡張出力スキーマ）

```python
class Step3aOutputV2(BaseModel):
    """Step 3A 拡張出力スキーマ（blog.System対応）."""
    # 既存フィールド（後方互換）
    keyword: str
    search_intent: SearchIntent
    personas: list[UserPersona] = Field(default_factory=list)  # 簡易版（後方互換）
    content_expectations: list[str] = Field(default_factory=list)
    recommended_tone: str = ""
    raw_analysis: str

    # 新規フィールド（blog.System対応）
    core_question: CoreQuestion | None = None
    question_hierarchy: QuestionHierarchy | None = None
    detailed_persona: DetailedPersona | None = None  # 詳細版
    behavioral_economics_profile: BehavioralEconomicsProfile | None = None
    three_phase_mapping: ThreePhaseMapping | None = None
```

---

## 実装タスク

### 4.1.1 スキーマ拡張（schemas/step3a.py） `cc:完了`

- [x] `CoreQuestion` モデル追加
- [x] `QuestionHierarchy` モデル追加
- [x] `BehavioralEconomicsPrinciple` / `BehavioralEconomicsProfile` モデル追加
- [x] `Phase1Anxiety` / `Phase2Understanding` / `Phase3Action` モデル追加
- [x] `ThreePhaseMapping` モデル追加
- [x] `SearchScenario` / `EmotionalState` モデル追加
- [x] `DetailedPersona` モデル追加
- [x] `Step3aOutputV2` モデル追加（既存 `Step3aOutput` を継承）

### 4.1.2 プロンプト更新 `cc:TODO`

- [ ] `default.json` の step3a プロンプトに4本柱対応を追加
- [ ] `v2_blog_system.json` 用の詳細プロンプト作成
  - 核心的疑問抽出の指示
  - 行動経済学6原則の分析指示
  - 3フェーズ心理マッピングの生成指示
  - JSON出力形式の明示

### 4.1.3 Activity修正（step3a.py） `cc:完了`

- [x] `REQUIRED_ELEMENTS` に新フィールドのパターン追加
  ```python
  REQUIRED_ELEMENTS = {
      "search_intent": [...],
      "persona": [...],
      "pain_points": [...],
      # 新規追加
      "core_question": ["核心的", "メインQuestion", "main_question"],
      "behavioral_economics": ["損失回避", "社会的証明", "loss_aversion"],
      "three_phase": ["Phase 1", "Phase 2", "phase1", "phase2"],
  }
  ```
- [x] `execute()` のパース処理を拡張
  - `core_question` の抽出
  - `behavioral_economics_profile` の抽出
  - `three_phase_mapping` の抽出
- [x] 入力に `competitor_data`（step2から）を追加
- [x] 品質検証に新フィールドの存在チェックを追加
- [x] 出力形式を `Step3aOutputV2` に対応
- [x] V2モード判定（`pack_id` による自動切替）
- [x] V2モード用の厳格なバリデーション
- [x] `_extract_v2_fields()` メソッドで blog.System 形式からのフィールド抽出

### 4.1.4 テスト追加 `cc:完了`

- [x] **スキーマテスト** (36テスト全パス)
  - `CoreQuestion` のバリデーション
  - `BehavioralEconomicsProfile` の6原則
  - `ThreePhaseMapping` の構造検証
  - `SearchScenario` / `EmotionalState` / `DetailedPersona`
  - `Step3aOutputV2` の後方互換性とシリアライズ
- [ ] **Activity単体テスト** (要実装: LLM モック使用)
  - 新フィールドが正しくパースされることの確認
  - 後方互換性の確認（旧形式出力も動作）
- [ ] **統合テスト** (要実装: 実データ使用)
  - step0/step1/step2 → step3a のデータフロー確認
  - step3a → step4/step3.5 への引き継ぎ確認
- [ ] **品質テスト** (要実装: E2E)
  - 行動経済学6原則すべてが出力されること
  - 3フェーズすべてに`emotions`と`content_strategy`があること

---

## 依存関係

### 入力元
- **step0**: keyword, four_pillars_evaluation
- **step1**: competitor_pages
- **step2**: validated_data（本文・見出し含む）

### 出力先
- **step3.5**: three_phase_mapping（感情データ）
- **step4**: core_question, question_hierarchy, behavioral_economics_profile, three_phase_mapping
- **step6**: detailed_persona（執筆トーン設計）
- **step7a**: three_phase_mapping（CTA配置）

---

## フロー変更の必要性

**なし** - 並列実行（3A/3B/3C）は既存のまま維持

ただし、step3a の出力が step3.5/step4/step6/step7a で参照されるため、
出力スキーマの拡張は後続工程に影響する。

---

## 実装優先度

| タスク | 優先度 | 理由 |
|--------|--------|------|
| スキーマ拡張 | 高 | 後続タスクの前提 |
| プロンプト更新 | 高 | LLM出力形式を決定 |
| Activity修正 | 中 | スキーマ完成後に対応 |
| テスト追加 | 中 | 実装完了後に対応 |

---

## 参考: unified_knowledge.json の活用

blog.System の `工程3A_【並列処理】クエリ分析・ペルソナ深掘り/unified_knowledge.json` には以下が含まれる：

- **guidelines**: 詳細なガイドライン（Markdown形式）
- **templates**: JSON出力テンプレート
- **examples**: 具体的な出力例
- **checklist**: 4本柱チェックリスト

プロンプト作成時はこれらを参照し、特に `templates.output_template_complete` の構造に準拠すること。
