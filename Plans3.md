# Frontend 統合修正計画（Plans3）

> **作成日**: 2026-01-12
> **完了日**: 2026-01-12
> **目的**: React/TypeScript/UI 関連のバグ修正（Plans6〜10統合）
> **ステータス**: ✅ 完了
> **並列作業**: Plans1 (Backend), Plans2 (Worker) と競合なし

---

## 概要

フロントエンド（React/TypeScript/UI）関連の問題を修正します。

| フェーズ | 内容 | 件数 |
|---------|------|------|
| 0 | CRITICAL（即時対応） | 5件 |
| 1 | HIGH（早期対応） | 8件 |
| 2 | MEDIUM（中期対応） | 10件 |
| 3 | LOW（改善） | 6件 |
| 4 | テスト追加 | - |

---

## 🔴 フェーズ0: CRITICAL ✅ 完了

### 0-1. [CRITICAL] ImageGenerationWizard の無限 API ループ `cc:TODO`
**ファイル**: [ImageGenerationWizard.tsx:111-162](apps/ui/src/components/imageGeneration/ImageGenerationWizard.tsx#L111)
**問題**: `state.phase` が依存配列に含まれ、setState が phase を変更する可能性
**修正方針**: useRef で前回 phase を追跡し、変更時のみ fetch
**工数**: 45分

```typescript
const prevPhaseRef = useRef(state.phase);
useEffect(() => {
  if (!isOpen || prevPhaseRef.current === state.phase) return;
  prevPhaseRef.current = state.phase;
  // fetch logic
}, [isOpen, state.phase, runId]);
```

---

### 0-2. [CRITICAL] useRun ポーリングのメモリリーク `cc:TODO`
**ファイル**: [useRun.ts:95-120](apps/ui/src/hooks/useRun.ts#L95)
**問題**: アンマウント後も fetch が実行され、state 更新で React 警告
**修正方針**: isMountedRef + AbortController を使用
**工数**: 45分

```typescript
const isMountedRef = useRef(true);
const abortControllerRef = useRef<AbortController | null>(null);

useEffect(() => {
  isMountedRef.current = true;
  return () => {
    isMountedRef.current = false;
    abortControllerRef.current?.abort();
  };
}, []);
```

---

### 0-3. [CRITICAL] useRunProgress WebSocket接続リーク `cc:TODO`
**ファイル**: [useRunProgress.ts:59-80](apps/ui/src/hooks/useRunProgress.ts#L59)
**問題**: 同じ runId で複数回呼び出されると、処理中の接続が中途で切断
**修正方針**: connectionState を追加してガード
**工数**: 45分

```typescript
const [connectionState, setConnectionState] = useState<'idle' | 'connecting' | 'connected'>('idle');

const connect = useCallback(() => {
  if (connectionState !== 'idle') return;
  setConnectionState('connecting');
  // ...
}, [runId, connectionState, handleMessage]);
```

---

### 0-4. [CRITICAL] StepArtifactsList 競合状態 `cc:TODO`
**ファイル**: [OutputApprovalTab.tsx:708-720](apps/ui/src/components/tabs/OutputApprovalTab.tsx#L708)
**問題**: 古いリクエストの結果が新しい選択を上書きする可能性
**修正方針**: request ID を追跡して stale response を無視
**工数**: 30分

```typescript
const loadContent = async (artifact: ArtifactRef) => {
  const requestId = artifact.id;
  setSelectedArtifact(artifact);

  const data = await api.artifacts.download(runId, artifact.id);
  if (selectedArtifactRef.current?.id === requestId) {
    setContent(data);
  }
};
```

---

### 0-5. [CRITICAL] WebSocket 接続状態遷移 - CONNECTING状態未チェック `cc:TODO`
**ファイル**: [websocket.ts:46-63](apps/ui/src/lib/websocket.ts#L46)
**問題**: CONNECTING 状態はチェックされず、複数接続が同時進行
**修正方針**: CONNECTING 状態もチェック
**工数**: 15分

```typescript
connect(): void {
  if (this.ws?.readyState === WebSocket.OPEN ||
      this.ws?.readyState === WebSocket.CONNECTING) {
    return;
  }
}
```

---

## 🟠 フェーズ1: HIGH ✅ 完了

### 1-1. [HIGH] useRunProgress.ts - WebSocket 接続管理の競合 `cc:TODO`
**ファイル**: [useRunProgress.ts:87-104](apps/ui/src/hooks/useRunProgress.ts#L87)
**問題**: 複数の runId 変更が急速に発生した場合、接続状態が混在
**修正方針**: connect() 呼び出し前に既存接続を必ず閉じる
**工数**: 45分

---

### 1-2. [HIGH] useRuns.ts - ページネーション状態同期漏れ `cc:TODO`
**ファイル**: [useRuns.ts:37-60](apps/ui/src/hooks/useRuns.ts#L37)
**問題**: page/status 変更時の同期ロジックが不足
**修正方針**: page 変更時に既存データをクリア
**工数**: 30分

---

### 1-3. [HIGH] useArtifactContent - runId 変更時のレースコンディション `cc:TODO`
**ファイル**: [useArtifact.ts:59-95](apps/ui/src/hooks/useArtifact.ts#L59)
**問題**: 古い runId の結果が新しい runId の content を上書き
**修正方針**: AbortController でキャンセル
**工数**: 30分

---

### 1-4. [HIGH] StepDetailDrawer.tsx - タイマークリーンアップ漏れ `cc:TODO`
**ファイル**: [StepDetailDrawer.tsx:170-174](apps/ui/src/components/workflow/StepDetailDrawer.tsx#L170)
**問題**: setTimeout の ID が未保存、アンマウント後の state 更新
**修正方針**: useRef でタイマー ID を保存、cleanup で clearTimeout
**工数**: 15分

```typescript
const timerRef = useRef<NodeJS.Timeout | null>(null);

const copyToClipboard = (text: string, id: string) => {
  if (timerRef.current) clearTimeout(timerRef.current);
  setCopiedId(id);
  timerRef.current = setTimeout(() => setCopiedId(null), 2000);
};

useEffect(() => {
  return () => {
    if (timerRef.current) clearTimeout(timerRef.current);
  };
}, []);
```

---

### 1-5. [HIGH] OutputApprovalTab infinite loop risk `cc:TODO`
**ファイル**: [OutputApprovalTab.tsx:140-144](apps/ui/src/components/tabs/OutputApprovalTab.tsx#L140)
**問題**: `selectedRunId` が依存配列に含まれ、無限ループの可能性
**修正方針**: `selectedRunId` を依存配列から除外
**工数**: 10分

```typescript
useEffect(() => {
  if (!selectedRunId && filteredRuns.length > 0) {
    setSelectedRunId(filteredRuns[0].id);
  }
}, [filteredRuns]);  // selectedRunId を除外
```

---

### 1-6. [HIGH] RunDetailPanel fetchArtifacts duplicate fetch `cc:TODO`
**ファイル**: [OutputApprovalTab.tsx:319-324](apps/ui/src/components/tabs/OutputApprovalTab.tsx#L319)
**問題**: `fetchArtifacts` が依存配列に含まれ、重複フェッチ
**修正方針**: `fetchArtifacts` を依存配列から除外
**工数**: 15分

---

### 1-7. [HIGH] OutputApprovalTab 未処理Promise `cc:TODO`
**ファイル**: [OutputApprovalTab.tsx:291-323](apps/ui/src/components/tabs/OutputApprovalTab.tsx#L291)
**問題**: Promise が await されず、失敗が無視される
**修正方針**: async/await + try-catch
**工数**: 30分

```typescript
onEvent: async (event) => {
  try {
    if (event.type === "step_completed" || ...) {
      await fetch();
    }
  } catch (err) {
    console.error("Failed to handle event:", err);
  }
},
```

---

### 1-8. [HIGH] useRun ポーリング依存配列の循環参照修正 `cc:TODO`
**ファイル**: [useRun.ts:92-118](apps/ui/src/hooks/useRun.ts#L92)
**問題**: `startPolling` の依存配列に `stopPolling` が含まれ、循環参照
**修正方針**: 直接 interval をクリア
**工数**: 15分

---

## 🟡 フェーズ2: MEDIUM ✅ 完了

### 2-1. [MEDIUM] ImageGenerationWizard race condition `cc:TODO`
**ファイル**: [ImageGenerationWizard.tsx:114-162](apps/ui/src/components/imageGeneration/ImageGenerationWizard.tsx#L114)
**問題**: runId 変更時に前の runId の処理結果で上書きされるリスク
**修正方針**: AbortController でキャンセル
**工数**: 35分

---

### 2-2. [MEDIUM] RunDetailPage handleOpenPreview stale closure `cc:TODO`
**ファイル**: [page.tsx:134-148](apps/ui/src/app/runs/[id]/page.tsx#L134)
**問題**: 連続クリックで複数の fetch リクエストが並行実行
**修正方針**: `previewArticle` を依存配列から除外
**工数**: 15分

---

### 2-3. [MEDIUM] useArtifactContent 無条件フェッチ `cc:TODO`
**ファイル**: [useArtifact.ts:85-87](apps/ui/src/hooks/useArtifact.ts#L85)
**問題**: runId 変更時に不要な二回フェッチ
**修正方針**: artifactId 有無をチェック
**工数**: 10分

---

### 2-4. [MEDIUM] WorkflowPattern1_N8nStyle 非決定的 UI `cc:TODO`
**ファイル**: [WorkflowPattern1_N8nStyle.tsx:162](apps/ui/src/components/workflow/WorkflowPattern1_N8nStyle.tsx#L162)
**問題**: 秒ごとに表示が変わる（UX 不安定、テスト不安定）
**修正方針**: step 開始時刻から経過時間を計算
**工数**: 25分

---

### 2-5. [MEDIUM] RunList fetchRuns 依存配列の曖昧性 `cc:TODO`
**ファイル**: [RunList.tsx:55-58](apps/ui/src/components/runs/RunList.tsx#L55)
**問題**: `page` 変更時にフェッチされない
**修正方針**: `page, limit` を依存配列に追加
**工数**: 15分

---

### 2-6. [MEDIUM] ImageGenerationWizard handleImagesReview phase ロジック曖昧 `cc:TODO`
**ファイル**: [ImageGenerationWizard.tsx:275-318](apps/ui/src/components/imageGeneration/ImageGenerationWizard.tsx#L275)
**問題**: `hasRetries` の判定が不明確
**修正方針**: API 側の `result.has_retries` を使用
**工数**: 20分

---

### 2-7. [MEDIUM] useRun.ts stale closure問題 `cc:TODO`
**ファイル**: [useRun.ts:114-121](apps/ui/src/hooks/useRun.ts#L114)
**問題**: `stopOnComplete` 変更時、既存 interval は古い値を使用
**修正方針**: `stopOnComplete` を ref で管理
**工数**: 25分

---

### 2-8. [MEDIUM] api.ts has_more計算ロジック `cc:TODO`
**ファイル**: [api.ts:131-146](apps/ui/src/lib/api.ts#L131)
**問題**: `runs.length === 0` の場合、実際には more items 存在
**修正方針**: `has_more = (offset + runs.length) < total` に簡潔化
**工数**: 10分

---

### 2-9. [MEDIUM] useRuns ページング競合 `cc:TODO`
**ファイル**: [useRuns.ts:37-54](apps/ui/src/hooks/useRuns.ts#L37)
**問題**: 高速ページ切り替えで古い結果が新しい結果を上書き
**修正方針**: AbortController でキャンセル機能を追加
**工数**: 30分

---

### 2-10. [MEDIUM] Phase11D_Review の retryInputs リセット不足 `cc:TODO`
**ファイル**: [Phase11D_Review.tsx:40-52](apps/ui/src/components/imageGeneration/phases/Phase11D_Review.tsx#L40)
**問題**: images プロップが変更されても retryInputs がリセットされない
**修正方針**: useEffect で images 変更時にリセット
**工数**: 10分

```typescript
useEffect(() => {
  setRetryInputs(new Map());
}, [images]);
```

---

## 🟢 フェーズ3: LOW ✅ 完了

### 3-1. [LOW] StepDetailDrawer.tsx Sub-step シミュレーション不正確 `cc:TODO`
**ファイル**: [StepDetailDrawer.tsx:152-168](apps/ui/src/components/workflow/StepDetailDrawer.tsx#L152)
**問題**: Date.now() 直接使用で毎フレーム異なる値
**修正方針**: started_at から経過時間を計算
**工数**: 20分

---

### 3-2. [LOW] RunCreateForm.tsx localStorage エラーハンドリング `cc:TODO`
**ファイル**: [RunCreateForm.tsx:37-46](apps/ui/src/components/runs/RunCreateForm.tsx#L37)
**問題**: JSON パース失敗時にユーザー通知なし
**修正方針**: toast またはエラーメッセージ表示
**工数**: 15分

---

### 3-3. [LOW] WorkflowGraph.tsx - useMemo と useEffect の重複計算 `cc:TODO`
**ファイル**: [WorkflowGraph.tsx:620-635](apps/ui/src/components/workflow/WorkflowGraph.tsx#L620)
**問題**: useMemo と useEffect で同じ計算
**修正方針**: どちらかに統一
**工数**: 20分

---

### 3-4. [LOW] ArtifactViewer nullチェック漏れ `cc:TODO`
**ファイル**: [ArtifactViewer.tsx:259-266](apps/ui/src/components/artifacts/ArtifactViewer.tsx#L259)
**問題**: `artifact.ref_path` が null でエラー
**修正方針**: `(artifact.ref_path || "").split("/").pop()`
**工数**: 10分

---

### 3-5. [LOW] artifactsByStep undefined キー `cc:TODO`
**ファイル**: [OutputApprovalTab.tsx:405-414](apps/ui/src/components/tabs/OutputApprovalTab.tsx#L405)
**問題**: 両方 undefined で undefined キーにグループ化
**修正方針**: `stepKey = ... || "unknown"`
**工数**: 10分

---

### 3-6. [LOW] Step name 表記ゆれの型安全化 `cc:TODO`
**ファイル**: 複数（types.ts, api.ts, useRun.ts）
**問題**: `step6_5` と `step6.5` の表記ゆれが散在
**修正方針**: 共通の正規化関数を作成
**工数**: 30分

```typescript
export function normalizeStepName(step: string): StepNameInternal {
  return step.replace(/\./g, "_") as StepNameInternal;
}

export function displayStepName(step: string): StepNameDisplay {
  return step.replace(/_/g, ".") as StepNameDisplay;
}
```

---

## 🔵 フェーズ4: テスト追加 `cc:TODO` (未着手)

### 4-1. 修正箇所のユニットテスト追加 `cc:TODO`
- [ ] useRun ポーリング cleanup テスト
- [ ] WebSocket 接続管理テスト
- [ ] React hooks 依存配列テスト
- [ ] ページネーション状態同期テスト

### 4-2. smoke テスト実行 `cc:TODO`
```bash
npm run lint --prefix apps/ui
npx tsc --noEmit --project apps/ui/tsconfig.json
```

---

## 完了基準

- [ ] 全フェーズの修正完了
- [ ] TypeScript エラーがない
- [ ] lint エラーがない
- [ ] 目視動作確認完了

---

## 次のアクション

- 「`/work Plans3.md`」でフェーズ0から実装開始
