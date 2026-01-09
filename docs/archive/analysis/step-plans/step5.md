# 工程5: 一次情報収集

## 概要

キーワードとアウトラインに基づき、信頼性の高い一次情報（学術論文、政府レポート、統計データ等）を収集し、3フェーズ（不安喚起→理解納得→行動決定）に分類して各セクションへの配置を提案する。

---

## 入力スキーマ

```json
{
  "keyword": "string - step0から",
  "outline": "string - step4から",
  "sections": "OutlineSection[] - step4から",
  "competitor_analysis": "Step3COutput - step3cから（知識ギャップ発見用）"
}
```

**入力元**:
- `step4.outline` - 戦略的アウトライン（必須）
- `step4.sections` - セクション構造
- `step3c.competitor_analysis` - 競合分析結果（知識ギャップ発見用）

---

## 出力スキーマ（既存）

```python
class PrimarySource(BaseModel):
    url: str
    title: str
    source_type: Literal["academic_paper", "government_report", "statistics",
                         "official_document", "industry_report", "news_article", "other"]
    excerpt: str  # max_length=500
    credibility_score: float  # 0.0-1.0
    verified: bool

class CollectionStats(BaseModel):
    total_collected: int
    total_verified: int
    failed_queries: int

class Step5Output(BaseModel):
    step: str = "step5"
    keyword: str
    search_queries: list[str]
    sources: list[PrimarySource]
    invalid_sources: list[PrimarySource]
    failed_queries: list[dict[str, str]]
    collection_stats: CollectionStats
```

---

## blog.System との差分

| 観点 | 既存実装 | blog.System | 対応方針 |
|------|----------|-------------|----------|
| ソースタイプ | 7種類 | 同等 | 維持 |
| 3フェーズ分類 | なし | phase1/2/3必須 | **Phase 1** |
| 知識ギャップ | なし | 5-10個必須 | **Phase 1** |
| セクション配置 | なし | 全セクションにマッピング | **Phase 2** |
| 鮮度スコア | なし | freshness_score | **Phase 2** |
| 行動経済学効果 | なし | psychological_effect | **Phase 3** |

---

## 実装フェーズ

### Phase 1: 3フェーズ分類と知識ギャップ `cc:DONE`

blog.Systemの最重要要件：ソースの3フェーズ分類と知識ギャップ発見。

#### 1.1 スキーマ拡張

**ファイル**: `apps/worker/activities/schemas/step5.py`

**PrimarySource に追加**:
```python
class PrimarySource(BaseModel):
    # 既存フィールド...
    phase_alignment: Literal["phase1_anxiety", "phase2_understanding", "phase3_action"] = "phase2_understanding"
    freshness_score: float = 0.5  # 0.0-1.0
    data_points: list[DataPoint] = []

class DataPoint(BaseModel):
    metric: str                  # 指標名
    value: str                   # 値
    previous_year: str = ""      # 前年値
    change: str = ""             # 変化率
    context: str = ""            # 文脈
```

**Step5Output に追加**:
```python
class PhaseData(BaseModel):
    description: str
    sources: list[str]  # source IDs
    total_count: int
    key_data_summary: list[str]
    usage_sections: list[str]

class PhaseSpecificData(BaseModel):
    phase1_anxiety: PhaseData
    phase2_understanding: PhaseData
    phase3_action: PhaseData

class KnowledgeGap(BaseModel):
    gap_id: str                  # "KG001"
    gap_description: str
    competitor_coverage: str     # "0/10記事"
    primary_source_id: str | None
    implementation_section: str
    differentiation_value: Literal["high", "medium", "low"]

class Step5Output(BaseModel):
    # 既存フィールド...
    phase_specific_data: PhaseSpecificData | None = None
    knowledge_gaps_filled: list[KnowledgeGap] = []
```

#### 1.2 3フェーズ分類ロジック

**ファイル**: `apps/worker/activities/step5.py`

**変更内容**:
```python
# 各ソースのphase_alignmentを判定
def _classify_phase(self, source: dict, keyword: str) -> str:
    """ソースを3フェーズに分類"""
    source_type = source.get("source_type", "")
    excerpt = source.get("excerpt", "").lower()

    # Phase 1 (不安喚起): 問題の深刻さ、リスク、損失
    phase1_indicators = ["リスク", "問題", "損失", "減少", "危険", "失敗", "課題"]

    # Phase 2 (理解納得): 解決策、方法、効果
    phase2_indicators = ["方法", "解決", "効果", "改善", "手順", "ステップ"]

    # Phase 3 (行動決定): 成功事例、導入実績、費用対効果
    phase3_indicators = ["成功", "事例", "導入", "実績", "満足", "達成"]

    # キーワードマッチでスコアリング
    phase1_score = sum(1 for ind in phase1_indicators if ind in excerpt)
    phase2_score = sum(1 for ind in phase2_indicators if ind in excerpt)
    phase3_score = sum(1 for ind in phase3_indicators if ind in excerpt)

    if phase1_score > phase2_score and phase1_score > phase3_score:
        return "phase1_anxiety"
    elif phase3_score > phase1_score and phase3_score > phase2_score:
        return "phase3_action"
    else:
        return "phase2_understanding"
```

