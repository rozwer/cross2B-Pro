# Session 8: Frontend UI

## Phase 5（Phase 4完了後）

---

## 作業開始手順

```bash
cd /home/rozwer/案件
git fetch origin
git pull origin develop

# Phase 4 のマージ確認
git log --oneline develop | head -10
# feat/langgraph がマージ済みであること

# Worktree作成
TOPIC="frontend"
mkdir -p .worktrees
git worktree add -b "feat/$TOPIC" ".worktrees/$TOPIC" develop

# 作業ディレクトリへ移動
cd ".worktrees/$TOPIC"
```

---

## 前提確認

Phase 1-4 が完了済みであること:

```bash
ls apps/api/
ls apps/worker/
```

---

## 実装指示

あなたはSEO記事自動生成システムのフロントエンド実装者です。

### 実装対象

社内エンジニア向けUI（全情報閲覧可能）

### 前提

- 仕様書/ROADMAP.md の Step 7 を参照
- 仕様書/frontend/ui.md を参照

### 技術スタック

- Next.js 14+ (App Router)
- React 18+
- TypeScript
- WebSocket（リアルタイム進捗）
- Tailwind CSS

### 成果物

```
apps/ui/
├── package.json
├── tsconfig.json
├── next.config.js
├── tailwind.config.js
├── app/                     # App Router
│   ├── layout.tsx
│   ├── page.tsx             # リダイレクト
│   ├── runs/
│   │   ├── page.tsx         # 1. Runs一覧
│   │   ├── new/
│   │   │   └── page.tsx     # 2. Run作成
│   │   └── [id]/
│   │       ├── page.tsx     # 3. Run詳細
│   │       └── preview/
│   │           └── page.tsx # 7. Previewリンク
│   └── api/                 # API Routes (BFF)
│       └── [...path]/
│           └── route.ts
├── components/
│   ├── runs/
│   │   ├── RunList.tsx
│   │   ├── RunCard.tsx
│   │   ├── RunStatusBadge.tsx
│   │   └── RunCreateForm.tsx
│   ├── steps/
│   │   ├── StepTimeline.tsx
│   │   ├── StepNode.tsx
│   │   └── StepDetailPanel.tsx
│   ├── workflow/
│   │   ├── WorkflowCanvas.tsx    # ノード・エッジ可視化
│   │   └── WorkflowMinimap.tsx
│   ├── approval/
│   │   ├── ApprovalDialog.tsx
│   │   └── ResumeConfirmDialog.tsx
│   ├── artifacts/
│   │   ├── ArtifactViewer.tsx
│   │   ├── JsonViewer.tsx
│   │   ├── MarkdownViewer.tsx
│   │   └── HtmlPreview.tsx
│   ├── validation/
│   │   └── ValidationReportViewer.tsx
│   └── common/
│       ├── Loading.tsx
│       ├── ErrorBoundary.tsx
│       └── ConfirmDialog.tsx
├── hooks/
│   ├── useRunProgress.ts     # WebSocket進捗
│   ├── useRuns.ts
│   ├── useRun.ts
│   └── useArtifact.ts
├── lib/
│   ├── api.ts               # Backend API クライアント
│   ├── websocket.ts         # WebSocket接続
│   └── types.ts             # 型定義
└── __tests__/
```

---

## 画面仕様

### 1. Runs一覧 (`/runs`)

| 項目       | 内容                                                      |
| ---------- | --------------------------------------------------------- |
| 状態       | pending / running / waiting_approval / completed / failed |
| 最終更新   | timestamp                                                 |
| 要約       | 入力キーワード、現在工程                                  |
| 設定サマリ | 選択モデル、オプション                                    |

```tsx
// components/runs/RunCard.tsx
interface RunCardProps {
  run: {
    id: string;
    status: RunStatus;
    current_step: string;
    keyword: string;
    model_config: ModelConfig;
    updated_at: string;
  };
}
```

### 2. Run作成 (`/runs/new`)

- **工程-1入力UI**（スプレッドシート代替）
  - キーワード入力
  - ターゲット設定
  - 競合URL指定
- **実行オプション切替UI**
  - プラットフォーム/モデル選択（Gemini/Claude/OpenAI）
  - 重要オプション（grounding等）
  - repair/retry上限

### 3. Run詳細 (`/runs/[id]`)

```
┌─────────────────────────────────────────────┐
│ Step Timeline                               │
│                                             │
│ ● step0 [completed] ✓                       │
│ ● step1 [completed] ✓                       │
│ ● step2 [completed] ✓                       │
│ ● step3a [completed] ✓                      │
│ ● step3b [failed] ✗  [リトライ] [ここから再実行] │
│ ○ step3c [pending]                          │
│ ○ step4 [pending]                           │
└─────────────────────────────────────────────┘
```

