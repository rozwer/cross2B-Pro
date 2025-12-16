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

## 並列実行

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