**テスト**:
- [x] 各ソースにphase_alignmentが付与されること
- [x] phase_specific_dataが正しく集計されること

#### 1.3 知識ギャップ発見ロジック

**ファイル**: `apps/worker/activities/step5.py`

**変更内容**:
```python
async def _find_knowledge_gaps(
    self,
    ctx: ExecutionContext,
    step3c_data: dict | None,
    collected_sources: list[dict],
) -> list[dict]:
    """step3c競合分析から知識ギャップを発見"""
    gaps = []

    if not step3c_data:
        return gaps

    # 競合カバレッジの低いトピックを抽出
    weak_topics = step3c_data.get("differentiation_angles", [])

    for i, topic in enumerate(weak_topics[:10]):  # 最大10個
        # 収集したソースで対応可能か確認
        matching_source = None
        for source in collected_sources:
            if topic.get("keyword", "") in source.get("excerpt", ""):
                matching_source = source.get("url")
                break

        gaps.append({
            "gap_id": f"KG{i+1:03d}",
            "gap_description": topic.get("description", ""),
            "competitor_coverage": topic.get("coverage", "不明"),
            "primary_source_id": matching_source,
            "implementation_section": topic.get("recommended_section", ""),
            "differentiation_value": "high" if topic.get("coverage", "").startswith("0") else "medium",
        })

    return gaps
```

**テスト**:
- [x] step3cデータから知識ギャップが抽出されること
- [x] 収集ソースとのマッチングが動作すること
- [x] step3cがない場合、空リストで正常終了すること

---

### Phase 2: セクション配置と鮮度スコア `cc:DONE`

#### 2.1 セクション配置マッピング

**ファイル**: `apps/worker/activities/schemas/step5.py`

**追加スキーマ**:
```python
class SectionSourceMapping(BaseModel):
    section_id: str              # "introduction", "H2-1", etc.
    section_title: str
    assigned_sources: list[str]  # source URLs
    source_type_priority: list[str]
    enhancement_notes: str = ""

class Step5Output(BaseModel):
    # 既存フィールド...
    section_source_mapping: list[SectionSourceMapping] = []
```

**ファイル**: `apps/worker/activities/step5.py`

**変更内容**:
```python
def _map_sources_to_sections(
    self,
    sources: list[dict],
    sections: list[dict],
) -> list[dict]:
    """ソースを各セクションに割り当て"""
    mappings = []

    for section in sections:
        section_id = section.get("id", "")
        section_title = section.get("title", "")

        # セクション位置からフェーズを推定
        if section_id in ["introduction", "H2-1", "H2-2"]:
            target_phase = "phase1_anxiety"
        elif section_id in ["H2-11", "H2-12", "conclusion"]:
            target_phase = "phase3_action"
        else:
            target_phase = "phase2_understanding"

        # 該当フェーズのソースを優先的に割り当て
        assigned = [
            s["url"] for s in sources
            if s.get("phase_alignment") == target_phase
        ][:3]  # 最大3ソース

        mappings.append({
            "section_id": section_id,
            "section_title": section_title,
            "assigned_sources": assigned,
            "source_type_priority": ["statistics", "government_report", "academic_paper"],
            "enhancement_notes": f"{target_phase}向けデータ配置",
        })

    return mappings
```

**テスト**:
- [x] 各セクションにソースが割り当てられること
- [x] 導入部にはPhase1ソース、結論部にはPhase3ソースが優先されること

#### 2.2 鮮度スコア計算

**ファイル**: `apps/worker/activities/step5.py`

**変更内容**:
```python
from datetime import datetime

def _calculate_freshness_score(self, publication_date: str | None) -> float:
    """ソースの鮮度スコアを計算（0.0-1.0）"""
    if not publication_date:
        return 0.5  # 不明な場合は中間値

    try:
        # 年のみの場合
        if len(publication_date) == 4:
            pub_year = int(publication_date)
        else:
            pub_year = datetime.fromisoformat(publication_date).year

        current_year = datetime.now().year
        age = current_year - pub_year

        if age <= 0:
            return 1.0
        elif age == 1:
            return 0.9
        elif age == 2:
            return 0.7
        elif age == 3:
            return 0.5
        else:
            return max(0.1, 0.5 - (age - 3) * 0.1)
    except (ValueError, TypeError):
        return 0.5
```

