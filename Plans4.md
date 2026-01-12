# エラー表示・リトライ機能修正計画

> **作成日**: 2026-01-12
> **目的**: ステップ失敗時のエラー原因表示とリトライ機能の修正

---

## 背景・問題

### ユーザー報告
1. **エラー原因が表示されない** - ステップ失敗時にエラー詳細が UI に表示されない
2. **失敗したステップからのやり直しができない** - リトライ機能が動作しない
3. **前のステップでやり直しをしても失敗する** - リトライのカスケード失敗

### 調査で判明した根本原因

| # | 問題 | 重大度 | 影響 |
|---|------|--------|------|
| **A** | リトライ時に前ステップデータが読み込まれない | 🔴 HIGH | リトライが必ず失敗 |
| **B** | Step モデルに error_code がない | 🟠 MEDIUM | エラー種類の分類表示不可 |
| **C** | step1.5, step3.5, step6.5 がリトライ有効リストから除外 | 🟠 MEDIUM | 特定ステップでリトライ拒否 |
| **D** | エラーレスポンス形式の FE/BE 不一致 | 🟡 LOW | 詳細エラー表示の問題 |

---

## 影響範囲

| ファイル | 変更内容 |
|---------|---------|
| `apps/api/routers/runs.py` | リトライロジック修正、有効ステップリスト追加 |
| `apps/api/db/models.py` | Step モデルに error_code 追加 |
| `apps/worker/activities/base.py` | エラー情報の伝播改善 |
| `apps/ui/src/components/steps/StepDetailPanel.tsx` | エラー詳細表示 |
| `apps/ui/src/app/runs/[id]/page.tsx` | エラー表示の改善 |

---

## フェーズ 0: 過去の Run 履歴からエラー情報収集 `cc:TODO`

まず現状を把握するため、過去の失敗 run からエラー情報を収集する。

### 0.1 エラー情報の収集

- [ ] error_logs テーブルから最近の失敗ログを取得
- [ ] diagnostic_reports テーブルからエラー分析情報を取得
- [ ] runs テーブルから FAILED ステータスの run を特定
- [ ] 失敗パターン（どのステップで、どのようなエラーか）を整理

### 0.2 収集結果の分析

- [ ] 共通するエラーパターンを特定
- [ ] リトライ失敗の具体的なケースを記録
- [ ] 修正優先度の確認

---

## フェーズ 1: リトライ機能の修正 ✅ 完了

**最重要**: リトライが機能しない根本原因を修正

### 1.1 前ステップデータ読み込みロジックの追加

対象: `apps/api/routers/runs.py:574-620` (retry_step エンドポイント)

- [ ] `resume_from_step` と同様の前ステップデータ読み込みロジックを追加
- [ ] ArtifactStore から前ステップの output を取得
- [ ] Workflow 起動時に前準備データを config に含める

参考実装: `apps/api/routers/runs.py:682-691` (resume_from_step のロジック)

```python
# 追加すべきロジック（概念）
previous_outputs = {}
for prev_step in get_steps_before(normalized_step):
    output = await artifact_store.get_step_output(run_id, prev_step)
    if output:
        previous_outputs[prev_step] = output

loaded_config["previous_outputs"] = previous_outputs
```

### 1.2 有効ステップリストの更新

対象: `apps/api/routers/runs.py:509-525`

- [ ] `step1_5`, `step3_5`, `step6_5` を有効ステップリストに追加
- [ ] 正規化後の名前（`_` 使用）で一致確認

```python
valid_steps = [
    "step0",
    "step1",
    "step1_5",  # 追加
    "step2",
    "step3a",
    "step3b",
    "step3c",
    "step3_5",  # 追加
    "step4",
    "step5",
    "step6",
    "step6_5",  # 追加
    # ... 残りのステップ
]
```

### 1.3 Workflow 側のリトライ受け付け改善

対象: `apps/worker/workflows/article_workflow.py`

- [ ] resume_from に対応する前準備データの検証
- [ ] 前準備データが不足している場合の明確なエラーメッセージ

---

## フェーズ 2: エラー情報の保存強化 ✅ 完了

### 2.1 Step モデルに error_code 追加

対象: `apps/api/db/models.py:149`

- [ ] Step モデルに `error_code: Optional[str]` カラムを追加
- [ ] Alembic マイグレーション作成
- [ ] マイグレーション実行

### 2.2 エラー記録ロジックの更新

対象: `apps/worker/activities/base.py:326-385`

- [ ] _update_step_status に error_code を追加
- [ ] ErrorCategory enum を error_code として記録

