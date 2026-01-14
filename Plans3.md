# Plans3.md

> **最終更新**: 2026-01-14
> **目的**: Step3（3A/3B/3C）の「指示付きリトライ」機能実装

---

## 背景・現状分析

### 現在の問題点

1. **却下 = 即終了**: `reject` signal を受信すると `status: "failed"` でワークフローが終了
2. **フィードバック不可**: Step3（3A/3B/3C）の結果に対して修正指示を渡してリトライする仕組みがない
3. **Step11との差異**: 画像生成（Step11）には `retry_instruction` で再生成指示を渡せるが、Step3にはそれがない

### Step11（参考実装）の指示付きリトライ

```
POST /images/retry
- index: 画像インデックス
- instruction: 再生成指示

POST /images/review
- reviews[]: {index, accepted, retry, retry_instruction}
```

**特徴**:
- 個別の成果物に対して「承認」「リトライ」を選択可能
- リトライ時に修正指示を添えられる
- 承認されるまで何度でもリトライ可能（上限3回）

---

## 要件定義

### 必須要件

| ID | 要件 | 詳細 |
|----|------|------|
| REQ-01 | 指示付き却下 | 却下時に修正指示（rejection_instructions）を添えられる |
| REQ-02 | ステップ個別リトライ | 3A/3B/3Cを個別にリトライ可能 |
| REQ-03 | 修正指示の反映 | リトライ時に修正指示がLLMプロンプトに追加される |
| REQ-04 | 再レビュー | リトライ後、再度承認待ち状態になる |
| REQ-05 | リトライ上限 | 各ステップ最大3回までリトライ可能 |

### オプション要件

| ID | 要件 | 詳細 |
|----|------|------|
| OPT-01 | 部分承認 | 3A/3B/3Cを個別に承認し、NGのみリトライ |
| OPT-02 | 成果物比較 | 前回と今回の成果物を比較表示 |

---

## 設計方針

### API設計

#### 新規エンドポイント

```
POST /api/runs/{run_id}/step3/review
リクエスト:
{
  "reviews": [
    {
      "step": "step3a",
      "accepted": false,
      "retry": true,
      "retry_instruction": "ペルソナをより具体的に。年齢層と職業を明記してください"
    },
    {
      "step": "step3b",
      "accepted": true
    },
    {
      "step": "step3c",
      "accepted": false,
      "retry": true,
      "retry_instruction": "競合との差別化ポイントをもっと明確に"
    }
  ]
}

レスポンス:
{
  "success": true,
  "retrying": ["step3a", "step3c"],
  "approved": ["step3b"],
  "next_action": "waiting_retry_completion"
}
```

#### 既存エンドポイント拡張

```
POST /api/runs/{run_id}/reject
既存フィールド:
  - reason: string

新規フィールド（オプション）:
  - retry_with_instructions: boolean (default: false)
  - step_instructions: {
      "step3a": "修正指示...",
      "step3b": "修正指示...",
      "step3c": "修正指示..."
    }
```

### Temporal Signal設計

#### 新規Signal

```python
@workflow.signal
async def step3_review(self, payload: dict[str, Any]) -> None:
    """Step3の個別レビュー結果を受け取る

    payload:
        reviews: list[{step, accepted, retry, retry_instruction}]
    """
    self.step3_reviews = payload.get("reviews", [])
    self.step3_retry_requested = any(r.get("retry") for r in self.step3_reviews)
```

#### 拡張Signal

```python
@workflow.signal
async def reject(self, reason: str, instructions: dict[str, str] | None = None) -> None:
    """却下シグナル（指示付きリトライ対応）

    Args:
        reason: 却下理由
        instructions: ステップ別の修正指示（指定時はリトライモード）
    """
    if instructions:
        self.rejection_with_retry = True
        self.step3_retry_instructions = instructions
    else:
        self.rejected = True
        self.rejection_reason = reason
```

### Workflow状態遷移

```
[step3完了]
    ↓
[waiting_approval]
    ↓
┌─────────────────────────────────────────┐
│ approve signal          reject signal   │
│     ↓                       ↓           │
│ [post_approval]    ┌────────────────┐   │
│     ↓              │ instructions?  │   │
│ [step3_5...]       │   YES    NO    │   │
│                    │    ↓      ↓    │   │
│                    │ RETRY  FAILED  │   │
│                    └────────────────┘   │
└─────────────────────────────────────────┘
            ↓
     [step3_retry]
            ↓
     [waiting_approval] ← 再度レビュー待ち
```

### Activity修正

```python
@activity.defn
async def step3a_query_analysis(
    tenant_id: str,
    run_id: str,
    config: dict[str, Any],
    retry_instruction: str | None = None,  # 新規パラメータ
) -> dict[str, Any]:
    """
    retry_instruction が指定されている場合、
    プロンプトに追加の指示として挿入する
    """
    ...
```

---

## 実装計画

### フェーズ1: API層 `cc:DONE`

- [x] Pydanticスキーマ追加（Step3ReviewInput, Step3ReviewItem）
- [x] `POST /api/runs/{run_id}/step3/review` エンドポイント実装
- [x] `POST /api/runs/{run_id}/reject` 拡張（instructions対応）
- [x] 監査ログ対応（step3_review, reject_with_instructions）

