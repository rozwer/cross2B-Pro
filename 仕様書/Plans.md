# リトライ推奨表示機能

> **作成日**: 2026-01-24
> **目的**: ステップ失敗時にエラーカテゴリに基づき推奨リトライ方法をボタン表示

---

## ルールベース判定

| エラーカテゴリ | 推奨アクション | 理由 |
|---------------|---------------|------|
| `retryable` | 同一ステップをリトライ | 一時的障害のため再試行で解決可能 |
| `non_retryable` | 同一ステップをリトライ | 設定変更後に再試行が必要 |
| `validation_fail` | 入力元ステップからリトライ | 入力データ品質問題のため再生成必要 |

## ステップ依存関係マップ（順序付き候補リスト）

| ステップ | 入力元候補（優先順） | config無効化 |
|---------|-------------------|-------------|
| step1 | [step0] | - |
| step1_5 | [step1] | `enable_step1_5` |
| step2 | [step1_5, step1] | - |
| step3a | [step2] | - |
| step3b | [step2] | - |
| step3c | [step1] | - |
| step3_5 | [step3a] | `enable_step3_5` |
| step4 | [step3_5, step3a] | - |
| step5 | [step4] | - |
| step6 | [step4] | - |
| step6_5 | [step6] | - |
| step7a | [step6_5] | - |
| step7b | [step7a] | - |
| step8 | [step7b] | - |
| step9 | [step7b] | - |
| step10 | [step9] | - |
| step11 | [step10] | `enable_images` |
| step12 | [step10] | `enable_step12` |

**注**: 候補リストは優先順。先頭から探索し、config無効化されていない最初の有効ステップを推奨。

---

## 🔴 フェーズ1: バックエンド実装 `cc:TODO`

### 1.1 リトライ推奨ロジック `[feature:tdd]`

**対象**: `apps/api/services/runs.py`

**エラーソース**: `Step.error_code`（Run.error_code ではない）

```python
# 最新の失敗ステップを取得
failed_step = next(
    (s for s in sorted(run.steps, key=lambda s: s.completed_at or datetime.min, reverse=True)
     if s.status == "failed"),
    None
)
if not failed_step:
    return None
error_code = failed_step.error_code
```

**config無効化ステップの除外**:
```python
# config無効化チェック対象
CONFIG_DISABLED_STEPS = {
    "step1_5": "enable_step1_5",
    "step3_5": "enable_step3_5",
    "step11": "enable_images",
    "step12": "enable_step12",
}

def is_step_enabled(step: str, config: dict) -> bool:
    """ステップがconfig で有効かどうかを判定"""
    config_key = CONFIG_DISABLED_STEPS.get(step)
    if config_key is None:
        return True  # 無効化対象でないステップは常に有効
    return config.get(config_key, True)

def get_valid_target_step(step: str, config: dict) -> str | None:
    """候補リストから有効な最初のステップを返す"""
    candidates = STEP_INPUT_MAP.get(step, [])
    for candidate in candidates:
        if not is_step_enabled(candidate, config):
            continue
        if candidate in RESUME_STEP_ORDER:
            return candidate
    return None
```

#### テストケース

| ケース | error_code | step | config | 期待 |
|--------|-----------|------|--------|------|
| validation失敗 | validation_fail | step4 | - | step3_5 |
| 一時障害 | retryable | step4 | - | step4 |
| ステップレコードなし | - | - | - | None |
| step3_5無効 | validation_fail | step4 | enable_step3_5=False | step3a |
| step1_5無効 | validation_fail | step2 | enable_step1_5=False | step1 |
| step11無効でstep12失敗 | validation_fail | step12 | enable_images=False | step10 |

### 1.2 RunResponse拡張

**対象**: `apps/api/schemas/runs.py`

```python
class RetryRecommendation(BaseModel):
    action: Literal["retry_same", "retry_previous"]
    target_step: str
    reason: str
```

---

## 🟡 フェーズ2: フロントエンド実装 `cc:TODO`

### 2.1 RetryRecommendationBanner `[feature:a11y]`

**対象**: `apps/ui/src/components/runs/RetryRecommendationBanner.tsx`

**表示条件**: `run.status === "failed" && run.retry_recommendation && !run.needs_github_fix`

**既存UIとの優先度**:
1. `needs_github_fix` → GitHubFixButton/Status
2. 初回失敗 → RetryRecommendationBanner
3. 既存retry/resumeボタン → そのまま維持

### 2.2 型定義追加

**対象**: `apps/ui/src/lib/types.ts`

### 2.3 Run詳細ページ統合

**対象**: `apps/ui/src/app/runs/[id]/page.tsx`

---

## 🟢 フェーズ3: テスト `cc:TODO`

**対象**: `tests/unit/test_retry_recommendation.py`

1. validation_fail時に入力元ステップを推奨
2. retryable時に同一ステップを推奨
3. ステップレコードなし時はNone
4. config無効化ステップは除外
5. target_stepがRESUME_STEP_ORDERに含まれる
6. needs_github_fix時はバナー非表示

---

## 参照先

| 項目 | 参照先 |
|------|--------|
| Step.error_code | `apps/api/db/models.py` L188 |
| RESUME_STEP_ORDER | `apps/api/constants.py` L33-52 |
| 既存retry/resumeボタン | `apps/ui/src/components/workflow/WorkflowPattern1_N8nStyle.tsx` L483-507 |

## 修正対象ファイル

| ファイル | 変更 |
|----------|------|
| `apps/api/services/runs.py` | `get_retry_recommendation()` 追加 |
| `apps/api/schemas/runs.py` | `RetryRecommendation` 追加 |
| `apps/ui/src/lib/types.ts` | 型追加 |
| `apps/ui/src/components/runs/RetryRecommendationBanner.tsx` | 新規 |
| `apps/ui/src/app/runs/[id]/page.tsx` | 統合 |
| `tests/unit/test_retry_recommendation.py` | 新規 |
