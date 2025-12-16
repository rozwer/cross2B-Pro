# Temporal + LangGraph 仕様

## 責務分離

| コンポーネント | 責務 |
|----------------|------|
| **Temporal** | 実行状態、待機、リトライ、タイムアウト、キャンセル |
| **LangGraph** | 工程ロジック（プロンプト、整形、検証） |
| **DB** | UI表示、履歴、監査、成果物索引 |

## Workflow

```python
@workflow.defn
class ArticleWorkflow:
    @workflow.signal
    async def approve(self): ...

    @workflow.signal
    async def reject(self): ...

    @workflow.run
    async def run(self, tenant_id: str, run_id: str) -> dict:
        # step0 → step1 → step2 → step3_parallel
        # → wait_approval
        # → step4 → ... → step10
        pass
```

### 決定性ルール

- Workflow では外部I/Oや時刻依存を避ける
- 必要なら Activity に寄せる

## Activity

- 副作用（LLM/外部API/DB/Storage）を閉じ込める
- Activity から LangGraph を呼び出して工程ロジックを実装
- 大きい出力は storage に保存し、path/digest のみ返す

### 冪等性

```python
# 同一入力 → 同一出力
if existing := storage.get(f"{tenant}/{run}/{step}/output.json"):
    return existing  # 再計算しない
```

---

## 承認フロー {#approval}

### タイミング

工程3（3A/3B/3C）完了後 → 工程4開始前

### 実装

```python
# Workflow側
await workflow.wait_condition(lambda: self.approved or self.rejected)

if self.rejected:
    return {"status": "rejected"}
# continue to step4...
```

### API

```
POST /api/runs/{id}/approve  → Temporal signal
POST /api/runs/{id}/reject   → Temporal signal
```

### 監査ログ

承認/却下時に必須：
- `actor`, `tenant_id`, `run_id`, `timestamp`
- `decision` (approve/reject), `reason`

---

## 並列実行 {#parallel}

工程3A/3B/3Cは Temporal の並列実行：

```python
results = await asyncio.gather(
    workflow.execute_activity("step3a", ...),
    workflow.execute_activity("step3b", ...),
    workflow.execute_activity("step3c", ...),
    return_exceptions=True
)
# 失敗分のみリトライ
```

### 並列工程エラーハンドリング詳細

| ケース | 挙動 |
|--------|------|
| 3A成功、3B失敗、3C成功 | 3Bのみリトライ（最大3回） |
| 3A/3B/3C全失敗 | 全リトライ。全再失敗でrun失敗 |
| 3Aが3回失敗後 | 3B/3C続行せず即座に停止（3つ揃わないと承認待ちに進めない） |

### 実装パターン

```python
async def run_parallel_steps():
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
                # ログ記録
                logger.warning(f"{step} failed (attempt {attempt + 1}): {result}")

    if len(completed) < 3:
        failed = [s for s in ["step3a", "step3b", "step3c"] if s not in completed]
        raise WorkflowFailedError(f"Parallel steps failed: {failed}")

    return completed
```

---

## タイムアウト

| 工程 | タイムアウト | 備考 |
|------|-------------|------|
| 0 | 60s | |
| 1 | 300s | 外部API依存 |
| 3A/B/C | 各120s | |
| 4 | 180s | |
| 5 | 300s | Web検索あり |
| 6 | 180s | |
| 6.5 | 180s | |
| 7A | 600s | 長文生成 |
| 7B | 300s | |
| 8 | 300s | Web検索あり |
| 9 | 300s | |
| 10 | 120s | |

---

## エラーハンドリング

| 方針 | 内容 |
|------|------|
| フォールバック | **使用しない** |
| リトライ | 同一条件で再試行（最大3回） |
| 並列失敗時 | 失敗した工程のみリトライ |
| JSON破損 | バリデーション失敗時は再実行 |

---

## 部分再実行（Resume）機能 {#resume}

### 概要

失敗した run を特定工程から再開する機能。全 run やり直しの非効率を解消。

### 設計方針

> Temporal Workflow の決定性を保つため、再実行は「新しい run_id で開始し、既存成果物を参照する」方式を採用

### API

```
POST /api/runs/{id}/resume/{step}
```

### 実装

```python
@workflow.defn
class ArticleWorkflow:
    @workflow.run
    async def run(self, tenant_id: str, run_id: str, resume_from: str | None = None):
        # resume_from が指定されている場合、その工程までスキップ
        steps = ["step0", "step1", "step2", "step3", "step4", ...]

        for step in steps:
            if resume_from and steps.index(step) < steps.index(resume_from):
                # 既存成果物の存在 + digest 検証
                artifact = await self.verify_existing_artifact(step)
                if not artifact:
                    raise WorkflowFailedError(f"Missing artifact for {step}")
                continue

            # 通常実行
            await workflow.execute_activity(step, ...)
```

### 検証事項

| チェック項目 | 説明 |
|--------------|------|
| 依存成果物存在確認 | 再開工程より前の成果物がすべて存在すること |
| digest 検証 | 成果物が改ざんされていないこと |
| tenant_id 一致 | 元 run と同一テナントであること |

### 新規 run_id 生成

```python
# 元 run との関連を記録
new_run = Run(
    id=generate_uuid(),
    parent_run_id=original_run_id,
    resume_from_step=resume_from,
    # ...
)
```
