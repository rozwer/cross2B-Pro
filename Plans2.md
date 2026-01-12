# 工程3承認画面 成果物自動読み込み修正計画

> **作成日**: 2026-01-12
> **目的**: 承認待ち状態で成果物が自動的に読み込まれるように修正

---

## 背景・問題

現在、工程3（3A/3B/3C）が完了して承認待ち状態になっても、成果物が自動的に読み込まれない。
ユーザーが「成果物を確認して承認」ボタンをクリックするまで、成果物が表示されない。

### 根本原因

1. **WebSocket イベント監視の不足**: `OutputApprovalTab.tsx` で `approval_requested` イベントが監視対象に含まれていない
2. **成果物フェッチのトリガー不足**: 承認待ち状態になっても `fetchArtifacts()` が呼ばれない
3. **ApprovalDialog の依存関係**: `approvalArtifacts.length` のみを監視しているため、配列内容の変更を検知できない

---

## 影響範囲

| ファイル | 変更内容 |
|---------|---------|
| `apps/ui/src/components/tabs/OutputApprovalTab.tsx` | WebSocket イベント監視に `approval_requested` を追加、成果物自動フェッチ |
| `apps/ui/src/components/common/ApprovalDialog.tsx` | useEffect 依存関係の修正 |
| `apps/ui/src/lib/types.ts` | ProgressEventType に `approval_requested` 追加（必要に応じて） |

---

## フェーズ 1: OutputApprovalTab.tsx の修正 `cc:完了`

### 1.1 WebSocket イベント監視の拡張

- [ ] `onEvent` コールバックに `approval_requested` イベントを追加
- [ ] `approval_requested` 受信時に `fetchArtifacts()` を呼び出す

**修正前 (L292-302)**:
```typescript
const { events, wsStatus } = useRunProgress(runId, {
  onEvent: (event) => {
    if (
      event.type === "step_completed" ||
      event.type === "step_failed" ||
      event.type === "run_completed"
    ) {
      fetch();
    }
  },
});
```

**修正後**:
```typescript
const { events, wsStatus } = useRunProgress(runId, {
  onEvent: (event) => {
    if (
      event.type === "step_completed" ||
      event.type === "step_failed" ||
      event.type === "approval_requested" ||
      event.type === "run_completed"
    ) {
      fetch();
    }
    // 承認待ち状態になったら成果物も再フェッチ
    if (event.type === "approval_requested") {
      fetchArtifacts();
    }
  },
});
```

### 1.2 run.status 変更時の自動フェッチ

- [ ] `run.status` が `waiting_approval` に変わった時に成果物をフェッチする useEffect を追加

```typescript
useEffect(() => {
  if (run?.status === "waiting_approval") {
    fetchArtifacts();
  }
}, [run?.status, fetchArtifacts]);
```

---

## フェーズ 2: ApprovalDialog.tsx の修正 `cc:完了`

### 2.1 useEffect 依存関係の修正

- [ ] `approvalArtifacts.length` ではなく `approvalArtifacts` 全体を依存配列に含める
- [ ] eslint-disable コメントを削除

**修正前 (L100-105)**:
```typescript
useEffect(() => {
  if (isOpen && approvalArtifacts.length > 0 && !selectedArtifact) {
    loadContent(approvalArtifacts[0]);
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [isOpen, approvalArtifacts.length]);
```

**修正後**:
```typescript
useEffect(() => {
  if (isOpen && approvalArtifacts.length > 0 && !selectedArtifact) {
    loadContent(approvalArtifacts[0]);
  }
}, [isOpen, approvalArtifacts, selectedArtifact, loadContent]);
```

---

## フェーズ 3: 型定義の確認 `cc:完了`

### 3.1 ProgressEventType の確認

- [ ] `apps/ui/src/lib/types.ts` で `approval_requested` が `ProgressEventType` に含まれているか確認
- [ ] 含まれていない場合は追加

```typescript
export type ProgressEventType =
  | "step_started"
  | "step_completed"
  | "step_failed"
  | "run_started"
  | "run_completed"
  | "run_failed"
  | "approval_requested"  // ← 追加（必要に応じて）
  | ...
```

---

## フェーズ 4: テスト・確認 `cc:完了`

- [ ] TypeScript 型チェック (`npx tsc --noEmit`)
- [ ] lint チェック (`npm run lint`)
- [ ] ブラウザで工程3実行 → 承認待ち状態を確認
- [ ] 承認ダイアログを開かずに成果物が表示されることを確認
- [ ] 承認ダイアログ内で成果物が正しく表示されることを確認

---

## 完了基準

- [ ] 工程3完了時に成果物が自動的に読み込まれる
- [ ] 承認ダイアログを開く前から成果物プレビューが表示される
- [ ] TypeScript エラーがない
- [ ] lint エラーがない
- [ ] WebSocket 接続が正常に動作する

---

## 技術詳細

### 関連フック

| フック | ファイル | 役割 |
|-------|---------|------|
| `useRunProgress` | `hooks/useRunProgress.ts` | WebSocket イベント監視 |
| `useArtifacts` | `hooks/useArtifact.ts` | 成果物フェッチ |
| `useRun` | `hooks/useRun.ts` | Run データフェッチ |

### WebSocket イベントフロー

```
Backend (Temporal Activity)
    ↓ approval_requested イベント発行
WebSocket (apps/api/routers/websocket.py)
    ↓ broadcast_run_update
Frontend (useRunProgress)
    ↓ onEvent コールバック
OutputApprovalTab
    ↓ fetch() + fetchArtifacts()
UI 更新
```

---

## 次のアクション

- 「`/work`」で実装を開始
- または「フェーズ1から始めて」
