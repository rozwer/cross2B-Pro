# Frontend層 修正計画（Plans-Frontend.md）

> **作成日**: 2026-01-12
> **対象**: apps/ui/src/ (hooks, components)
> **ステータス**: 計画中
> **並列実行**: Plans-API, Plans-Worker, Plans-LangGraph, Plans-LLM, Plans-DB と競合なし

---

## 概要

| 優先度 | 件数 |
|--------|------|
| CRITICAL | 4件 |
| HIGH | 10件 |
| MEDIUM | 5件 |

---

## 🔴 CRITICAL `cc:完了`

### C-1. useRunProgress: 無限ループリスク
- [x] `cc:完了` connectionStateをuseRefで管理 (**既に修正済み**)
- [x] `cc:完了` useEffect依存配列を`[autoConnect, runId]`のみに修正 (**既に修正済み**)

**ファイル**: `apps/ui/src/hooks/useRunProgress.ts:60-123`
**行番号**: 91（connect）、108-123（useEffect）
**結果**: connectionStateRef を使用、依存配列は `[autoConnect, runId]` のみ

### C-2. useRun: stopOnComplete の stale closure
- [x] `cc:完了` pollingIntervalをuseRef化 (**既に修正済み**)
- [x] `cc:完了` interval resetで古いintervalクリアを確実に (**既に修正済み**)

**ファイル**: `apps/ui/src/hooks/useRun.ts:144-163`
**行番号**: 152-162（startPolling内のsetInterval）
**結果**: stopOnCompleteRef を使用、interval クリア処理も適切

### C-3. Phase11D_Review: reviewsの未リセット
- [x] `cc:完了` useEffectでimages変更時にreviewsも再初期化

**ファイル**: `apps/ui/src/components/imageGeneration/phases/Phase11D_Review.tsx:54-68`
**修正内容**: useEffect で images 変更時に reviews Map を再初期化するように修正

### C-4. Phase11B_Positions: initialPositions同期漏れ
- [x] `cc:完了` useEffectでinitialPositions変更を検出してsetState

**ファイル**: `apps/ui/src/components/imageGeneration/phases/Phase11B_Positions.tsx:40-45`
**修正内容**: useEffect で initialPositions 変更時に positions state を更新するように修正

---

## 🟠 HIGH `cc:完了`

### H-1. ImageGenerationWizard: 状態更新キューイング問題
- [x] `cc:完了` abortControllerで既存リクエストをキャンセル (**既に修正済み**)
- [x] `cc:完了` state updateをbatch処理 (**React 18自動batching対応済み**)

**ファイル**: `apps/ui/src/components/imageGeneration/ImageGenerationWizard.tsx:119-122`
**結果**: abortControllerRef を使用してリクエストキャンセル対応済み

### H-2. WorkflowProgressView: localStorage 同期ズレ
- [x] `cc:完了` useEffect + useStateの分離（hydration対応）

**ファイル**: `apps/ui/src/components/workflow/WorkflowProgressView.tsx:60-72`
**修正内容**: SSR時はdefaultPattern、クライアント側でuseEffect経由でlocalStorageから読み込み

### H-3. ArtifactViewer: useMemo 依存配列問題
- [x] `cc:完了` 検証の結果、現状の実装で正しい (**修正不要**)

**ファイル**: `apps/ui/src/components/artifacts/ArtifactViewer.tsx:88-125`
**結果**: useMemoはartifactsのみを依存としており、参照が変わるのは親で配列が新規生成された時のみで正常

### H-4. useArtifactContent: artifactId 変更時の race condition
- [x] `cc:完了` abortControllerとisMountedRefで対策済み (**既に修正済み**)

**ファイル**: `apps/ui/src/hooks/useArtifact.ts:78-111`
**結果**: abortControllerRef + isMountedRef の二重保護パターンで実装済み

### H-5. RunDetailPage: handleOpenPreview の stale closure
- [x] `cc:完了` 引数で articleNumber を受け取る設計で回避 (**修正不要**)

