---
description: 既存 run を開始（API が start 分離の場合の手順）
---

## 注意

`仕様書/システム仕様書_技術者向け.md` では `POST /api/workflows` が開始に相当します。  
start エンドポイントを採用する場合のみ、この手順を使ってください。

## 例

```bash
curl -sS -X POST "$API_BASE_URL/api/workflows/$WORKFLOW_ID/start" \\
  -H "Authorization: Bearer $TOKEN"
```
