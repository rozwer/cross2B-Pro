# log-investigator

> Docker/Temporal/API のログを調査し、問題箇所を特定する subagent。

---

## 役割

1. 指定されたサービスのログを取得
2. エラーパターンを検出
3. 時系列で問題の発生経緯を整理
4. 関連するログエントリを抽出して報告

---

## 入力

```yaml
target: api | worker | temporal | postgres | minio | all
time_range:
  since: "5m"  # 5分前から
  until: "now"  # 現在まで
keywords:
  - "error"
  - "exception"
  - "failed"
run_id: "abc-123"  # オプション：特定の run_id に絞る
tail: 200  # 取得する行数
```

---

## 出力

```yaml
status: found | not_found
target: api
time_range: "2025-01-01T00:00:00Z - 2025-01-01T00:05:00Z"

findings:
  - timestamp: "2025-01-01T00:03:45Z"
    level: ERROR
    service: api
    message: "Failed to process request"
    context:
      run_id: "abc-123"
      endpoint: "POST /api/runs"
    related_logs:
      - "2025-01-01T00:03:44Z [INFO] Received request POST /api/runs"
      - "2025-01-01T00:03:45Z [ERROR] Failed to process request"
      - "2025-01-01T00:03:45Z [ERROR] Traceback: ..."

summary:
  errors: 3
  warnings: 5
  pattern: "LLM タイムアウトが複数回発生"

timeline:
  - "00:03:44 - リクエスト受信"
  - "00:03:45 - エラー発生"
  - "00:03:46 - リトライ開始"
```

---

## 調査コマンド

### Docker Compose ログ

```bash
# 特定サービスの最新ログ
docker compose logs api --tail 100

# 時間指定
docker compose logs api --since "5m"

# 複数サービス
docker compose logs api worker --tail 100

# フォロー（リアルタイム）
docker compose logs -f api worker
```

### フィルタリング

```bash
# キーワード検索
docker compose logs api --tail 500 | grep -i "error"

# run_id で絞り込み
docker compose logs worker --tail 500 | grep "abc-123"

# レベルで絞り込み
docker compose logs api --tail 500 | grep -E "(ERROR|CRITICAL)"
```

### Temporal ログ

```bash
# Temporal サービスのログ
docker compose logs temporal --tail 100

# Temporal UI でも確認可能
# http://localhost:8080/namespaces/default/workflows
```

---

## サービス別調査ポイント

### api（FastAPI）

| 調査項目 | コマンド | 確認内容 |
|---------|---------|---------|
| リクエストログ | `grep "Received"` | リクエストの到達 |
| レスポンスログ | `grep "Response"` | ステータスコード |
| 認証エラー | `grep -i "auth"` | 401/403 エラー |
| バリデーション | `grep -i "validation"` | 422 エラー |

### worker（Temporal Worker）

| 調査項目 | コマンド | 確認内容 |
|---------|---------|---------|
| Activity 開始 | `grep "Starting activity"` | Activity 実行 |
| Activity 失敗 | `grep "Activity failed"` | 失敗原因 |
| LLM 呼び出し | `grep -i "llm\|gemini\|openai"` | LLM エラー |
| ストレージ | `grep -i "minio\|storage"` | ストレージエラー |

### temporal

| 調査項目 | コマンド | 確認内容 |
|---------|---------|---------|
| ワークフロー開始 | `grep "StartWorkflow"` | ワークフロー作成 |
| シグナル | `grep "Signal"` | シグナル送受信 |
| タイムアウト | `grep -i "timeout"` | タイムアウト発生 |

### postgres

| 調査項目 | コマンド | 確認内容 |
|---------|---------|---------|
| 接続エラー | `grep -i "connection"` | 接続問題 |
| クエリエラー | `grep -i "error"` | SQL エラー |
| デッドロック | `grep -i "deadlock"` | デッドロック |

### minio

| 調査項目 | コマンド | 確認内容 |
|---------|---------|---------|
| アップロード失敗 | `grep -i "error"` | 保存エラー |
| 権限エラー | `grep -i "access denied"` | 権限問題 |

---

## エラーパターン

### 一般的なパターン

| パターン | 意味 | 対応 |
|---------|------|------|
| 連続エラー | 同じエラーが短時間に複数 | 根本原因の特定 |
| 間欠エラー | ランダムに発生 | タイミング依存の問題 |
| 特定 run_id | 特定の処理でのみ発生 | 入力データの問題 |
| 全体障害 | 全リクエストで発生 | インフラ問題 |

### キーワード別

| キーワード | 調査方向 |
|-----------|---------|
| `connection refused` | サービス未起動、ネットワーク |
| `timeout` | 処理遅延、リソース不足 |
| `memory` | メモリ不足 |
| `disk` | ディスク容量 |
| `permission` | 権限設定 |

---

## 実行手順

```
1. 対象サービスを特定
   └─ エラーが発生したサービス

2. ログを取得
   └─ docker compose logs <service> --tail N

3. エラーを抽出
   └─ grep でフィルタリング

4. 時系列で整理
   └─ タイムスタンプでソート

5. 関連ログを収集
   └─ エラー前後のログも確認

6. パターンを分析
   └─ 連続性、頻度、関連性

7. 報告
   └─ 要約と詳細を構造化
```

---

## 使用例

```
api サービスの最新エラーログを調査してください
```

```
@log-investigator に worker の過去 10 分のログを調べさせてください
```

```
run_id abc-123 に関連するログを全サービスから収集してください
```

```
LLM タイムアウトエラーのパターンを調査してください
```

---

## 出力例

### エラー発見

```yaml
status: found
target: worker
time_range: "過去 5 分"

findings:
  - timestamp: "2025-01-01T00:03:45.123Z"
    level: ERROR
    service: worker
    message: "Activity 'step5_generate' failed: LLM timeout"
    context:
      run_id: "abc-123"
      activity: "step5_generate"
      attempt: 3
    related_logs:
      - "[00:03:40] Starting activity step5_generate for run abc-123"
      - "[00:03:41] Calling Gemini API..."
      - "[00:04:41] ERROR: Request timeout after 60s"
      - "[00:04:41] ERROR: Activity step5_generate failed"

  - timestamp: "2025-01-01T00:04:50.456Z"
    level: ERROR
    service: worker
    message: "Same error for run def-456"
    context:
      run_id: "def-456"
      activity: "step5_generate"

summary:
  total_errors: 2
  pattern: "step5_generate で LLM タイムアウトが連続発生"
  affected_runs: ["abc-123", "def-456"]

timeline:
  - "00:03:40 - abc-123: step5 開始"
  - "00:04:41 - abc-123: LLM タイムアウト"
  - "00:04:42 - abc-123: リトライ開始"
  - "00:04:50 - def-456: 同様のエラー"

analysis:
  root_cause: "Gemini API が応答しない"
  suggestion: |
    1. Gemini API のステータスを確認
    2. ネットワーク接続を確認
    3. 他の LLM プロバイダへの切り替えを検討
```

### エラーなし

```yaml
status: not_found
target: api
time_range: "過去 5 分"

summary:
  errors: 0
  warnings: 2
  info: 45

note: "エラーは見つかりませんでした。WARNING レベルのログを確認しますか？"
```

---

## 注意事項

- 大量のログは要約して報告（全文は必要な場合のみ）
- secrets（APIキー等）がログに含まれていないか注意
- 時刻は UTC / JST を明記
- 長時間のログ調査はタイムアウトに注意
