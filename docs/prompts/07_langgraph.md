# Session 7: LangGraph + Temporal

## Phase 4（Phase 3完了後）

---

## 作業開始手順

```bash
cd /home/rozwer/案件
git fetch origin
git pull origin develop

# Phase 3 のマージ確認
git log --oneline develop | head -10
# feat/contract がマージ済みであること

# Worktree作成
TOPIC="langgraph"
mkdir -p .worktrees
git worktree add -b "feat/$TOPIC" ".worktrees/$TOPIC" develop

# 作業ディレクトリへ移動
cd ".worktrees/$TOPIC"
```

---

## 前提確認

Phase 1-3 が完了済みであること:

```bash
ls apps/api/llm/base.py
ls apps/api/tools/registry.py
ls apps/api/validation/schemas.py
ls apps/api/core/state.py
ls apps/api/storage/artifact_store.py
```

---

## 実装指示

あなたはSEO記事自動生成システムのバックエンド実装者です。

### 実装対象

LangGraph メインシステム + Temporal 統合

### 前提

- 仕様書/ROADMAP.md の Step 6 を参照
- 仕様書/workflow.md を参照
- 仕様書/backend/temporal.md を参照
- **顧客プロンプト未入手のためプロンプト内容はモック（mock_pack明示指定時のみ動作）**

### 成果物

```
apps/worker/
├── __init__.py
├── main.py                  # Worker エントリポイント
├── workflows/               # Part A: Temporal Workflow
│   ├── __init__.py
│   ├── article_workflow.py  # メインWorkflow
│   └── parallel.py          # 並列実行ヘルパー
├── activities/              # Part B: Activities
│   ├── __init__.py
│   ├── base.py              # 共通Activity基底
│   ├── step0.py             # キーワード選定
│   ├── step1.py             # 競合記事取得
│   ├── step2.py             # CSV検証
│   ├── step3a.py            # クエリ分析
│   ├── step3b.py            # 共起語抽出（心臓部）
│   ├── step3c.py            # 競合分析
│   ├── step4.py             # 戦略的アウトライン
│   ├── step5.py             # 一次情報収集
│   ├── step6.py             # アウトライン強化
│   ├── step6_5.py           # 統合パッケージ化
│   ├── step7a.py            # 本文生成
│   ├── step7b.py            # ブラッシュアップ
│   ├── step8.py             # ファクトチェック
│   ├── step9.py             # 最終リライト
│   └── step10.py            # 最終出力
└── graphs/                  # Part C: LangGraph
    ├── __init__.py
    ├── pre_approval.py      # 承認前グラフ
    ├── post_approval.py     # 承認後グラフ
    └── wrapper.py           # 共通ノードラッパー

tests/
├── integration/workflow/
└── e2e/
```

---

## Part A: Temporal Workflow

### article_workflow.py

```python
from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta

@workflow.defn
class ArticleWorkflow:
    def __init__(self):
        self.approved = False
        self.rejected = False
        self.rejection_reason: str | None = None

    @workflow.signal
    async def approve(self):
        self.approved = True

    @workflow.signal
    async def reject(self, reason: str):
        self.rejected = True
        self.rejection_reason = reason

    @workflow.run
    async def run(
        self,
        tenant_id: str,
        run_id: str,
        config: dict,
        resume_from: str | None = None
    ) -> dict:
        # Pre-approval phase
        if not resume_from or self._should_run("step0", resume_from):
            await workflow.execute_activity(
                "step0_keyword_selection",
                args=[tenant_id, run_id, config],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
        # ... step1, step2

        # Parallel step3
        await self._run_parallel_steps(tenant_id, run_id, config)

        # Wait for approval
        await workflow.wait_condition(
            lambda: self.approved or self.rejected
        )

        if self.rejected:
            return {"status": "rejected", "reason": self.rejection_reason}

        # Post-approval phase
        # step4 → ... → step10

        return {"status": "completed"}
```

### parallel.py

```python
async def run_parallel_steps(
    tenant_id: str,
    run_id: str,
    config: dict
) -> dict:
    """
    工程3A/3B/3Cの並列実行
    失敗分のみリトライ（最大3回）
    3つ揃わないと承認待ちに進めない
    """
    MAX_RETRIES = 3
    completed = {}

    for attempt in range(MAX_RETRIES):
        pending = [s for s in ["step3a", "step3b", "step3c"] if s not in completed]
        if not pending:
            break

        results = await asyncio.gather(
            *[workflow.execute_activity(s, ...) for s in pending],
            return_exceptions=True
        )

        for step, result in zip(pending, results):
            if not isinstance(result, Exception):
                completed[step] = result
            else:
                logger.warning(f"{step} failed (attempt {attempt + 1})")

    if len(completed) < 3:
        failed = [s for s in ["step3a", "step3b", "step3c"] if s not in completed]
        raise WorkflowFailedError(f"Parallel steps failed: {failed}")

    return completed
```

---

## Part B: Activities

### base.py

