# Frontend UI 仕様

## 技術スタック

- Next.js (React)
- WebSocket（リアルタイム進捗）

## 画面一覧

### 1. Runs一覧

| 項目 | 内容 |
|------|------|
| 状態 | pending / running / waiting_approval / completed / failed |
| 最終更新 | timestamp |
| 要約 | 入力キーワード、現在工程 |
| 設定サマリ | 選択モデル、オプション |

### 2. Run作成

- **工程-1入力UI**（スプレッドシート代替）
- **実行オプション切替UI**
  - プラットフォーム/モデル選択
  - 重要オプション（grounding等）
  - ツール設定
  - repair/retry上限

### 3. Run詳細

- Stepタイムライン（attempt含む）
- Validation Report閲覧
- Artifacts閲覧
- Logs/Events（全閲覧可能）
- **承認ボタン**（Approve/Reject）

### 4. Retry

- Step単位で再実行
- 同一条件のみ（フォールバック禁止）

### 5. 部分再実行（Resume）

- 失敗した run を特定工程から再開
- 「ここから再実行」ボタンを各工程に配置
- 新規 run_id が生成される（元 run との関連は保持）

#### UI仕様

```
[Run詳細画面]
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

#### 再実行確認ダイアログ

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

### 6. Clone Run

- 条件変更は別runとして明示作成

### 7. Previewリンク

- 生成HTMLのビルド成果への遷移

---

## ワークフロービュー（Canvas）

- 工程をノード、依存関係をエッジとして可視化
- 並列工程（3A/3B/3C）は同一フェーズ内の並列として表示
- 状態を色/バッジで表現

## 工程詳細パネル

- 入出力参照（`output_path`/`output_digest`/`summary`）
- 生成物（JSON/MD/HTML）のプレビュー
- ダウンロード導線
- 失敗時は `error_message` / `retry_count` を表示

---

## 承認フロー UI

- 「承認待ち」状態が明確にわかる表示
- 承認/却下ボタン
- 却下時は理由入力必須
- 監査ログ連携

---

## リアルタイム更新

WebSocket `/ws/runs/{id}` で進捗を受信：

```typescript
interface ProgressEvent {
  type: "step_started" | "step_completed" | "error";
  step: string;
  progress: number;  // 0-100
  message: string;
  timestamp: string;
}
```

---

## セキュリティ

- 表示データは tenant スコープ前提
- URL直打ちでのID差し替えを防ぐ
- presigned URL は有効期限に注意
