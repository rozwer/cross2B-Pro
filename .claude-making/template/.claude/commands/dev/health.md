---
description: 全サービスのヘルスチェック（@docker-manager 連携）
allowed-tools: Bash, Task
---

## 実行

@docker-manager に以下を依頼:
- action: health

## 使用例

```
/dev:health          # 全サービスのヘルスチェック
```

## 出力形式

```
| サービス    | 状態          | ポート     |
|-------------|---------------|------------|
| postgres    | ✅ healthy    | 5432       |
| minio       | ✅ healthy    | 9000       |
| temporal    | ✅ healthy    | 7233       |
| temporal-ui | ✅ running    | 8080       |
| api         | ✅ healthy    | 8000       |
| worker      | ✅ running    | -          |
| ui          | ❌ unhealthy  | 3000       |

Summary: 6/7 healthy, 1 unhealthy
```

---

## クイックリファレンス

### 手動コマンド

```bash
# コンテナ一覧
docker compose ps

# 詳細ヘルスチェック
docker compose exec postgres pg_isready -U seo -d seo_articles
docker compose exec minio mc ready local
docker compose exec temporal tctl --address temporal:7233 cluster health
curl -f http://localhost:8000/health
curl -f http://localhost:3000
```

### サービス別ヘルスチェック方法

| サービス    | チェック方法                              |
| ----------- | ----------------------------------------- |
| postgres    | `pg_isready -U seo -d seo_articles`       |
| minio       | `mc ready local`                          |
| temporal    | `tctl cluster health`                     |
| temporal-ui | HTTP GET (起動確認)                       |
| api         | `curl http://localhost:8000/health`       |
| worker      | プロセス存在確認                          |
| ui          | HTTP GET (起動確認)                       |

### unhealthy 時の対応

1. ログを確認: `/dev:logs <service>`
2. 再起動: `docker compose restart <service>`
3. トラブルシュート: `@docker-manager troubleshoot`