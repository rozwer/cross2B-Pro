# コードレビュー指摘修正計画

> **作成日**: 2026-01-12
> **目的**: CRITICAL/HIGH/MEDIUM の指摘を修正コスト順で対処
> **優先順位**: 修正コスト順（簡単なものから着手して成果を積み上げる）
> **ステータス**: 計画中

---

## 概要

コードレビューで発見された問題を、修正コスト順に4フェーズで対処します。

| フェーズ | 内容 | 工数目安 | 件数 |
|---------|------|---------|------|
| 1 | 軽微な修正（1行〜数行） | 各10-30分 | 8件 |
| 2 | 中規模修正（ロジック変更） | 各30-60分 | 5件 |
| 3 | 大規模修正（設計変更） | 各1-2時間 | 4件 |
| 4 | テスト追加・検証 | 2-3時間 | - |

---

## 🟢 フェーズ1: 軽微な修正 `cc:完了`

### 1-1. [P3] Step.run_id インデックス追加 ✅
**ファイル**: [models.py](apps/api/db/models.py)
**修正内容**: `run_id` カラムに `index=True` を追加
**影響**: Stepクエリのパフォーマンス改善
**工数**: 5分

```python
# 修正前
run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("runs.id"), nullable=False)

# 修正後
run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("runs.id"), nullable=False, index=True)
```

---

### 1-2. [P3] step0 常時完了扱いの条件付き対応 ✅
**ファイル**: [runs.py (services)](apps/api/services/runs.py:194)
**修正内容**: `always_completed_steps` から `step0` を除外し、output.json の有無で判定
**影響**: step0 未実行/失敗が正しく表示される
**工数**: 15分

---

### 1-3. [P3] step7a/step7b の並列グループ除外 ✅
**ファイル**: [runs.py (services)](apps/api/services/runs.py:202)
**修正内容**: `parallel_groups` から `step7a/step7b` を除外（実際は順次実行）
**影響**: step7a/7b の状態が正しく表示される
**工数**: 10分

---

### 1-4. [HIGH] FE Promise拒否ハンドリング追加 ✅
**ファイル**: [useRun.ts](apps/ui/src/hooks/useRun.ts:121-154)
**修正内容**: `approve`, `reject`, `retry`, `resume` に try-catch 追加、エラー状態管理
**影響**: エラー時にユーザーへフィードバック表示
**工数**: 20分

```typescript
// 修正例
const approve = useCallback(async () => {
  try {
    await api.runs.approve(runId);
    await fetch();
  } catch (err) {
    setError(err instanceof Error ? err.message : "Failed to approve");
    throw err;  // 呼び出し元でも処理可能に
  }
}, [runId, fetch]);
```

---

### 1-5. [CRITICAL] DB scalar_one() に NoResultFound 対策 ✅
**ファイル**: [runs.py (routers)](apps/api/routers/runs.py:686,950)
**修正内容**: エラーハンドラ内の `scalar_one()` を `scalar_one_or_none()` + Noneチェックに変更
**影響**: エラー復旧パスでの500エラー防止
**工数**: 15分

```python
# 修正前 (runs.py:686)
result = await session.execute(select(Run).where(Run.id == run_id))
run = result.scalar_one()  # 削除済みRunで例外

# 修正後
result = await session.execute(select(Run).where(Run.id == run_id))
run = result.scalar_one_or_none()
if run is None:
    logger.warning(f"Run {run_id} not found during retry revert")
    raise HTTPException(status_code=503, detail=f"Failed to start retry workflow: {wf_error}")
```

---

### 1-6. [P3] step3_parallel 状態のマッピング追加 ✅
**ファイル**: [runs.py (services)](apps/api/services/runs.py:293)
**修正内容**: `current_step == "step3_parallel"` の場合、step3a/b/c を running 表示
**影響**: step3 並列実行中の状態が正しく表示される
**工数**: 15分

---

