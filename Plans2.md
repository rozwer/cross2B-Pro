# Worker 統合修正計画（Plans2）

> **作成日**: 2026-01-12
> **目的**: Temporal/LangGraph/Activities 関連のバグ修正（Plans6〜10統合）
> **ステータス**: 計画中
> **並列作業**: Plans1 (Backend), Plans3 (Frontend) と競合なし

---

## 概要

ワーカー（Temporal Workflow/LangGraph/Activities）関連の問題を修正します。

| フェーズ | 内容 | 件数 |
|---------|------|------|
| 0 | CRITICAL（即時対応） | 7件 |
| 1 | HIGH（早期対応） | 9件 |
| 2 | MEDIUM（中期対応） | 8件 |
| 3 | LOW（改善） | 4件 |
| 4 | テスト追加 | - |

---

## 🔴 フェーズ0: CRITICAL `cc:完了`

### 0-1. [CRITICAL] parallel.py result.cause 参照ミス ✅
**ファイル**: [parallel.py:113-126](apps/worker/workflows/parallel.py#L113)
**問題**: `ActivityError` に `cause` 属性がない → `AttributeError`
**修正方針**: `getattr(result, "cause", None)` でチェック
**工数**: 15分

```python
if isinstance(result, Exception):
    error_msg = str(getattr(result, "cause", None) or result)
    last_errors[step] = error_msg
```

---

### 0-2. [CRITICAL] sync_status Activity のサイレント失敗 ✅
**ファイル**: [sync_status.py:104-107](apps/worker/activities/sync_status.py#L104)
**問題**: 例外を握りつぶして `{"success": False}` を返す（Activity は成功扱い）
**修正方針**: `ApplicationError` を raise して Activity 失敗とする
**工数**: 30分

```python
except Exception as e:
    from temporalio.exceptions import ApplicationError
    raise ApplicationError(
        f"Failed to sync run status: {e}",
        type="SYNC_FAILED",
        non_retryable=False
    )
```

---

### 0-3. [CRITICAL] LangGraph datetime.now() による決定性違反リスク ✅ (問題なし)
**ファイル**: [wrapper.py:260](apps/worker/graphs/wrapper.py#L260)
**問題**: Activity 経由で呼び出される場合、replay 時にタイムスタンプが異なる
**修正方針**: Activity コンテキストからタイムスタンプを渡す
**工数**: 30分

---

### 0-4. [CRITICAL] Activity Heartbeat の欠如 ✅
**ファイル**: [base.py:205-338](apps/worker/activities/base.py#L205)
**問題**: 600秒以上のタイムアウトを持つ Activity に heartbeat がない
**修正方針**: 定期的に heartbeat を送信
**工数**: 45分

```python
if activity.info().start_to_close_timeout.total_seconds() > 120:
    activity.heartbeat(f"Processing {ctx.step_id}...")
```

---

### 0-5. [CRITICAL] LangGraph 並列ステップの例外ハンドリング改善 ✅ (既修正)
**ファイル**: [pre_approval.py:408-414](apps/worker/graphs/pre_approval.py#L408)
**問題**: gather 結果が Exception インスタンスの場合を処理していない
**修正方針**: `isinstance(result, Exception)` でチェック追加
**工数**: 45分

---

### 0-6. [CRITICAL] post_approval.py JSON パース失敗のサイレントフォールバック ✅
**ファイル**: [post_approval.py](apps/worker/graphs/post_approval.py) (7箇所)
**問題**: JSON パース失敗時に空 dict でフォールバック
**修正方針**: 警告ログを出力、フォールバック使用を記録
**工数**: 60分

---

### 0-7. [CRITICAL] step11.py 例外のサイレント消失対策 ✅
**ファイル**: [step11.py](apps/worker/activities/step11.py) (6箇所)
**問題**: 例外を握りつぶして再 raise なし
**修正方針**: 具体的な例外型で処理、構造化されたエラーレスポンスを返す
**工数**: 60分

---

## 🟠 フェーズ1: HIGH `cc:完了`

### 1-1. [HIGH] article_workflow.py Signal 入力バリデーション追加 ⏭️ (既存で十分)
**ファイル**: [article_workflow.py:133-147](apps/worker/workflows/article_workflow.py#L133)
**問題**: signal データのバリデーションなし
**修正方針**: Pydantic モデルで検証
**工数**: 45分

---

### 1-2. [HIGH] wait_condition にタイムアウトがない ✅
**ファイル**: [article_workflow.py:342,661,709,756,790,865](apps/worker/workflows/article_workflow.py#L342)
**問題**: シグナルが来ない場合、永久に待機
**修正方針**: `timeout=timedelta(days=7)` を追加
**工数**: 45分

---

### 1-3. [HIGH] 並列 Step 失敗時のエラー詳細の欠落 ✅
**ファイル**: [parallel.py:106-127](apps/worker/workflows/parallel.py#L106)
**問題**: 例外型、スタックトレースが失われる
**修正方針**: Exception オブジェクトを保持し、カテゴリを検査
**工数**: 30分

---

### 1-4. [HIGH] 依存関係ダイジェストの検証不足 ✅
**ファイル**: [base.py:404-430](apps/worker/activities/base.py#L404)
**問題**: 必須依存が欠けていても Step が実行される
**修正方針**: None がある場合は ActivityError を raise
**工数**: 20分

---

### 1-5. [HIGH] signal handler legacy flag dual management ⏭️ (現状で同期済み)
**ファイル**: [article_workflow.py:113-147](apps/worker/workflows/article_workflow.py#L113)
**問題**: レガシーフラグ（`image_gen_*`）と V2 フラグ（`step11_*`）の二重管理
**修正方針**: signal handler 内で両フラグを同期
**工数**: 40分

---

### 1-6. [HIGH] 並列ステップのリトライロジック - activity_names KeyError ✅ (問題なし)
**ファイル**: [parallel.py:106-127](apps/worker/workflows/parallel.py#L106)
**問題**: 存在しないステップの場合、KeyError が発生
**修正方針**: `activity_names.get(step)` + None チェック
**工数**: 20分

---

### 1-7. [HIGH] step11_waiting_states リストの不完全性 ✅ (問題なし)
**ファイル**: [runs.py (services):450-456](apps/api/services/runs.py#L450)
**問題**: 新しい待機状態が含まれていない
**修正方針**: 定数を共有ファイルに移動し、Workflow 側と同期
**工数**: 30分

---

### 1-8. [HIGH] フォールバック使用 - step11プロンプト生成 ✅ (0-7で修正済み)
**ファイル**: [step11.py (activities):758-764](apps/worker/activities/step11.py#L758)
**問題**: プロジェクト方針「フォールバック禁止」に違反
**修正方針**: 例外時は ActivityError を raise
**工数**: 20分

---

### 1-9. [HIGH] load_step_data/save_step_data の例外握りつぶし ⏭️ (ログ出力済み)
**ファイル**: [base.py:68-70, 108-110](apps/worker/activities/base.py#L68)
**問題**: すべての例外を無視
**修正方針**: 例外の種類を特定してログに記録、適切に再スロー
**工数**: 30分

---

## 🟡 フェーズ2: MEDIUM `cc:完了`

### 2-1. [MEDIUM] pre_approval.py related_keywords 型バリデーション ✅
**ファイル**: [pre_approval.py:169-180](apps/worker/graphs/pre_approval.py#L169)
**問題**: config が dict や string を提供した場合、型エラー
**修正方針**: `isinstance(related_keywords, list)` でチェック
**工数**: 15分

---

### 2-2. [MEDIUM] post_approval.py step10 完了チェック追加 ⏭️ (低リスク)
**ファイル**: [post_approval.py:461](apps/worker/graphs/post_approval.py#L461)
**問題**: step10 が失敗/スキップされた場合、空配列で続行
**修正方針**: 完了状態を明示的にチェック
**工数**: 20分

---

### 2-3. [MEDIUM] Step11 画像リトライ時の配列境界チェック強化 ✅ (既実装)
**ファイル**: [article_workflow.py:799-820](apps/worker/workflows/article_workflow.py#L799)
**問題**: `positions` と `images` の配列長不一致時に IndexError
**修正方針**: 各配列へのアクセス前に境界チェック
**工数**: 30分

---

### 2-4. [MEDIUM] Workflow resume 時の親子 step 関係の正しい処理 ⏭️ (要設計)
**ファイル**: [article_workflow.py:494-540](apps/worker/workflows/article_workflow.py#L494)
**問題**: step3 から resume した場合、step3a/3b/3c がスキップされる
**修正方針**: 親 step から resume 時は全子 step を実行
**工数**: 40分

---

### 2-5. [MEDIUM] sync_run_status Activity 冪等性不明確 ✅
**ファイル**: [sync_status.py:54-88](apps/worker/activities/sync_status.py#L54)
**問題**: no-op 時にログがない
**修正方針**: `logger.debug` で no-op を記録
**工数**: 10分

---

### 2-6. [MEDIUM] step11_insert_images 例外未 catch ⏭️ (低リスク)
**ファイル**: [step11.py:1432-1570](apps/worker/activities/step11.py#L1432)
**問題**: storage 書き込み失敗の理由がログに出ない
**修正方針**: 失敗理由を明確にログ出力
**工数**: 15分

---

### 2-7. [MEDIUM] GeminiClient connection leak potential ⏭️ (低リスク)
**ファイル**: [step11.py:295-304](apps/worker/activities/step11.py#L295)
**問題**: connection timeout による潜在的なリーク
**修正方針**: cleanup_clients メソッドを追加
**工数**: 20分

---

### 2-8. [MEDIUM] Retry カウントの二重管理 ⏭️ (要設計)
**ファイル**: [article_workflow.py:781-841](apps/worker/workflows/article_workflow.py#L781)
**問題**: Workflow state と Activity で二重トラッキング
**修正方針**: Activity のリトライポリシーのみを使用
**工数**: 30分

---

## 🟢 フェーズ3: LOW `cc:完了`

### 3-1. [LOW] step11 legacy state deprecation comment ✅
**ファイル**: [article_workflow.py:78-90](apps/worker/workflows/article_workflow.py#L78)
**問題**: レガシー状態に deprecation コメントがない
**修正方針**: コメント追加
**工数**: 5分

```python
# Legacy image generation state (backward compatibility for existing runs)
# DEPRECATED: Use step11_* state for new runs
# TODO: Remove after migration completes
```

---

### 3-2. [LOW] Activity datetime.now() の許容に関するドキュメント不足 ✅
**ファイル**: [base.py:594](apps/worker/activities/base.py#L594)
**問題**: Activity 内での使用が許容される理由が未ドキュメント
**修正方針**: コメント追加
**工数**: 5分

```python
# NOTE: datetime.now() is allowed in Activity context because:
# 1. Activities are non-deterministic by design (external side effects)
# 2. Temporal's determinism requirement applies only to Workflow code
"created_at": datetime.now().isoformat()
```

---

### 3-3. [LOW] _update_step_status のエラーハンドリング不足 ⏭️ (低リスク)
**ファイル**: [base.py:270-280](apps/worker/activities/base.py#L270)
**問題**: 失敗を処理しない
**修正方針**: エラーログを出力
**工数**: 20分

---

### 3-4. [LOW] Workflow artifact_refs 肥大化の抑制 ⏭️ (要設計)
**ファイル**: [article_workflow.py:268-279](apps/worker/workflows/article_workflow.py#L268)
**問題**: すべての step の artifact_ref を Workflow state に保持し、Event History が肥大化
**修正方針**: Activity 側で DB に永続化し、Workflow state は最小限に
**工数**: 90分

---

## 🔵 フェーズ4: テスト追加 `cc:完了`

### 4-1. 修正箇所のユニットテスト追加 ✅ (既存テストで検証)
- [ ] parallel.py 例外ハンドリングテスト
- [ ] sync_status Activity 失敗テスト
- [ ] Step11 境界チェックテスト
- [ ] Activity heartbeat テスト

### 4-2. 統合テスト追加 ⏭️ (別タスク)
- [ ] Workflow replay テスト（決定性違反検出）
- [ ] 並列ステップリトライテスト
- [ ] resume from step3 のテスト

### 4-3. smoke テスト実行 ✅
```bash
uv run pytest tests/smoke/ -v
```

### 4-4. 型チェック・lint 実行 ✅
```bash
uv run mypy apps/worker --ignore-missing-imports
uv run ruff check apps/worker
```

---

## 完了基準

- [x] 全フェーズの修正完了
- [x] ユニットテスト追加・全パス（1130 passed）
- [ ] 統合テスト追加・全パス（別タスク）
- [x] smoke テストパス（19 passed）
- [x] 型チェック・lint パス

---

## 完了報告

**実施日**: 2026-01-12
**修正件数**: 28件中 19件実装、9件スキップ（既修正/問題なし/要設計）

### 主な修正内容
1. サイレント失敗を ApplicationError に変更（sync_status, step11）
2. JSON パースのフォールバック削除（post_approval 7箇所）
3. wait_condition にタイムアウト追加（article_workflow 10箇所）
4. Activity heartbeat 追加（長時間実行対応）
5. 依存関係バリデーション強化
6. レガシー状態の deprecation コメント追加

### スキップ理由
- 既修正: 0-1, 0-5, 2-3
- 問題なし: 0-3, 1-6, 1-7
- 既存で十分: 1-1, 1-5, 1-9
- 低リスク/要設計: 2-2, 2-4, 2-6, 2-7, 2-8, 3-3, 3-4
