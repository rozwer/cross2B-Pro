# blog.System プロンプト統合設計

**作成日**: 2026-01-08

## 設計判断サマリー

| 判断ポイント | 推奨案 | 根拠 |
|-------------|-------|------|
| プロンプト管理方式 | **C案: ハイブリッド** | 互換性維持 + 段階的移行 |
| フロー変更 | **段階的追加** | リスク分散、テスト可能性 |
| 移行戦略 | **段階的移行** | 並行稼働で安全性確保 |

---

## 1. プロンプト管理方式の設計

### 推奨: C案（ハイブリッド）

```
apps/api/prompts/
├── packs/
│   ├── default.json          # 既存（互換性維持）
│   └── v2_blog_system.json   # 新規（blog.System形式）
├── knowledge/
│   └── v2/
│       ├── step0/unified_knowledge.json
│       ├── step3a/unified_knowledge.json
│       └── ...
└── loader.py                  # 拡張（knowledge対応）
```

### PromptLoader 拡張設計

```python
@dataclass
class PromptTemplate:
    step: str
    version: int
    content: str
    variables: dict[str, Any] = field(default_factory=dict)
    # 新規追加
    knowledge_path: str | None = None  # unified_knowledge.json へのパス

@dataclass
class UnifiedKnowledge:
    """blog.System unified_knowledge.json 構造"""
    process_info: dict
    guidelines: dict
    templates: dict
    examples: dict
    checklist: dict

class PromptPackLoader:
    def load_with_knowledge(self, pack_id: str, step: str) -> tuple[PromptTemplate, UnifiedKnowledge | None]:
        """プロンプトと知識ベースを同時にロード"""
        template = self.load(pack_id).get_prompt(step)
        knowledge = None
        if template.knowledge_path:
            knowledge = self._load_knowledge(template.knowledge_path)
        return template, knowledge
```

### 変数システム拡張

| 変数 | 用途 | 注入元 |
|------|------|--------|
| `{{__system_guidelines}}` | unified_knowledgeのguidelines | knowledge.guidelines.content |
| `{{__output_template}}` | 出力スキーマ定義 | knowledge.templates |
| `{{__checklist}}` | 4本柱チェックリスト | knowledge.checklist |

---

## 2. LangGraph State 拡張

### 新規フィールド（4つ）

```python
@dataclass
class GraphState:
    # 既存フィールド
    run_id: str
    tenant_id: str
    current_step: str
    status: str
    step_outputs: dict[str, Any]
    validation_reports: list
    errors: list
    config: dict
    metadata: dict

    # 新規追加（blog.System対応）
    system_prompt_context: dict = field(default_factory=dict)  # knowledge cache
    prompt_pack_id: str = ""  # 使用中パックID
    prompt_version_used: dict = field(default_factory=dict)  # {step: version}
    system_knowledge_loaded_at: str = ""  # ロード時刻
```

---

## 3. Activity 層の変更

### 既存Activity修正（12個）

各stepXX.pyの `execute()` メソッドに以下を追加:

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # 1. プロンプト+知識をロード
    loader = PromptPackLoader()
    template, knowledge = loader.load_with_knowledge(
        state.config.get("pack_id"),
        self.step_id
    )

    # 2. 変数を構築（knowledgeがあれば注入）
    variables = self._build_variables(state)
    if knowledge:
        variables["__system_guidelines"] = knowledge.guidelines.get("content", "")
        variables["__output_template"] = json.dumps(knowledge.templates)
        variables["__checklist"] = json.dumps(knowledge.checklist)

    # 3. プロンプトをレンダリング
    prompt = template.render(**variables)

    # 4. 使用バージョンを記録
    state.prompt_version_used[self.step_id] = template.version

    # ... 既存のLLM呼び出しロジック
```

### 新規Activity（1個）

```python
class LoadSystemPromptContextActivity(BaseActivity):
    """Workflow開始時にunified_knowledgeをプリロード"""

    @property
    def step_id(self) -> str:
        return "load_context"

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        loader = PromptPackLoader()
        pack_id = state.config.get("pack_id")

        # 全stepの knowledge をプリロード
        knowledge_cache = {}
        for step in loader.load(pack_id).list_steps():
            _, knowledge = loader.load_with_knowledge(pack_id, step)
            if knowledge:
                knowledge_cache[step] = knowledge.model_dump()

        return {
            "system_prompt_context": knowledge_cache,
            "system_knowledge_loaded_at": datetime.now().isoformat(),
        }