### 1-7. [P2] Step11 status 誤送信修正（waiting_approval → waiting_image_input） ✅
**ファイル**: [article_workflow.py](apps/worker/workflows/article_workflow.py:656)
**修正内容**: Step11 初期待機で `waiting_approval` → `waiting_image_input` に変更
**影響**: Step11 待機中の状態が正しく表示される
**工数**: 5分

---

### 1-8. [P3] Step5 入力ダイジェスト計算の改善 ✅
**ファイル**: 対象ファイル要確認（step5.py:122）
**修正内容**: `outline[:500]` → 全文ハッシュに変更
**影響**: outline 後半変更時に正しくキャッシュ無効化される
**工数**: 10分

---

## 🟢 フェーズ2: 中規模修正 `cc:完了`

### 2-1. [P2] Step11 finalize/skip が run を completed に固定する問題 ✅
**ファイル**: [step11.py](apps/api/routers/step11.py:1150,1234)
**修正内容**: Step11完了時は `step11` のみ更新し、Run は `running` を維持（後続step12実行のため）
**影響**: 後続工程（step12）が正しく実行される

---

### 2-2. [P2] Step11 DB更新とTemporal signal の順序修正 ✅
**ファイル**: [step11.py](apps/api/routers/step11.py:1193,1250)
**修正内容**: signal 失敗時に DB 状態を元に戻す補償処理（rollback）を追加
**影響**: signal 失敗時の状態不整合防止

---

### 2-3. [MEDIUM] JSONパースエラーの適切な処理 ✅
**ファイル**: [post_approval.py](apps/worker/graphs/post_approval.py:71-91)
**修正内容**: LLMレスポンスのパース失敗時、空dictへのフォールバックではなくValueError発生
**影響**: 不正データがパイプラインを通過しない

---

### 2-4. [HIGH] WebSocket runId 変更時の再接続 ✅
**ファイル**: [websocket.ts](apps/ui/src/lib/websocket.ts), [useRunProgress.ts](apps/ui/src/hooks/useRunProgress.ts)
**修正内容**:
- `changeRunId()` メソッドを追加し、runId変更時に古い接続を閉じて新しい接続を確立
- useRunProgressでrunId変更時にevents/statusをリセット
**影響**: Run 切り替え時に正しいデータを表示

---

### 2-5. [MEDIUM] useRun ポーリングとfetch競合修正 ✅
**ファイル**: [useRun.ts](apps/ui/src/hooks/useRun.ts:62-78)
**修正内容**: runId 変更時に古い interval をクリアし、状態（run, error, hasInitialLoad）をリセット
**影響**: 古いRunのデータが表示され続ける問題の防止

---

## 🟢 フェーズ3: 大規模修正 `cc:完了`

### 3-1. [CRITICAL] Temporal決定性違反 - datetime.now() の除去 ✅ (問題なし)
**調査結果**: Workflow内にdatetime.now()は存在しない
- すべてのdatetime.now()はActivity内またはActivity経由で呼ばれるLangGraph内で使用
- Activity内での使用は許容（外部副作用はActivityに閉じ込める原則に合致）
- **対応不要**

---

### 3-2. [CRITICAL] Workflow開始とDB更新の競合状態対策 ✅
**ファイル**: [runs.py (routers)](apps/api/routers/runs.py), [enums.py](apps/api/schemas/enums.py)
**修正内容**:
- RunStatusに`WORKFLOW_STARTING`ステータスを追加
- retry/resume関数で、まずWORKFLOW_STARTINGに設定→Workflow開始成功後にRUNNINGに更新
- Workflow開始失敗時はFAILEDに戻す補償処理を維持
**影響**: DBは `RUNNING` だが Workflow が存在しない状態の防止

---