### フェーズ2: Workflow層 `cc:DONE`

- [x] `step3_review` signal追加
- [x] step3リトライロジック実装（whileループ + リトライ後waiting_approval復帰）
- [x] 状態遷移（waiting_approval → step3_retry → waiting_approval）
- [x] リトライ上限チェック（API側で実施、max 3回/ステップ）

### フェーズ3: Activity層 `cc:DONE`

- [x] step3a/3b/3c Activity修正（retry_instruction パラメータ追加）
- [x] プロンプトテンプレート修正（修正指示セクション追加）
- [x] parallel.py 修正（retry_steps, retry_instructions 対応）

### フェーズ4: フロントエンド `cc:DONE`

- [x] Step3レビューUI（3A/3B/3C個別の承認/リトライ選択）
- [x] 修正指示入力フォーム
- [x] リトライ状態の表示（リトライ回数、前回の指示）
- [ ] 成果物比較表示（オプション）- 将来の拡張として保留

### フェーズ5: テスト・ドキュメント `cc:DONE`

- [x] APIテスト（step3/review スキーマテスト）
- [x] Workflowテスト（parallel.py リトライ機能テスト）
- [ ] E2Eテスト（承認→リトライ→再承認）- 統合環境で実施
- [x] 仕様書更新（workflow.md）

---

## テストケース設計（TDD）

### 正常系

| テストケース | 入力 | 期待出力 |
|-------------|------|---------|
| 全ステップ承認 | reviews: [{step3a, accepted: true}, ...] | next_action: "proceed_to_step3_5" |
| 単一リトライ | reviews: [{step3a, retry: true, instruction: "..."}] | retrying: ["step3a"] |
| 全ステップリトライ | reviews: [{step3a, retry: true}, {step3b, retry: true}, {step3c, retry: true}] | retrying: ["step3a", "step3b", "step3c"] |
| リトライ後承認 | (リトライ完了後) reviews: [{step3a, accepted: true}] | approved: ["step3a"] |

### 異常系

| テストケース | 入力 | 期待出力 |
|-------------|------|---------|
| リトライ上限超過 | 4回目のリトライリクエスト | 400 Error: "Retry limit (3) exceeded for step3a" |
| 不正なステップ名 | reviews: [{step: "step99", ...}] | 400 Error: "Invalid step name" |
| 承認済みrunへのレビュー | 既にapproved状態のrun | 400 Error: "Run already approved" |

---

## 工数見積もり（参考）

| フェーズ | 工数（人日） |
|---------|------------|
| フェーズ1: API層 | 1 |
| フェーズ2: Workflow層 | 1.5 |
| フェーズ3: Activity層 | 1 |
| フェーズ4: フロントエンド | 2 |
| フェーズ5: テスト・ドキュメント | 1 |
| **合計** | **6.5** |

---

## 関連ファイル

| ファイル | 修正内容 |
|---------|---------|
| `apps/api/routers/runs.py` | step3/review エンドポイント追加 |
| `apps/api/schemas/runs.py` | Step3ReviewInput スキーマ追加 |
| `apps/worker/workflows/article_workflow.py` | step3_review signal、リトライロジック |
| `apps/worker/workflows/parallel.py` | retry_steps, retry_instructions 対応 |
| `apps/worker/activities/step3a.py` | retry_instruction パラメータ対応 |
| `apps/worker/activities/step3b.py` | retry_instruction パラメータ対応 |
| `apps/worker/activities/step3c.py` | retry_instruction パラメータ対応 |
| `apps/ui/src/lib/types.ts` | Step3Review型追加 |
| `apps/ui/src/lib/api.ts` | step3Review, rejectWithRetry メソッド追加 |
| `apps/ui/src/components/approval/Step3ReviewDialog.tsx` | Step3レビューダイアログ（新規） |
| `apps/ui/src/app/runs/[id]/page.tsx` | Step3レビューボタン・ダイアログ統合 |
| `仕様書/workflow.md` | 仕様更新（TODO） |

---

## 実装完了

全フェーズの実装が完了しました。

### 作成・修正されたファイル

#### Backend
- `apps/api/schemas/runs.py` - Step3Review型追加
- `apps/api/routers/runs.py` - step3/review エンドポイント追加
- `apps/worker/workflows/article_workflow.py` - step3_review signal追加
- `apps/worker/workflows/parallel.py` - retry_steps, retry_instructions対応
- `apps/worker/activities/step3a.py` - retry_instruction対応
- `apps/worker/activities/step3b.py` - retry_instruction対応
- `apps/worker/activities/step3c.py` - retry_instruction対応

#### Frontend
- `apps/ui/src/lib/types.ts` - Step3Review型追加
- `apps/ui/src/lib/api.ts` - step3Review, rejectWithRetry メソッド追加
- `apps/ui/src/components/approval/Step3ReviewDialog.tsx` - 新規作成
- `apps/ui/src/app/runs/[id]/page.tsx` - Step3レビューボタン統合

#### Tests
- `tests/unit/api/test_step3_review_schemas.py` - スキーマテスト
- `tests/unit/worker/test_parallel.py` - リトライ機能テスト

#### Documentation
- `仕様書/workflow.md` - Step3 指示付きリトライ仕様追加

