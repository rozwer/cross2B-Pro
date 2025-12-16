---
description: 実装ルール統合版（API/Temporal/LangGraph/Storage/Security）
---

# 実装ルール

> **CLAUDE.md** と **ROADMAP.md** を最優先とし、詳細はこのファイルを参照。

## 1. API 契約

### エンドポイント

| メソッド | パス | 用途 |
|----------|------|------|
| POST | `/api/runs` | ワークフロー開始 |
| GET | `/api/runs/{id}` | 状態取得 |
| POST | `/api/runs/{id}/approve` | 承認 |
| POST | `/api/runs/{id}/reject` | 却下 |
| POST | `/api/runs/{id}/retry/{step}` | 工程再実行 |
| DELETE | `/api/runs/{id}` | キャンセル |
| GET | `/api/runs/{id}/files` | 生成物一覧 |
| GET | `/api/runs/{id}/files/{step}` | 工程別出力取得 |
| WS | `/ws/runs/{id}` | 進捗ストリーム |

### 実装ルール

- `tenant_id` は認証から確定し、越境参照を防ぐ
- 承認/却下は Temporal に signal を送る（Workflow自身は副作用しない）
- 監査ログ必須：start/approve/reject/retry/cancel/download/delete

---

## 2. Temporal + LangGraph

### Temporal（Workflow）側

- **決定性を守る**：外部I/Oや時刻依存は避け、必要なら Activity に寄せる
- 工程3（3A/3B/3C）後は **signal 待機** で pause し、approve/reject で分岐
- 並列工程（3A/3B/3C）は Temporal の並列実行で行い、失敗分のみ再試行

### Activity 側

- 副作用（LLM/外部API/DB/Storage）は Activity に閉じ込める
- Activity から LangGraph を呼び出して工程ロジックを実装
- LangGraph state は最小化し、大きい出力は storage に保存

### 冪等性（必須）

```python
# 同一入力 → 同一出力
if existing_output := storage.get(f"{tenant}/{run}/{step}/output.json"):
    return existing_output  # 再計算しない
```

---

## 3. 成果物（Storage）

### 契約フィールド

| フィールド | 説明 |
|------------|------|
| `output_path` | storage上のパス（工程別・run別・tenant別） |
| `output_digest` | 出力内容の sha256 |
| `summary` | UI/ログ用の短い要約 |
| `metrics` | token usage / 文字数 / 主要メタ情報 |

### パス規約

```
storage/{tenant_id}/{run_id}/{step}/output.json
storage/{tenant_id}/{run_id}/{step}/artifacts/
```

### 禁止事項

- Temporal履歴やLangGraph stateに大きいJSON/本文を持たない
- 必ず `path/digest` 参照にする

---

## 4. セキュリティ / マルチテナント

### 越境防止

- すべてのデータアクセス（DB/Storage/WS）は `tenant_id` でスコープ
- `tenant_id` は認証から確定し、入力値・URLパラメータを信用しない

### 監査ログ

必須フィールド：
- `actor`: 実行者ID
- `tenant_id`: テナントID
- `run_id`: ワークフロー実行ID
- `step`: 工程名
- `input_digest` / `output_digest`
- `timestamp`

### 秘密情報

- APIキー等は暗号化して保存
- 復号は最小権限で行う
- 平文保存・平文ログは禁止

---

## 5. プロンプト管理

### 基本方針

- プロンプトは DB（`prompts` テーブル）で管理
- `step + version` で固定
- run は使用した `prompt_versions` を保存し、再現性を担保

### 変数とレンダリング

- 変数は `variables`（JSON）で宣言
- レンダラが不足変数を検知して fail fast
- 変数の追加/変更は version を上げる（既存runの再現性を壊さない）

---

## 6. フロントエンド（レビューUI）

### ワークフロービュー

- 工程をノード、依存関係をエッジとして可視化（DAG）
- run/工程の状態を色/バッジで表現
- 並列工程（3A/3B/3C）は同一フェーズ内の並列として表示

### 工程詳細パネル

- 入出力参照（`output_path`/`output_digest`/`summary`）を表示
- 生成物（JSON/MD/HTML）のプレビューとダウンロード
- 失敗時は `error_message` / `retry_count` を表示

### 承認フロー

- 「承認待ち」状態が明確にわかる表示
- 承認/却下ボタンで API を叩き、Workflow を再開
- 却下時は理由入力と監査ログ連携を必須化

### セキュリティ

- 画面に表示するデータは tenant スコープ前提
- URL直打ちでのID差し替えを防ぐ
- presigned URL は有効期限/権限に注意
