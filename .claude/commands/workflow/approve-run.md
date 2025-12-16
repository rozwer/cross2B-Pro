---
description: 工程3のレビュー承認（Temporal signal で再開）
---

## 実行（仕様書の `/approve`）

```bash
curl -sS -X POST "$API_BASE_URL/api/workflows/$WORKFLOW_ID/approve" \\
  -H "Authorization: Bearer $TOKEN"
```

承認が監査ログに記録され、工程4以降が再開されることを確認する。
