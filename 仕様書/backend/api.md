# Backend API 仕様

## エンドポイント

### Run 操作

| メソッド | パス                           | 用途                           |
| -------- | ------------------------------ | ------------------------------ |
| POST     | `/api/runs`                    | ワークフロー開始               |
| GET      | `/api/runs/{id}`               | 状態取得                       |
| POST     | `/api/runs/{id}/approve`       | 承認                           |
| POST     | `/api/runs/{id}/reject`        | 却下                           |
| POST     | `/api/runs/{id}/retry/{step}`  | 工程再実行                     |
| POST     | `/api/runs/{id}/resume/{step}` | 特定工程から再開（部分再実行） |
| DELETE   | `/api/runs/{id}`               | キャンセル                     |
| GET      | `/api/runs/{id}/files`         | 生成物一覧                     |
| GET      | `/api/runs/{id}/files/{step}`  | 工程別出力取得                 |
| GET      | `/api/runs/{id}/preview`       | HTMLプレビュー                 |

### ヘルスチェック

| メソッド | パス               | 用途                   |
| -------- | ------------------ | ---------------------- |
| GET      | `/health`          | 基本的な生存確認       |
| GET      | `/health/detailed` | 依存サービスの状態詳細 |

#### `/health` レスポンス

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### `/health/detailed` レスポンス

```json
{
  "status": "healthy",
  "services": {
    "postgres_admin": { "status": "healthy", "latency_ms": 5 },
    "postgres_tenant_pool": { "status": "healthy", "active_connections": 3 },
    "minio": { "status": "healthy", "bucket_count": 2 },
    "temporal": {
      "status": "healthy",
      "worker_count": 2,
      "queue_depth": 5
    },
    "llm_providers": {
      "gemini": { "status": "healthy", "last_check": "2024-01-01T00:00:00Z" },
      "claude": { "status": "healthy", "last_check": "2024-01-01T00:00:00Z" },
      "openai": { "status": "degraded", "error": "rate_limited" }
    }
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### コスト集計

| メソッド | パス                  | 用途                     |
| -------- | --------------------- | ------------------------ |
| GET      | `/api/runs/{id}/cost` | run 単位のコスト         |
| GET      | `/api/costs/summary`  | テナント単位のコスト集計 |

### WebSocket

| パス            | 用途           |
| --------------- | -------------- |
| `/ws/runs/{id}` | 進捗ストリーム |

## 認証・認可

- JWT認証（`tenant_id` は認証から確定）
- 越境参照禁止（DB/Storage/WS すべて tenant スコープ）

### ロール

| ロール   | 説明                     |
| -------- | ------------------------ |
| admin    | 全操作可能               |
| operator | 実行・承認・リトライ可能 |
| viewer   | 閲覧・DLのみ             |

---

## Rate Limiting

### テナント単位の制限

| 項目             | デフォルト値 | 説明                 |
| ---------------- | ------------ | -------------------- |
| API リクエスト   | 100 req/min  | 全エンドポイント合計 |
| 同時実行 run 数  | 3            | running 状態の run   |
| 1日の run 作成数 | 50           | 暴走防止             |

### LLM API スロットリング

| 項目   | デフォルト値 | 説明                     |
| ------ | ------------ | ------------------------ |
| Gemini | 60 req/min   | プロバイダ側の制限に準拠 |
| Claude | 40 req/min   | プロバイダ側の制限に準拠 |
| OpenAI | 60 req/min   | プロバイダ側の制限に準拠 |

### レスポンス

制限超過時は `429 Too Many Requests` を返す：

```json
{
  "error": "rate_limit_exceeded",
  "limit_type": "concurrent_runs",
  "retry_after_seconds": 60
}
```

## 監査ログ

必須アクション：

- start / approve / reject / retry / cancel / download / delete

必須フィールド：

- `actor`, `tenant_id`, `run_id`, `step`, `timestamp`

---

## Tools {#tools}

外部ツール（LLM以外の呼び出し）

### 必須ツール

| tool_id             | 機能                   |
| ------------------- | ---------------------- |
| `serp_fetch`        | SERP取得（上位N件URL） |
| `page_fetch`        | ページ取得 + 本文抽出  |
| `primary_collector` | 一次情報収集器         |
| `url_verify`        | URL実在確認            |
| `pdf_extract`       | PDFテキスト抽出        |

### 拡張ツール

| tool_id            | 機能               |
| ------------------ | ------------------ |
| `search_volume`    | 検索ボリューム取得 |
| `related_keywords` | 関連語取得         |

### 共通設計

- Tool Manifest で `tool_id` 明示呼び出し
- I/O は JSON
- 取得結果は証拠として追跡可能（URL/取得日時/抜粋/ハッシュ）
- エラー分類：`RETRYABLE` / `NON_RETRYABLE` / `VALIDATION_FAIL`