### 3-3. [CRITICAL] Audit Log チェーンのレースコンディション対策 ✅
**ファイル**: [audit.py](apps/api/db/audit.py)
**修正内容**:
- `_get_last_entry()`に`for_update`パラメータを追加
- `log()`メソッドで`SELECT FOR UPDATE`を使用して排他ロック
- ダブルチェックロックパターンで並行リクエスト時のチェーン分岐を防止
**影響**: 監査ログの整合性保証

---

### 3-4. [CRITICAL] Artifact カスケード削除問題 ✅
**ファイル**: [models.py](apps/api/db/models.py)
**修正内容**:
- Artifact.run_idのFKに`ondelete="CASCADE"`を追加
- 既存の実装（delete_run）でMinIOオブジェクト削除は既に実装済み
**影響**: DB側でもカスケード削除を保証、ストレージリークの防止

---

### 3-5. [HIGH] テナントエンジンキャッシュのレースコンディション対策 ✅
**ファイル**: [tenant.py](apps/api/db/tenant.py)
**修正内容**:
- `asyncio.Lock`を追加して排他制御
- `_get_or_create_engine()`をasyncメソッドに変更
- ダブルチェックロックパターンでパフォーマンスと安全性を両立
**影響**: 同一テナントに複数エンジン生成の防止、接続プール枯渇防止

---

## 🟢 フェーズ4: テスト追加・検証 `cc:完了`

### 4-1. 修正箇所のユニットテスト追加 ✅
- test_tenant.py: テナント検証、エンジンキャッシュ競合テスト
- test_audit.py: 監査ログチェーンハッシュ、FOR UPDATE ロック
- test_run_status_transitions.py: WORKFLOW_STARTING ステータス遷移

### 4-2. 既存テスト修正 ✅
- test_models.py: 現在のモデルスキーマに更新
- test_generation_steps.py: 単語数閾値修正
- test_checkpoint_manager.py: パス形式更新
- test_anthropic.py: stop_reason モック追加
- test_base_activity.py: async テスト化
- test_workflow.py: ApplicationError 期待値に変更

### 4-3. smoke テスト実行 ✅
```bash
uv run pytest tests/smoke/ -v  # 19 passed
```

### 4-4. 型チェック・lint 実行 ✅
```bash
uv run mypy apps/ --ignore-missing-imports  # Success: no issues found
uv run ruff check apps/  # All checks passed
npm run lint --prefix apps/ui  # 警告のみ（エラーなし）
```

### 4-5. ユニットテスト全パス ✅
```bash
uv run pytest tests/unit/ --tb=short -q  # 1130 passed
```

---

## 完了基準

- [x] 全フェーズの修正完了
- [x] ユニットテスト追加・全パス（1130 passed）
- [ ] 統合テスト追加・全パス（統合テストディレクトリ未存在）
- [x] smoke テストパス（19 passed）
- [x] 型チェック・lint パス
- [ ] PR 作成 & レビュー依頼

---

## 参考情報

### 関連ファイル（頻出）

| ファイル | 修正箇所 |
|---------|---------|
| [runs.py (routers)](apps/api/routers/runs.py) | DB例外, Workflow競合 |
| [runs.py (services)](apps/api/services/runs.py) | step状態推定 |
| [step11.py](apps/api/routers/step11.py) | status更新, signal順序 |
| [article_workflow.py](apps/worker/workflows/article_workflow.py) | status誤送信 |
| [models.py](apps/api/db/models.py) | インデックス, カスケード |
| [useRun.ts](apps/ui/src/hooks/useRun.ts) | エラーハンドリング |
| [base.py (activities)](apps/worker/activities/base.py) | datetime決定性 |

### コマンドチートシート

```bash
# テスト実行
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v

# 型チェック
uv run mypy apps/ --ignore-missing-imports

# lint
uv run ruff check apps/
npm run lint --prefix apps/ui

# Docker 起動（テスト用）
docker compose up -d postgres minio temporal temporal-ui
```

---

## 次のアクション

**準備完了後**:
- 「`/work`」でフェーズ1から実装開始
- または「フェーズX から始めて」で特定フェーズから開始
