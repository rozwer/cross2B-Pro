# 工程6.5: 統合パッケージ（構成案作成）

## 入力スキーマ

```json
{
  "keyword": "string - step0から",
  "enhanced_outline": "Step6Output - step6から",
  "query_analysis": "Step3aOutput - step3aから",
  "cooccurrence_keywords": "KeywordItem[] - step3bから",
  "competitor_analysis": "Step3cOutput - step3cから",
  "primary_sources": "PrimarySource[] - step5から",
  "human_touch_elements": "Step3_5Output - step3.5から",
  "cta_specification": "object - step0から",
  "target_word_count": "number - 確定値（step0またはstep3cから）"
}
```

## 出力スキーマ（既存）

```python
class InputSummary(BaseModel):
    """入力データサマリー."""
    step_id: str
    available: bool
    key_points: list[str] = []
    data_quality: str = "unknown"  # good|fair|poor|unknown

class SectionBlueprint(BaseModel):
    """セクション設計図."""
    level: int = 2  # 1-4
    title: str = ""
    target_words: int = 0
    key_points: list[str] = []
    sources_to_cite: list[str] = []
    keywords_to_include: list[str] = []

class PackageQuality(BaseModel):
    """パッケージ品質."""
    is_acceptable: bool = True
    issues: list[str] = []
    warnings: list[str] = []
    scores: dict[str, float] = {}

class Step6_5Output(StepOutputBase):
    """Step6.5 の構造化出力."""
    step: str = "step6_5"
    integration_package: str = ""
    article_blueprint: dict[str, Any] = {}
    section_blueprints: list[SectionBlueprint] = []
    outline_summary: str = ""
    section_count: int = 0
    total_sources: int = 0
    input_summaries: list[InputSummary] = []
    inputs_summary: dict[str, bool] = {}
    quality: PackageQuality
    quality_score: float = 0.0
    handoff_notes: list[str] = []
    model: str = ""
    usage: dict[str, int] = {}
```

---

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 統合深度 | 基本 | ファイル集約ハブ（全工程成果物統合） |
| 執筆指示 | 概要（section_blueprints） | セクション別詳細論理展開 |
| 視覚要素 | なし | 図表配置指示 |
| 4本柱チェック | なし | 全セクション適合確認 |

---

## 追加スキーマ（詳細）

### ReferenceData

```python
class ReferenceData(BaseModel):
    """パート2: 参照データ."""
    keywords: list[str] = Field(default_factory=list, description="使用するキーワード")
    sources: list[str] = Field(default_factory=list, description="引用するソース")
    human_touch_elements: list[str] = Field(default_factory=list, description="人間味要素")
    cta_placements: list[str] = Field(default_factory=list, description="CTA配置")
```

### ComprehensiveBlueprint

```python
class ComprehensiveBlueprint(BaseModel):
    """包括的な構成案（パート1/2構成）."""
    part1_outline: str = Field(default="", description="構成案概要")
    part2_reference_data: ReferenceData = Field(
        default_factory=ReferenceData,
        description="参照データ集"
    )
```

### SectionExecutionInstruction

```python
class SectionExecutionInstruction(BaseModel):
    """セクション別の詳細執筆指示."""
    section_title: str = Field(..., description="セクションタイトル")
    logic_flow: str = Field(default="", description="論理展開の詳細")
    key_points: list[str] = Field(default_factory=list, description="必須含むポイント")
    sources_to_cite: list[str] = Field(default_factory=list, description="引用するソース")
    keywords_to_include: list[str] = Field(default_factory=list, description="含めるキーワード")
    human_touch_to_apply: list[str] = Field(default_factory=list, description="適用する人間味要素")
    word_count_target: int = Field(default=0, ge=0, description="目標文字数")
```

### VisualElementInstruction

```python
class VisualElementInstruction(BaseModel):
    """視覚要素の配置指示."""
    element_type: str = Field(..., description="要素タイプ（table/chart/diagram/image）")
    placement_section: str = Field(..., description="配置するセクション")
    content_description: str = Field(default="", description="内容の説明")
    purpose: str = Field(default="", description="目的・効果")
```

### FourPillarsFinalCheck

```python
class FourPillarsFinalCheck(BaseModel):
    """4本柱の最終適合チェック."""
    all_sections_compliant: bool = Field(default=False, description="全セクション適合")
    neuroscience_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="神経科学カバー率")
    behavioral_economics_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="行動経済学カバー率")
    llmo_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="LLMOカバー率")
    kgi_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="KGIカバー率")
    issues: list[str] = Field(default_factory=list, description="不適合の問題点")
    recommendations: list[str] = Field(default_factory=list, description="改善推奨事項")
```

---

## 実装タスク

### 6.5.1 スキーマ拡張（schemas/step6_5.py）`cc:TODO`

- [ ] `ReferenceData` モデル追加
- [ ] `ComprehensiveBlueprint` モデル追加（part1_outline, part2_reference_data）
- [ ] `SectionExecutionInstruction` モデル追加
- [ ] `VisualElementInstruction` モデル追加
- [ ] `FourPillarsFinalCheck` モデル追加
- [ ] `Step6_5Output` に新フィールド追加（Optional でデフォルト None）

**ファイル**: `apps/worker/activities/schemas/step6_5.py`