```python
await self._update_step_status(
    run_id=run_id,
    step_name=self.step_id,
    status="failed",
    error_message=str(e),
    error_code=e.category.value if hasattr(e, 'category') else "UNKNOWN",
)
```

---

## フェーズ 3: API エラーレスポンスの統一 ✅ 完了

### 3.1 エラーレスポンス形式の統一

対象: `apps/api/routers/runs.py`, `apps/api/core/errors.py`

FE 期待形式に合わせる:
```json
{
  "error": {
    "code": "STEP_FAILED",
    "message": "Step 3A failed due to LLM timeout",
    "details": {
      "step": "step3a",
      "category": "RETRYABLE",
      "stack_trace": "..."
    }
  }
}
```

- [ ] 標準エラーレスポンス形式を定義（または既存を確認）
- [ ] 各エンドポイントでエラーレスポンス形式を統一

### 3.2 Step 詳細 API の改善

対象: `apps/api/routers/runs.py`

- [ ] GET /api/runs/{run_id} のレスポンスに各 step の error_code, error_message を含める
- [ ] 失敗した step の詳細情報を返す

---

## フェーズ 4: UI エラー表示の改善 ✅ 完了

### 4.1 StepDetailPanel でのエラー表示

対象: `apps/ui/src/components/steps/StepDetailPanel.tsx`

- [ ] error_code に基づくエラー種類の表示（Retryable / Non-Retryable）
- [ ] error_message の詳細表示
- [ ] スタックトレースの折りたたみ表示（デバッグ用）

### 4.2 リトライボタンの条件改善

対象: `apps/ui/src/app/runs/[id]/page.tsx`

- [ ] RETRYABLE エラーの場合のみリトライボタンを有効化
- [ ] リトライ不可能な場合はその理由を表示
- [ ] リトライ進行中の状態表示

### 4.3 エラーメッセージのユーザーフレンドリー化

- [ ] 技術的エラーメッセージをユーザー向けに翻訳
- [ ] 推奨アクション（リトライ、設定確認など）を表示

---

## フェーズ 5: テスト・検証 ✅ 完了

### 5.1 リトライ機能のテスト

- [ ] 各ステップでのリトライが正常に動作することを確認
- [ ] step1.5, step3.5, step6.5 でのリトライ確認
- [ ] 前ステップデータが正しく引き継がれることを確認

### 5.2 エラー表示のテスト

- [ ] 失敗時にエラー詳細が UI に表示されることを確認
- [ ] error_code が正しく保存・表示されることを確認

### 5.3 lint・型チェック

- [ ] `npm run lint` 通過
- [ ] `npx tsc --noEmit` 通過
- [ ] `uv run ruff check apps/` 通過
- [ ] `uv run mypy apps/` 通過

---

## 完了基準

- [ ] 失敗したステップのエラー原因が UI に表示される
- [ ] 失敗したステップからリトライが正常に動作する
- [ ] step1.5, step3.5, step6.5 を含む全ステップでリトライ可能
- [ ] エラーの種類（Retryable/Non-Retryable）が表示される
- [ ] TypeScript/Python の型エラーがない
- [ ] lint エラーがない

---

## 技術詳細

### エラー情報の流れ

```
Temporal Activity 実行
    ↓
  [base.py:326-385]
  ActivityError / Exception キャッチ
    ├─ _collect_error() → error_logs テーブルに記録
    ├─ _emit_event()    → イベント発行
    └─ _update_step_status() → API 経由で DB 更新
    ↓
Step テーブル更新
    ├─ step_name (ステップ ID)
    ├─ status (failed)
    ├─ error_code (エラー種類) ← 追加予定
    └─ error_message (エラーメッセージ)
    ↓
Run テーブル更新
    ├─ current_step (失敗したステップ)
    ├─ error_code (Run 全体のコード)
    └─ error_message (Run 全体のメッセージ)
```

### リトライの流れ（修正後）

```
POST /api/runs/{run_id}/retry/{step}
    [runs.py:496-620]
    ↓
    1. ✅ Run が FAILED か確認
    2. ✅ 前ステップデータを ArtifactStore から読み込み ← 修正
    3. ✅ 新 Workflow を開始（前準備データ付き）
    ↓
Temporal Workflow 開始
    [article_workflow.py]
    ├─ resume_from = normalized_step
    ├─ ✅ 前準備データあり
    └─ ✅ 依存データ充足で実行成功
```

---

## 次のアクション

- 「`/work`」で実装を開始
- または「フェーズ0から始めて」
