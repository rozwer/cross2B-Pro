# E2Eテスト コマンドリファレンス

## 1. 新規ワークフロー作成

```bash
curl -s -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -d '{
    "input": {
      "keyword": "クラウドネイティブアプリケーション"
    },
    "model_config": {
      "platform": "gemini",
      "model": "gemini-2.0-flash"
    }
  }' | jq .
```

**レスポンス例:**

```json
{
  "id": "618923ad-c915-4415-9f25-6857ac69dd7d",
  "tenant_id": "dev-tenant-001",
  "status": "running",
  ...
}
```

## 2. 状態確認コマンド

### API でワークフロー状態取得

```bash
RUN_ID="618923ad-c915-4415-9f25-6857ac69dd7d"
curl -s "http://localhost:8000/api/runs/${RUN_ID}" \
  -H "X-Tenant-ID: dev-tenant-001" | jq '{status, current_step}'
```

### Worker ログ確認

```bash
# 最新30行
docker compose logs worker --tail 30

# リアルタイム監視
docker compose logs worker --tail 10 --follow
```

### Temporal UI API でワークフロー状態取得

```bash
RUN_ID="618923ad-c915-4415-9f25-6857ac69dd7d"
curl -s "http://localhost:8080/api/v1/namespaces/default/workflows/${RUN_ID}" | jq '.workflowExecutionInfo.status'
```

### MinIO ストレージ 成果物確認

```bash
# バケット一覧
docker compose exec minio mc ls local/

# 特定 run の成果物一覧
RUN_ID="618923ad-c915-4415-9f25-6857ac69dd7d"
docker compose exec minio mc ls --recursive local/seo-gen-artifacts/ | grep "${RUN_ID}"
```

### DB 確認（runs テーブル）

```bash
docker compose exec postgres psql -U seo -d seo_articles \
  -c "SELECT id, status, current_step FROM runs WHERE id = '618923ad-c915-4415-9f25-6857ac69dd7d'"
```

## 3. ワークフロー操作

### 承認

```bash
RUN_ID="618923ad-c915-4415-9f25-6857ac69dd7d"
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/approve" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -d '{}'
```

### 却下

```bash
RUN_ID="618923ad-c915-4415-9f25-6857ac69dd7d"
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/reject" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -d '{"reason": "内容を修正してください"}'
```

### 工程再実行

```bash
RUN_ID="618923ad-c915-4415-9f25-6857ac69dd7d"
STEP="step3a"
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/retry/${STEP}" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant-001"
```

### キャンセル

```bash
RUN_ID="618923ad-c915-4415-9f25-6857ac69dd7d"
curl -s -X DELETE "http://localhost:8000/api/runs/${RUN_ID}" \
  -H "X-Tenant-ID: dev-tenant-001"
```

## 4. 成果物取得

### 生成物一覧

```bash
RUN_ID="618923ad-c915-4415-9f25-6857ac69dd7d"
curl -s "http://localhost:8000/api/runs/${RUN_ID}/files" \
  -H "X-Tenant-ID: dev-tenant-001" | jq .
```

### 工程別出力取得

```bash
RUN_ID="618923ad-c915-4415-9f25-6857ac69dd7d"
STEP="step10"
curl -s "http://localhost:8000/api/runs/${RUN_ID}/files/${STEP}" \
  -H "X-Tenant-ID: dev-tenant-001" | jq .
```

## 5. インフラ確認

### Docker サービス状態

```bash
docker compose ps
```

### API ヘルスチェック

```bash
curl -s http://localhost:8000/health | jq .
```

### ポート使用確認

```bash
lsof -i :8000  # API
lsof -i :7233  # Temporal
lsof -i :8080  # Temporal UI
lsof -i :9000  # MinIO
lsof -i :5432  # PostgreSQL
```

## 6. ワークフロー全ステップ一覧

| ステップ     | 説明               | 依存         |
| ------------ | ------------------ | ------------ |
| step0        | キーワード選定     | -            |
| step1        | 競合記事取得       | step0        |
| step2        | CSV検証            | step1        |
| step3a       | クエリ分析         | step0, step1 |
| step3b       | 共起語分析         | step1        |
| step3c       | 競合分析           | step1        |
| **承認待ち** | Human-in-the-loop  | step3完了    |
| step4        | 戦略的アウトライン | step3a/b/c   |
| step5        | 一次情報収集       | step4        |
| step6        | 強化アウトライン   | step5        |
| step6_5      | 統合パッケージ     | step6        |
| step7a       | ドラフト生成       | step6_5      |
| step7b       | ブラッシュアップ   | step7a       |
| step8        | ファクトチェック   | step7b       |
| step9        | 最終リライト       | step8        |
| step10       | 最終出力（HTML）   | step9        |

## 7. トラブルシューティング

### ポート競合

```bash
# 既存プロセス確認
lsof -i :8000

# プロセス終了（PIDを指定）
kill -9 <PID>
```

### Worker が動かない

```bash
# Worker 再起動
docker compose restart worker

# Worker ログ確認
docker compose logs worker --tail 50
```

### 承認が効かない

APIとTemporalの状態同期が取れていない可能性あり。
Temporal UI (http://localhost:8080) で直接確認。