- Stepタイムライン（attempt含む）
- Validation Report閲覧
- Artifacts閲覧
- Logs/Events（全閲覧可能）
- **承認ボタン**（Approve/Reject）
- 各工程に「リトライ」「ここから再実行」ボタン

### 4. 承認ダイアログ

```tsx
// components/approval/ApprovalDialog.tsx
interface ApprovalDialogProps {
  runId: string;
  onApprove: () => void;
  onReject: (reason: string) => void;
}
```

却下時は理由入力必須。

### 5. 部分再実行確認ダイアログ

```
┌─────────────────────────────────────────────┐
│ 部分再実行の確認                             │
│                                             │
│ step3b から再実行します。                    │
│                                             │
│ ・新しい run が作成されます                  │
│ ・step0〜step3a の成果物は引き継がれます     │
│ ・元の run は「再実行済み」としてマークされます│
│                                             │
│              [キャンセル] [再実行開始]        │
└─────────────────────────────────────────────┘
```

---

## WebSocket

### useRunProgress.ts

```typescript
interface ProgressEvent {
  type: "step_started" | "step_completed" | "step_failed" | "error";
  step: string;
  progress: number;  // 0-100
  message: string;
  timestamp: string;
}

export function useRunProgress(runId: string) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [status, setStatus] = useState<RunStatus>("pending");

  useEffect(() => {
    const ws = new WebSocket(
      `${process.env.NEXT_PUBLIC_WS_URL}/ws/runs/${runId}`
    );

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as ProgressEvent;
      setEvents((prev) => [...prev, data]);
      // ステータス更新ロジック
    };

    return () => ws.close();
  }, [runId]);

  return { events, status };
}
```

---

## API クライアント

### lib/api.ts

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL;

export const api = {
  runs: {
    list: () => fetch(`${API_BASE}/api/runs`).then(r => r.json()),
    get: (id: string) => fetch(`${API_BASE}/api/runs/${id}`).then(r => r.json()),
    create: (data: CreateRunInput) =>
      fetch(`${API_BASE}/api/runs`, {
        method: "POST",
        body: JSON.stringify(data),
      }).then(r => r.json()),
    approve: (id: string) =>
      fetch(`${API_BASE}/api/runs/${id}/approve`, { method: "POST" }),
    reject: (id: string, reason: string) =>
      fetch(`${API_BASE}/api/runs/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
    retry: (id: string, step: string) =>
      fetch(`${API_BASE}/api/runs/${id}/retry/${step}`, { method: "POST" }),
    resume: (id: string, step: string) =>
      fetch(`${API_BASE}/api/runs/${id}/resume/${step}`, { method: "POST" }),
  },
  artifacts: {
    list: (runId: string) =>
      fetch(`${API_BASE}/api/runs/${runId}/files`).then(r => r.json()),
    get: (runId: string, step: string) =>
      fetch(`${API_BASE}/api/runs/${runId}/files/${step}`).then(r => r.json()),
  },
};
```

---

## セキュリティ

- 表示データは tenant スコープ前提
- URL直打ちでのID差し替えを防ぐ（API側で検証）
- presigned URL は有効期限に注意

---

## DoD（完了条件）

- [ ] UI から Run 作成 → 承認 → step retry → Preview 参照が一通りできる
- [ ] モデル/ツールの自動切替や黙った回復が存在しない
- [ ] 全画面でエラー状態が明示される
- [ ] レスポンシブ対応（デスクトップ優先）
- [ ] WebSocket でリアルタイム更新が動作
- [ ] TypeScript 型チェック通過
- [ ] ESLint 通過

### 禁止事項

- tenant スコープ外のデータ表示
- URL直打ちでのID差し替えによる越境
- エラー状態の非表示

---

## 完了後

```bash
# 依存インストール
cd apps/ui
npm install

# 型チェック
npm run type-check

# Lint
npm run lint

# ビルド確認
npm run build

# コミット
git add .
git commit -m "feat(ui): フロントエンドUI実装"

# push & PR作成
git push -u origin feat/frontend
gh pr create --base develop --title "feat(ui): フロントエンドUI" --body "## 概要
- Runs一覧/作成/詳細
- StepTimeline
- 承認/却下/リトライ/部分再実行
- WebSocketリアルタイム更新
- Artifacts閲覧

## 依存
- Phase 1-4 完了済み

## テスト
- [x] TypeScript型チェック通過
- [x] ESLint通過
- [x] ビルド成功"
```