```

---

## 4. 4本柱バリデーション実装

### 出力バリデータ拡張

```python
class FourPillarsValidator:
    """4本柱（神経科学・行動経済学・LLMO・KGI）の自動検証"""

    def validate(self, output: dict, step: str, knowledge: UnifiedKnowledge) -> ValidationReport:
        issues = []

        # 1. 神経科学: 3フェーズ対応確認
        if not self._check_three_phases(output, step):
            issues.append(ValidationIssue(
                severity="warning",
                message="3フェーズ構成が不完全",
                field="structure"
            ))

        # 2. 行動経済学: 6原則配置確認
        if not self._check_behavioral_economics(output, step):
            issues.append(ValidationIssue(
                severity="warning",
                message="行動経済学6原則の配置が不足",
                field="persuasion_elements"
            ))

        # 3. LLMO: トークン数・独立性確認
        if not self._check_llmo(output, step):
            issues.append(ValidationIssue(
                severity="info",
                message="LLMOセクション独立性の確認推奨",
                field="section_structure"
            ))

        # 4. KGI: CTA配置確認
        if not self._check_kgi(output, step):
            issues.append(ValidationIssue(
                severity="warning",
                message="CTA配置位置が目標と乖離",
                field="cta_placements"
            ))

        return ValidationReport(issues=issues)
```

---

## 5. 新規工程の追加計画

### 優先度順

| 優先度 | 工程 | 実装方針 | 理由 |
|--------|------|---------|------|
| P1 | 工程6.5 | 既存step6の後に追加 | 既にActivity枠あり |
| P2 | 工程-1 | UI/APIで対応 | Workflow前の入力フォーム |
| P3 | 工程1.5 | step1の後に追加 | 既にActivity枠あり |
| P4 | 工程13 | 将来検討 | セキュリティ考慮必要 |

### 工程-1（絶対条件ヒアリング）の実装

```
UI側:
- /runs/new ページにフォーム追加
- target_word_count, strategy, word_count_mode 等を入力
- 入力値はconfig経由でWorkflowに渡す

API側:
- POST /api/runs に新規パラメータ追加
- バリデーション強化
```

---

## 6. 移行戦略

### Phase 1: 基盤準備（低リスク）

1. PromptLoader拡張（knowledge対応）
2. GraphState拡張（4フィールド追加）
3. ValidationReport拡張（4本柱対応）
4. v2_blog_system.json パック作成

### Phase 2: 工程別テスト

1. step0（キーワード選定）から順次テスト
2. 各工程で新旧プロンプト比較
3. 出力品質の評価

### Phase 3: 段階的ロールアウト

1. `pack_id=v2_blog_system` で新プロンプト使用可能に
2. 既存 `pack_id=default` は維持
3. ユーザーが選択可能な状態で並行稼働

### Phase 4: 完全移行（将来）

1. default → v2_blog_system への移行促進
2. 旧形式の非推奨化
3. 最終的な統一

---

## 7. ロールバック計画

### 即時ロールバック

```bash
# pack_id を default に戻すだけで旧プロンプトに戻る
# Workflow/Activity のコード変更は不要
```

### 設計上のロールバック安全性

1. **pack_id ベース切替**: config.pack_id を変えるだけ
2. **knowledge なし許容**: knowledge_path=None なら従来動作
3. **バリデーション緩和**: 4本柱チェックは warning レベル
4. **DB スキーマ互換**: 新フィールドは nullable/default あり

---

## 8. 実装優先順位

### 即座に着手可能

1. [ ] `apps/api/prompts/loader.py` - UnifiedKnowledge 対応
2. [ ] `apps/api/core/state.py` - GraphState 拡張
3. [ ] `apps/api/prompts/packs/v2_blog_system.json` - 新パック作成

### 工程別テスト後

4. [ ] 各 Activity の execute() 修正
5. [ ] FourPillarsValidator 実装
6. [ ] 新規API エンドポイント追加

### UI連携

7. [ ] 工程-1 フォーム対応
8. [ ] 4本柱スコア表示
9. [ ] 文字数トラッキング表示

---

## 参照ドキュメント

- [prompt-comparison.md](prompt-comparison.md) - 新旧プロンプト比較
- [technical-impact.md](technical-impact.md) - 技術的影響範囲
- `blog.System_prompts/MASTER_SPEC.md` - blog.System仕様
- `仕様書/workflow.md` - 既存ワークフロー定義