```python
from temporalio import activity
from apps.api.core.context import ExecutionContext
from apps.api.core.state import GraphState
from apps.api.storage.artifact_store import ArtifactStore
from apps.api.observability.events import EventEmitter

class BaseActivity:
    def __init__(self):
        self.store = ArtifactStore()
        self.emitter = EventEmitter()

    async def execute_with_idempotency(
        self,
        ctx: ExecutionContext,
        state: GraphState,
        execute_fn
    ):
        """冪等性を保証した実行"""
        # 既存成果物があればスキップ
        existing = await self.store.get_if_exists(
            f"{ctx.tenant_id}/{ctx.run_id}/{ctx.step_id}/output.json"
        )
        if existing:
            return existing

        # 実行
        await self.emitter.emit_step_started(ctx)
        try:
            result = await execute_fn()
            artifact_ref = await self.store.put(result, ...)
            await self.emitter.emit_step_succeeded(ctx, artifact_ref)
            return artifact_ref
        except Exception as e:
            await self.emitter.emit_step_failed(ctx, e)
            raise
```

### 各工程Activity

各工程は以下の責務:

1. LLM or Tool を呼び出す
2. 出力を検証する（ValidationReport）
3. 成果物を保存する（ArtifactRef）
4. イベントを発行する

---

## Part C: LangGraph Graphs

### wrapper.py

```python
from apps.api.core.context import ExecutionContext
from apps.api.core.state import GraphState
from apps.api.prompts.loader import PromptPackLoader

async def step_wrapper(
    step_fn,
    ctx: ExecutionContext,
    state: GraphState,
    config: dict
) -> GraphState:
    """共通ノードラッパー"""
    loader = PromptPackLoader()
    prompt_pack = loader.load(config.get("pack_id"))  # None なら例外

    # 1. prompt load
    prompt = prompt_pack.get_prompt(ctx.step_id)

    # 2. call (LLM or Tool)
    result = await step_fn(prompt, state, ctx)

    # 3. validate
    report = validator.validate(result)
    if not report.valid:
        raise ValidationError(report)

    # 4. store artifact
    artifact_ref = await store.put(result, ...)

    # 5. emit event
    await emitter.emit_step_succeeded(ctx, artifact_ref)

    # 6. update state
    state["step_outputs"][ctx.step_id] = artifact_ref
    state["validation_reports"].append(report)
    state["current_step"] = ctx.step_id

    return state
```

### pre_approval.py

```python
from langgraph.graph import StateGraph
from apps.api.core.state import GraphState

def build_pre_approval_graph() -> StateGraph:
    graph = StateGraph(GraphState)

    graph.add_node("step0", step0_node)
    graph.add_node("step1", step1_node)
    graph.add_node("step2", step2_node)
    graph.add_node("step3_parallel", step3_parallel_node)

    graph.add_edge("step0", "step1")
    graph.add_edge("step1", "step2")
    graph.add_edge("step2", "step3_parallel")

    graph.set_entry_point("step0")
    graph.set_finish_point("step3_parallel")

    return graph.compile()
```

---

## タイムアウト設定

| 工程   | タイムアウト | 備考             |
| ------ | ------------ | ---------------- |
| 0      | 60s          | キーワード選定   |
| 1      | 300s         | 外部API依存      |
| 2      | 60s          | CSV検証          |
| 3A/B/C | 各120s       | 並列             |
| 4      | 180s         | アウトライン     |
| 5      | 300s         | Web検索          |
| 6      | 180s         | 強化版           |
| 6.5    | 180s         | 統合パッケージ   |
| 7A     | 600s         | **長文生成**     |
| 7B     | 300s         | ブラッシュアップ |
| 8      | 300s         | ファクトチェック |
| 9      | 300s         | 最終リライト     |
| 10     | 120s         | 最終出力         |

---

## DoD（完了条件）

- [ ] mock_pack 指定で pre が並列含め完走し承認待ち State が保存される
- [ ] 承認後 post が進み、工程6.5 の統合パッケージが生成・保存される
- [ ] 全工程で検証・保存・イベント記録が行われ、黙って採用がない
- [ ] 冪等性: 同一入力→同一出力（既存成果物があればスキップ）
- [ ] E2E テストが通過
- [ ] Temporal Replay テストが通過（決定性違反がない）
- [ ] pytest が通過
- [ ] mypy が通過

### 禁止事項

- フォールバック使用禁止
- Workflow内での外部I/O（Activityに寄せる）
- 大きいJSON/本文をTemporal履歴に持つ（path/digest参照のみ）
- pack_id 未指定での自動実行

---

## 完了後

```bash
# ユニットテスト
pytest tests/unit/ -v

# 統合テスト
pytest tests/integration/workflow/ -v

# E2Eテスト（mock_pack使用）
USE_MOCK_LLM=true MOCK_PACK_ID=mock_pack pytest tests/e2e/ -v

# 型チェック
mypy apps/worker/

# コミット
git add .
git commit -m "feat(workflow): LangGraph + Temporal 統合"

# push & PR作成
git push -u origin feat/langgraph
gh pr create --base develop --title "feat(workflow): LangGraph + Temporal メインシステム" --body "## 概要
- ArticleWorkflow (Temporal)
- pre_approval_graph, post_approval_graph (LangGraph)
- 全工程Activities (step0〜step10)
- 並列実行 (step3A/B/C)
- 承認待ち/再開機能

## 依存
- Phase 1-3 完了済み

## テスト
- [x] pytest通過
- [x] mypy通過
- [x] E2Eテスト通過（mock_pack）
- [x] Temporal Replayテスト通過"
```