**テスト**:
- [x] 今年のソースは1.0
- [x] 昨年のソースは0.9
- [x] 2年前は0.7、3年前は0.5

---

### Phase 3: 行動経済学効果（オプション） `cc:TODO`

blog.Systemの高度な要件。Phase 1, 2 完了後に検討。

#### 3.1 心理効果フィールド追加

**PrimarySource に追加**:
```python
psychological_effect: str = ""     # "損失回避", "社会的証明" など
behavioral_trigger: str = ""       # "今すぐ行動したくなる理由"
```

#### 3.2 LLMによる心理効果分析

各ソースに対してLLMで行動経済学的な効果を分析・付与。

---

## テスト計画

### 単体テスト

| テスト項目 | ファイル | 状態 |
|-----------|---------|------|
| 基本的な一次情報取得 | test_step5.py | ✅ 既存 |
| クエリ生成 | test_step5.py | ✅ 既存 |
| **3フェーズ分類** | test_step5.py | ✅ 完了 (27テスト) |
| **知識ギャップ発見** | test_step5.py | ✅ 完了 |
| **セクション配置** | test_step5.py | ✅ 完了 |
| **鮮度スコア計算** | test_step5.py | ✅ 完了 |

### 統合テスト

| テスト項目 | 状態 |
|-----------|------|
| step4 → step5 連携 | ✅ 既存 |
| **step3c → step5 連携（知識ギャップ）** | ⏳ 追加予定 |
| step5 → step6 連携 | ⏳ 追加予定 |

---

## 実装ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `apps/worker/activities/schemas/step5.py` | 修正（Phase 1.1, 2.1） |
| `apps/worker/activities/step5.py` | 修正（Phase 1.2, 1.3, 2.1, 2.2） |
| `tests/unit/activities/test_step5.py` | 追加 |
| `tests/integration/test_step5_integration.py` | 新規 |

---

## フロー変更の必要性

**なし** - 既存Activity枠で対応可能

step3cからの入力読み込みを追加するが、オプショナル（なければスキップ）として実装。

---

## 定数・設定

```python
# apps/worker/activities/step5.py
MAX_SEARCH_QUERIES = 5           # 生成するクエリ数
MIN_SOURCES = 2                  # 最低ソース数
TARGET_SOURCES_PER_PHASE = {
    "phase1_anxiety": 5,         # 目標: 5-8個
    "phase2_understanding": 10,  # 目標: 10-15個
    "phase3_action": 3,          # 目標: 3-5個
}
MAX_KNOWLEDGE_GAPS = 10          # 知識ギャップ上限
```

---

## 優先度

| Phase | 重要度 | 理由 |
|-------|--------|------|
| Phase 1 | **最高** | 3フェーズ分類はblog.System必須要件、step6に影響 |
| Phase 2 | **高** | セクション配置で記事品質向上 |
| Phase 3 | 中 | 高度な心理効果分析、後回し可能 |

---

## step6への影響

step5の拡張により、step6（アウトライン強化）で以下が利用可能になる:

- `phase_specific_data` → フェーズ別データ配置の自動化
- `knowledge_gaps_filled` → 差別化ポイントの強調
- `section_source_mapping` → 引用配置の効率化

step6側でこれらを参照するロジック追加が必要（別途step6計画で対応）。

---

## 実装状況

**Phase 1: 3フェーズ分類と知識ギャップ** - ✅ 完了
- スキーマ拡張 (`DataPoint`, `PhaseData`, `PhaseSpecificData`, `KnowledgeGap`)
- 3フェーズ分類ロジック (`_classify_phase`)
- 知識ギャップ発見ロジック (`_find_knowledge_gaps`)

**Phase 2: セクション配置と鮮度スコア** - ✅ 完了
- セクション配置マッピング (`_map_sources_to_sections`, `SectionSourceMapping`)
- 鮮度スコア計算 (`_calculate_freshness_score`)
- `CollectionStats`にフェーズ別カウント追加

**Phase 3: 行動経済学効果** - ⏳ 未着手（オプション）

---

## 次のアクション

1. Phase 3 (行動経済学効果) の実装（オプション）
2. 統合テストの追加（step3c → step5 連携）
3. step6 との連携確認
