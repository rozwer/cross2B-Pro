---
description: ローカル起動（Docker Compose で全サービスを起動）
---

## クイック起動（推奨）

```bash
# 初回または完全リセット後
./scripts/bootstrap.sh

# 通常起動
docker compose up -d
```

## 手順（個別）

### 1. 依存を用意（初回のみ）

```bash
# Python 依存
uv sync

# Node.js 依存（UI）
cd apps/ui && npm install && cd ../..

# 環境変数ファイルをコピー
cp .env.example .env
# .env を編集して API キー等を設定
```

### 2. インフラのみ起動（開発時）

```bash
docker compose up -d postgres minio temporal temporal-ui
```

### 3. 全サービス起動

```bash
docker compose up -d
```

### 4. 起動確認

```bash
# サービス状態
docker compose ps

# API ヘルスチェック
curl -s http://localhost:8000/health | jq .

# Temporal UI
open http://localhost:8080

# フロントエンド
open http://localhost:3000
```

## サービス一覧

| サービス    | ポート     | 説明                    |
| ----------- | ---------- | ----------------------- |
| postgres    | 5432       | PostgreSQL データベース |
| minio       | 9000, 9001 | オブジェクトストレージ  |
| temporal    | 7233       | ワークフローエンジン    |
| temporal-ui | 8080       | Temporal 管理UI         |
| api         | 8000       | FastAPI バックエンド    |
| worker      | -          | Temporal Worker         |
| ui          | 3000       | Next.js フロントエンド  |

## トラブルシューティング

| 症状              | 解決策                              |
| ----------------- | ----------------------------------- |
| ポート競合        | `.env` でポート変更 or `lsof -i :PORT` |
| コンテナ起動失敗  | `docker compose logs <service>` で確認 |
| DB 接続エラー     | `docker compose restart postgres`   |
