# 全体コードレビュー修正計画（Plans7）

> **作成日**: 2026-01-12
> **目的**: プロジェクト全体のバグ温床となる問題の特定と修正
> **ステータス**: 計画中
> **除外項目**: モデル名設定、セキュリティ（developでの認証スキップ等）

---

## 概要

Plans1〜4でカバーされていない、または新たに発見された問題を修正します。

| フェーズ | 内容 | 件数 |
|---------|------|------|
| 0 | CRITICAL（即時対応） | 5件 |
| 1 | HIGH（早期対応） | 7件 |
| 2 | MEDIUM（中期対応） | 8件 |
| 3 | LOW（改善） | 5件 |
| 4 | テスト・検証 | - |

---

## 🔴 フェーズ0: CRITICAL `cc:TODO`

### 0-1. [CRITICAL] WebSocket connect() に tenant_id が渡されていない `cc:TODO`
**ファイル**: [websocket.py:319](apps/api/routers/websocket.py#L319)
**問題**:
- `ws_manager.connect(run_id, websocket)` でtenant_idが渡されていない
- ConnectionManager.connect() はtenant_id=Noneの場合、legacy_connectionsに格納
- broadcast() 時にtenant分離が効かず、他テナントにメッセージ漏洩の可能性
**修正方針**:
```python
# 修正前
await ws_manager.connect(run_id, websocket)

# 修正後
await ws_manager.connect(run_id, websocket, tenant_id=user.tenant_id)
```
**工数**: 15分

---

### 0-2. [CRITICAL] WebSocket disconnect() で tenant_id が渡されていない `cc:TODO`
**ファイル**: [websocket.py:334](apps/api/routers/websocket.py#L334)
**問題**:
- `ws_manager.disconnect(run_id, websocket)` でtenant_idが渡されていない
- disconnect時にlegacy_connectionsとactive_connections両方を探索する必要
- tenant_idなしでは正しくクリーンアップされない可能性
**修正方針**:
```python
# 修正前
ws_manager.disconnect(run_id, websocket)

# 修正後
ws_manager.disconnect(run_id, websocket, tenant_id=user.tenant_id)
```
**工数**: 15分

---

### 0-3. [CRITICAL] useRunProgress connect() の connectionState 依存配列問題 `cc:TODO`
**ファイル**: [useRunProgress.ts:91](apps/ui/src/hooks/useRunProgress.ts#L91)
**問題**:
- `connect` が `connectionState` を依存配列に含む
- useEffect (line 108-123) が `connect` を依存配列に含む
- connectionState変更 → connect再生成 → useEffect再実行 → 無限ループリスク
- runId変更時にconnect()が複数回呼ばれる可能性
**修正方針**:
```typescript
// connectionState を ref で管理し、依存配列から除外
const connectionStateRef = useRef<'idle' | 'connecting' | 'connected'>('idle');

const connect = useCallback(() => {
  if (connectionStateRef.current === 'connecting') return;
  connectionStateRef.current = 'connecting';
  // ...
}, [runId, handleMessage]); // connectionState を除外
```
**工数**: 30分

---

### 0-4. [CRITICAL] Temporal approve/reject シグナル競合 `cc:TODO`
**ファイル**: [article_workflow.py:94-104](apps/worker/workflows/article_workflow.py#L94)
**問題**:
- approve() と reject() シグナルが両方受信された場合の処理が未定義
- 両方のフラグが True になり、どちらが優先されるか不明確
- ワークフローが承認処理を続行しても rejected フラグがTrueのまま残る
**修正方針**:
```python
@workflow.signal
async def approve(self) -> None:
    """Signal handler for approval."""
    if self.rejected:
        workflow.logger.warning("Approve signal ignored: already rejected")
        return
    self.approved = True

@workflow.signal
async def reject(self, reason: str) -> None:
    """Signal handler for rejection."""
    if self.approved:
        workflow.logger.warning("Reject signal ignored: already approved")
        return
    self.rejected = True
    self.rejection_reason = reason
```
**工数**: 30分

---

### 0-5. [CRITICAL] sync_run_status のステータス上書き競合 `cc:TODO`
**ファイル**: [sync_status.py:66-68](apps/worker/activities/sync_status.py#L66)
**問題**:
- Workflow完了後にAPIが既にstatusを変更している可能性がある
- 例: APIがwaiting_approvalに設定 → sync_statusがcompletedで上書き
- ステートマシン違反が発生する可能性
**修正方針**:
```python
# 許可される状態遷移のみ実行
VALID_TRANSITIONS = {
    "running": ["completed", "failed", "cancelled", "waiting_approval"],
    "waiting_approval": ["running", "completed", "rejected"],
    # ...
}

if run.status != status:
    if status not in VALID_TRANSITIONS.get(run.status, []):
        logger.warning(f"Invalid state transition: {run.status} -> {status}, skipping")
    else:
        run.status = status
        updated_fields.append("status")
```
**工数**: 45分

---

## 🟠 フェーズ1: HIGH `cc:TODO`

### 1-1. [HIGH] broadcast_run_update/broadcast_step_event に tenant_id が渡されていない `cc:TODO`
**ファイル**: [websocket.py:104-138, 140-177](apps/api/routers/websocket.py#L104)
**問題**:
- `broadcast_run_update` と `broadcast_step_event` はtenant_idを受け取らない
- 内部で `broadcast(run_id, event_message)` を呼ぶがtenant_idなし
- runs.py からの呼び出し箇所もtenant_idを渡していない
**修正方針**:
1. broadcast_run_update/broadcast_step_event に tenant_id パラメータを追加
2. runs.py の呼び出し箇所を全て更新
**工数**: 60分

---

### 1-2. [HIGH] Run.step11_state のJSON直列化問題 `cc:TODO`
**ファイル**: [models.py:126-128](apps/api/db/models.py#L126)
**問題**:
- step11_state は `dict[str, Any]` 型でJSON保存
- datetime や non-serializable オブジェクトが混入する可能性
- step11.py で状態更新時に検証なし
**修正方針**:
- step11_state 更新前にJSON直列化可能性を検証
- datetime は ISO 文字列に変換
**工数**: 30分

---

### 1-3. [HIGH] TenantDBManager エンジンキャッシュのメモリリーク `cc:TODO`
**ファイル**: [tenant.py:104-105](apps/api/db/tenant.py#L104)
**問題**:
- `_engines` と `_session_factories` は無限に成長
- テナント数が増加すると接続プールが枯渇
- エンジンのクリーンアップ機構がない
**修正方針**:
- LRU キャッシュまたは TTL 付きキャッシュを導入
- 使用されていないエンジンを定期的に dispose
**工数**: 60分

---

### 1-4. [HIGH] ArtifactStore.get_by_path の response リソース解放漏れ `cc:TODO`
**ファイル**: [artifact_store.py:253-271](apps/api/storage/artifact_store.py#L253)
**問題**:
- MinIO response は read() 後に close()/release_conn() が必要
- 例外発生時にリソースがリークする
**修正方針**:
```python
async def get_by_path(self, tenant_id: str, run_id: str, step: str) -> bytes | None:
    # ...
    response = None
    try:
        response = self.client.get_object(self.bucket, path)
        return response.read()
    finally:
        if response:
            response.close()
            response.release_conn()
```
**工数**: 20分

---

### 1-5. [HIGH] Activity heartbeat の欠如（長時間Activity） `cc:TODO`
**ファイル**: [base.py:205-338](apps/worker/activities/base.py#L205)
**問題**:
- STEP_TIMEOUTS で 600秒以上のタイムアウトを持つ Activity がある
- heartbeat がないと Temporal がハング検出できない
- ワーカー障害時にタイムアウトまで待機する必要
**修正方針**:
- BaseActivity に定期的な heartbeat 送信を追加
- タイムアウト > 120秒 の場合、30秒ごとに heartbeat
**工数**: 45分

---

### 1-6. [HIGH] retry_step/resume_from_step の楽観的ロック欠如 `cc:TODO`
**ファイル**: [runs.py:570-788, 790-1061](apps/api/routers/runs.py#L570)
**問題**:
- approve/reject は `expected_updated_at` で楽観的ロックを実装
- retry_step と resume_from_step は楽観的ロックがない
- 同時リクエストで古い設定が使用される可能性
**修正方針**:
- retry_step と resume_from_step に `expected_updated_at` パラメータを追加
- 既存APIとの後方互換性のためオプショナルに
**工数**: 45分

---

### 1-7. [HIGH] clone_run のワークフロー開始失敗時の孤立Run `cc:TODO`
**ファイル**: [runs.py:1176-1239](apps/api/routers/runs.py#L1176)
**問題**:
- クローン作成後にワークフロー開始が失敗すると、Runが孤立
- status が `pending` または `workflow_starting` のまま放置
- クリーンアップ機構がない
**修正方針**:
- ワークフロー開始失敗時に Run を削除またはエラーステータスに更新
- または定期的なクリーンアップジョブを追加
**工数**: 30分

---

## 🟡 フェーズ2: MEDIUM `cc:TODO`

### 2-1. [MEDIUM] useRunProgress のuseEffect依存配列に connect/disconnect 含む `cc:TODO`
**ファイル**: [useRunProgress.ts:108-123](apps/ui/src/hooks/useRunProgress.ts#L108)
**問題**:
- useEffect が `[autoConnect, connect, disconnect, runId]` を依存配列に含む
- connect/disconnect は useCallback で毎回再生成される可能性
- 不要な再接続が発生するリスク
**修正方針**:
- connect/disconnect を ref で保持し、依存配列から除外
**工数**: 25分

---

### 2-2. [MEDIUM] API_BASE_URL の空文字列フォールバック `cc:TODO`
**ファイル**: [api.ts:34](apps/ui/src/lib/api.ts#L34)
**問題**:
- `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"`
- 空文字列 `""` は falsy なので localhost にフォールバック
- 本番環境で誤設定時にサイレント失敗
**修正方針**:
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL?.trim() || "http://localhost:8000";
if (process.env.NODE_ENV === "production" && API_BASE.includes("localhost")) {
  console.warn("WARNING: Using localhost API in production mode");
}
```
**工数**: 15分

---

### 2-3. [MEDIUM] Step11 signals のフェーズ検証不足 `cc:TODO`
**ファイル**: [article_workflow.py:133-205](apps/worker/workflows/article_workflow.py#L133)
**問題**:
- step11_* シグナルハンドラーがフェーズの前提条件を検証していない
- 例: step11_confirm_positions は 11B フェーズでのみ有効であるべき
- 順序外のシグナルで状態が破損する可能性
**修正方針**:
```python
@workflow.signal
async def step11_confirm_positions(self, positions: list[dict[str, Any]]) -> None:
    if self.step11_phase not in ("11A", "11B"):
        workflow.logger.warning(f"step11_confirm_positions ignored: wrong phase {self.step11_phase}")
        return
    self.step11_phase = "11B"
    self.step11_positions_confirmed = {"positions": positions}
```
**工数**: 45分

---

### 2-4. [MEDIUM] パストラバーサル検証の二重エンコーディング対策不足 `cc:TODO`
**ファイル**: [artifact_store.py:29](apps/api/storage/artifact_store.py#L29)
**問題**:
- `PATH_TRAVERSAL_PATTERN = re.compile(r"\.\./|\.\.\\|%2e%2e|%252e")`
- `%252e%252e` (二重エンコード) を検出していない
- `%2e%2e%2f` (部分エンコード) のバリエーションも未対応
**修正方針**:
```python
PATH_TRAVERSAL_PATTERN = re.compile(
    r"\.\./|\.\.\\|"  # 通常のトラバーサル
    r"%2e%2e|%252e%252e|"  # URLエンコード
    r"%2e%2e%2f|%2e%2e%5c|"  # 混合エンコード
    r"\.%2e|%2e\.",  # 部分エンコード
    re.IGNORECASE
)
```
**工数**: 20分

---

### 2-5. [MEDIUM] load_step_data のエラーハンドリングが曖昧 `cc:TODO`
**ファイル**: [base.py:53-70](apps/worker/activities/base.py#L53)
**問題**:
- すべての例外を catch して None を返す
- 「データが存在しない」と「アクセスエラー」が区別できない
- 後続処理で誤った前提で動作する可能性
**修正方針**:
- ArtifactNotFoundError は None を返す
- その他の例外は再 raise
**工数**: 25分

---

### 2-6. [MEDIUM] save_step_data のエラーハンドリングが曖昧 `cc:TODO`
**ファイル**: [base.py:73-110](apps/worker/activities/base.py#L73)
**問題**:
- すべての例外を catch して None を返す
- 保存失敗時に None が返され、呼び出し元が成功と誤認する可能性
**修正方針**:
- 保存失敗は例外を再 raise
- 呼び出し元で適切にハンドリング
**工数**: 25分

---

### 2-7. [MEDIUM] ConnectionManager の legacy_connections 削除タイミング `cc:TODO`
**ファイル**: [websocket.py:33, 51-56, 69-75](apps/api/routers/websocket.py#L33)
**問題**:
- `_legacy_connections` は後方互換のために存在
- しかしすべての新規接続が tenant_id なしで legacy に格納されている (0-1, 0-2の問題)
- 修正後は legacy_connections を段階的に廃止すべき
**修正方針**:
- 0-1, 0-2 修正後、legacy_connections への新規追加を警告ログ
- 将来的に legacy_connections を削除
**工数**: 20分

---

### 2-8. [MEDIUM] Run.config の型安全性 `cc:TODO`
**ファイル**: [models.py:123](apps/api/db/models.py#L123)
**問題**:
- `config: Mapped[dict[str, Any] | None]` は任意の構造を許容
- スキーマ検証なしで保存・読み込み
- 不正な構造で後続処理が失敗する可能性
**修正方針**:
- Pydantic モデルで config 構造を定義
- 保存前にバリデーション
**工数**: 45分

---

## 🟢 フェーズ3: LOW `cc:TODO`

### 3-1. [LOW] API client の重複したエラーハンドリング `cc:TODO`
**ファイル**: [api.ts:102-113](apps/ui/src/lib/api.ts#L102)
**問題**:
- `response.json().catch(() => null)` で JSON パース失敗を無視
- エラーレスポンスの詳細が失われる
**修正方針**:
- JSON パース失敗時も適切なエラーメッセージを生成
**工数**: 15分

---

### 3-2. [LOW] normalizeStepForApi の不完全なマッピング `cc:TODO`
**ファイル**: [useRun.ts:12-20](apps/ui/src/hooks/useRun.ts#L12)
**問題**:
- `step3` → `step3a` のマッピングのみ
- 他のグループ化ステップ（step7など）のマッピングがない
**修正方針**:
- 全グループ化ステップのマッピングを追加
**工数**: 15分

---

### 3-3. [LOW] TenantDBManager._get_tenant_db_url の二重検証 `cc:TODO`
**ファイル**: [tenant.py:137-140](apps/api/db/tenant.py#L137)
**問題**:
- `validate_tenant_id` の呼び出しが複数箇所で重複
- パフォーマンスへの影響は軽微だが冗長
**修正方針**:
- 入口で一度だけ検証するように整理
**工数**: 15分

---

### 3-4. [LOW] workflow_logger の import 位置 `cc:TODO`
**ファイル**: [parallel.py:19](apps/worker/workflows/parallel.py#L19)
**問題**:
- `workflow_logger = workflow.logger` はモジュールレベルで実行
- ワークフローコンテキスト外でのアクセスで問題が発生する可能性
**修正方針**:
- 関数内でロガーを取得
**工数**: 10分

---

### 3-5. [LOW] STEP_TIMEOUTS の定数と実際のタイムアウトの乖離確認 `cc:TODO`
**ファイル**: [article_workflow.py:24-44](apps/worker/workflows/article_workflow.py#L24)
**問題**:
- STEP_TIMEOUTS が仕様書と一致しているか検証が必要
- step11 が 600秒だが、画像生成の実際の所要時間と合っているか
**修正方針**:
- 仕様書 (workflow.md) との整合性を確認
- 必要に応じて調整
**工数**: 30分

---

## 🔵 フェーズ4: テスト・検証 `cc:TODO`

### 4-1. 修正箇所のユニットテスト追加 `cc:TODO`
- [ ] WebSocket tenant isolation テスト
- [ ] connectionState 競合テスト
- [ ] approve/reject シグナル競合テスト
- [ ] sync_status 状態遷移テスト
- [ ] パストラバーサル検証テスト

### 4-2. 統合テスト実行 `cc:TODO`
```bash
# Backend テスト
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v

# Frontend テスト
npm run lint --prefix apps/ui
npx tsc --noEmit --project apps/ui/tsconfig.json
```

---

## 完了基準

- [ ] 全フェーズの修正完了
- [ ] TypeScript エラーがない
- [ ] Python lint/type エラーがない
- [ ] ユニットテスト追加・通過
- [ ] 統合テスト通過

---

## 関連ドキュメント

- [Plans1.md](Plans1.md) - Backend 統合修正計画
- [Plans2.md](Plans2.md) - Worker 統合修正計画
- [Plans3.md](Plans3.md) - Frontend 統合修正計画
- [Plans4.md](Plans4.md) - 設定・テスト・インフラ統合修正計画

---

## 次のアクション

- 「`/work Plans7.md`」でフェーズ0から実装開始
