---
description: 全サービスのヘルスチェック（@docker-manager 連携）
allowed-tools: Bash, Task
---

## 実行

@docker-manager に以下を依頼:
- action: health

## 使用例

\`\`\`
/dev:health          # 全サービスのヘルスチェック
\`\`\`

## 出力形式

\`\`\`
| サービス    | 状態          | ポート     |
|-------------|---------------|------------|
| db          | healthy       | 5432       |
| cache       | healthy       | 6379       |
| api         | healthy       | 8000       |
| worker      | running       | -          |
| ui          | unhealthy     | 3000       |

Summary: 4/5 healthy, 1 unhealthy
\`\`\`

---

## クイックリファレンス

### 手動コマンド

\`\`\`bash
# コンテナ一覧
docker compose ps

# 詳細ヘルスチェック（例）
docker compose exec db pg_isready -U \$DB_USER -d \$DB_NAME
curl -f http://localhost:8000/health
curl -f http://localhost:3000
\`\`\`

### サービス別ヘルスチェック方法

| サービス    | チェック方法                              |
| ----------- | ----------------------------------------- |
| db          | \`pg_isready\` / \`mysqladmin ping\` 等       |
| cache       | \`redis-cli ping\` 等                       |
| api         | \`curl http://localhost:8000/health\`       |
| worker      | プロセス存在確認                          |
| ui          | HTTP GET (起動確認)                       |

### unhealthy 時の対応

1. ログを確認: \`/dev:logs <service>\`
2. 再起動: \`docker compose restart <service>\`
3. トラブルシュート: \`@docker-manager troubleshoot\`
