---
description: run の障害解析（API→DB→Temporal→storage の順に辿る）
---

## 1) API で状態確認

```bash
curl -sS "$API_BASE_URL/api/workflows/$WORKFLOW_ID" \\
  -H "Authorization: Bearer $TOKEN"
```

## 2) 失敗工程を特定

- `current_step` / `step_executions` / `last_error` を確認
- `output_path` があれば storage 側の成果物を確認

## 3) Temporal がある場合（例）

```bash
temporal workflow show --workflow-id "$WORKFLOW_ID"
```
