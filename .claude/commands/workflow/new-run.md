---
description: 新規 run/workflow を開始（API 経由）
---

## 前提

- `API_BASE_URL`（例：`http://localhost:8000`）
- `TOKEN`（Bearer）

## 実行例（仕様書の `/api/workflows`）

```bash
curl -sS -X POST "$API_BASE_URL/api/workflows" \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "project_name": "demo",
    "config": {
      "keyword": "例: SEO記事 自動生成",
      "target_word_count": 8000
    }
  }'
```

返ってきた `id`（または `workflow_run_id`）を控える。