**ファイル**: `apps/ui/src/app/runs/[id]/page.tsx:134-152`
**結果**: handleOpenPreview(articleNumber?) で引数経由で値を受け取る設計。依存配列除外は意図的でコメントあり

### H-6. RunList: selectedIds の Set 参照透過性
- [x] `cc:完了` 検証の結果、既に new Set() で新しいインスタンス作成済み (**修正不要**)

**ファイル**: `apps/ui/src/components/runs/RunList.tsx:84-91`
**結果**: `const newSelected = new Set(selectedIds)` で毎回新しいSetを作成している

### H-7. Phase11C_Instructions: 位置情報変更時の指示数不同期
- [x] `cc:完了` useEffectでpositions.length変更を検出して再初期化

**ファイル**: `apps/ui/src/components/imageGeneration/phases/Phase11C_Instructions.tsx:35-46`
**修正内容**: positions.length変更時にinstructions配列を再初期化（既存値は保持）

### H-8. ImageGenerationWizard: Phase変更検出ロジック不完全
- [x] `cc:完了` prevPhaseRefはphase変更検出用で正しく使用されている (**修正不要**)

**ファイル**: `apps/ui/src/components/imageGeneration/ImageGenerationWizard.tsx:113-180`
**結果**: prevPhaseRef は fetchPhaseData を phase 変更時のみ実行する制御用。isOpen はダイアログ表示用で役割が異なる

### H-9. onClick内のstale closure
- [x] `cc:完了` propsの?.()呼び出しで直接参照しており問題なし (**修正不要**)

**ファイル**:
- `apps/ui/src/components/workflow/WorkflowPattern1_N8nStyle.tsx:428-431`
- `apps/ui/src/components/workflow/WorkflowPattern5_RadialProgress.tsx:559-561`
**結果**: `onImageGenerate?.()` でpropsの現在値を直接参照。クロージャで古い参照を保持していない

### H-10. onComplete依存関係漏れ
- [x] `cc:完了` handleSettingsSubmit内でonCompleteは使用されていない (**修正不要**)

**ファイル**: `apps/ui/src/components/imageGeneration/ImageGenerationWizard.tsx:189-218`
**結果**: handleSettingsSubmitは設定送信のみ。onCompleteを使うのはhandleSkip, handleFinalizeで、これらには依存配列にonCompleteが含まれている

---

## 🟡 MEDIUM

### M-1. useRuns: page/status 変更時の race condition
- [ ] `cc:TODO` AbortControllerでrace condition対策

**ファイル**: `apps/ui/src/hooks/useRuns.ts:77-84`
**工数**: 25分

### M-2. ErrorBoundary: 再試行ボタンで状態が完全リセットされない
- [ ] `cc:TODO` 再試行時に関連stateをすべてリセット

**ファイル**: `apps/ui/src/components/common/ErrorBoundary.tsx:30-32`
**工数**: 15分

### M-3. ArtifactViewer: expandedSteps が Set のまま参照保持
- [ ] `cc:TODO` 新しいSetインスタンスを作成してsetState

**ファイル**: `apps/ui/src/components/artifacts/ArtifactViewer.tsx:127-135`
**工数**: 15分

### M-4. ImageGenerationWizard: currentPhase prop 変更時の状態不整合
- [ ] `cc:TODO` currentPhase変更時に内部stateをリセット

**ファイル**: `apps/ui/src/components/imageGeneration/ImageGenerationWizard.tsx:93-98`
**工数**: 20分

### M-5. ContentRenderer: decodedContent の再計算不要
- [ ] `cc:TODO` useMemoで依存配列を最適化

**ファイル**: `apps/ui/src/components/artifacts/ArtifactViewer.tsx:379`
**工数**: 15分

---

## 完了基準

- [ ] 全CRITICAL/HIGH項目の修正完了
- [ ] TypeScript エラーがない
- [ ] ESLint エラーがない
- [ ] 関連するユニットテスト追加・通過