**追加フィールド（Step6_5Output）**:
```python
# blog.System 対応フィールド（後方互換性のため Optional）
comprehensive_blueprint: ComprehensiveBlueprint | None = Field(
    default=None,
    description="包括的構成案（パート1/2構成）"
)
section_execution_instructions: list[SectionExecutionInstruction] = Field(
    default_factory=list,
    description="セクション別詳細執筆指示"
)
visual_element_instructions: list[VisualElementInstruction] = Field(
    default_factory=list,
    description="視覚要素配置指示"
)
four_pillars_final_check: FourPillarsFinalCheck | None = Field(
    default=None,
    description="4本柱最終適合チェック"
)
```

### 6.5.2 Activity修正（step6_5.py）`cc:TODO`

- [ ] `_prepare_integration_input()` に `target_word_count`, `cta_specification` を追加
- [ ] LLM 出力パースに新フィールド抽出を追加
- [ ] `_build_section_execution_instructions()` メソッド追加
- [ ] `_build_visual_element_instructions()` メソッド追加
- [ ] `_check_four_pillars_compliance()` メソッド追加
- [ ] Step6_5Output 構築時に新フィールドを設定

**ファイル**: `apps/worker/activities/step6_5.py`

**修正箇所**:
1. `_prepare_integration_input()` メソッド（L274-288）
2. `execute()` メソッド（L226-250）- 出力構築部分

### 6.5.3 プロンプト更新 `cc:TODO`

- [ ] `apps/api/prompts/packs/default.json` の step6_5 セクションに追加指示
- [ ] セクション別詳細論理展開の出力指示
- [ ] 視覚要素配置指示の出力
- [ ] 4本柱チェック結果の出力
- [ ] JSON出力形式の明示

---

## テスト計画

### 単体テスト（schemas）`cc:TODO`

**ファイル**: `tests/unit/activities/test_step6_5_schemas.py`

- [ ] `test_comprehensive_blueprint_creation()`: ComprehensiveBlueprint の作成
- [ ] `test_section_execution_instruction_validation()`: SectionExecutionInstruction のバリデーション
- [ ] `test_visual_element_instruction_validation()`: VisualElementInstruction のバリデーション
- [ ] `test_four_pillars_final_check_coverage_range()`: カバー率が 0-1 の範囲
- [ ] `test_step6_5_output_backward_compatible()`: 新フィールドなしで動作確認
- [ ] `test_step6_5_output_with_new_fields()`: 新フィールド付きデータの動作確認

### 統合テスト `cc:TODO`

**ファイル**: `tests/integration/activities/test_step6_5.py`

- [ ] `test_step6_5_integration_with_all_inputs()`: 全入力データありでの統合
- [ ] `test_step6_5_section_instructions_generated()`: セクション指示が生成される
- [ ] `test_step6_5_four_pillars_check_populated()`: 4本柱チェックが設定される
- [ ] `test_step7a_receives_section_instructions()`: step7aへの引き継ぎ確認

---

## フロー変更の必要性

**なし** - スキーマ拡張のみ。Temporal Workflow 定義の変更は不要。

---

## 依存関係

### 上流（入力データ）
- **step0**: keyword, cta_specification, target_word_count
- **step3a**: query_analysis
- **step3b**: cooccurrence_keywords
- **step3c**: competitor_analysis, target_word_count（ai_*モード時）
- **step3_5**: human_touch_elements
- **step4**: strategic_outline
- **step5**: primary_sources
- **step6**: enhanced_outline

### 下流（出力利用）
- **step7a**: section_execution_instructions を参照して本文生成
- **step7b**: visual_element_instructions を参照して視覚要素追加

---

## 参照ファイル

| 種別 | ファイル |
|------|---------|
| スキーマ | `apps/worker/activities/schemas/step6_5.py` |
| Activity | `apps/worker/activities/step6_5.py` |
| プロンプト | `apps/api/prompts/packs/default.json` |
| blog.System参照 | `blog.System_prompts/工程6.5_統合パッケージ/` |

---

## 実装順序

1. **スキーマ拡張**（6.5.1）- 後方互換性テストを先に書く
2. **Activity修正**（6.5.2）- 新フィールドの抽出・設定
3. **プロンプト更新**（6.5.3）- 必要に応じて
4. **テスト**（全体）- 各段階で実施

---

## 重要ポイント

### ファイル集約ハブとしての役割

工程6.5は工程7以降の全ての参照データをここで統合する「ハブ」です。

- 工程0〜6の成果物を**すべて読み込み**
- 執筆に必要な情報を**構造化して整理**
- 工程7以降は**step6_5の出力のみ参照**すれば良い設計

### section_execution_instructions の重要性

工程7Aでの本文生成時に、各セクションの執筆指示として使用されます：
- `logic_flow`: 論理展開の詳細（PREP法ベース）
- `sources_to_cite`: 引用すべきソース
- `keywords_to_include`: 含めるべきキーワード
- `human_touch_to_apply`: 適用する人間味要素
- `word_count_target`: 目標文字数

### 4本柱最終チェック

工程4で設計した4本柱（神経科学・行動経済学・LLMO・KGI）が全セクションに適切に実装されているかを最終確認します。問題があれば `issues` に記録し、`recommendations` で改善案を提示します。

---

## 注意事項

- **後方互換性必須**: 新フィールドは全て Optional とし、既存データで動作すること
- **既存ロジック維持**: `_load_all_step_data()`, `_validate_package_quality()` は変更しない
- **チェックポイント維持**: CheckpointManager の動作は変更しない
