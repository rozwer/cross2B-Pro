# Backend API 仕様

## エンドポイント

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
| GET | `/api/runs/{id}/preview` | HTMLプレビュー |

### WebSocket

| パス | 用途 |
|------|------|
| `/ws/runs/{id}` | 進捗ストリーム |

## 認証・認可

- JWT認証（`tenant_id` は認証から確定）
- 越境参照禁止（DB/Storage/WS すべて tenant スコープ）

### ロール

| ロール | 説明 |
|--------|------|
| admin | 全操作可能 |
| operator | 実行・承認・リトライ可能 |
| viewer | 閲覧・DLのみ |

## 監査ログ

必須アクション：
- start / approve / reject / retry / cancel / download / delete

必須フィールド：
- `actor`, `tenant_id`, `run_id`, `step`, `timestamp`

---

## Tools {#tools}

外部ツール（LLM以外の呼び出し）

### 必須ツール

| tool_id | 機能 |
|---------|------|
| `serp_fetch` | SERP取得（上位N件URL） |
| `page_fetch` | ページ取得 + 本文抽出 |
| `primary_collector` | 一次情報収集器 |
| `url_verify` | URL実在確認 |
| `pdf_extract` | PDFテキスト抽出 |

### 拡張ツール

| tool_id | 機能 |
|---------|------|
| `search_volume` | 検索ボリューム取得 |
| `related_keywords` | 関連語取得 |

### 共通設計

- Tool Manifest で `tool_id` 明示呼び出し
- I/O は JSON
- 取得結果は証拠として追跡可能（URL/取得日時/抜粋/ハッシュ）
- エラー分類：`RETRYABLE` / `NON_RETRYABLE` / `VALIDATION_FAIL`
