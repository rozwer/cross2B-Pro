---
description: 生成物取得（files 一覧→工程別出力→storage）
---

## 1) 生成物一覧

```bash
curl -sS "$API_BASE_URL/api/workflows/$WORKFLOW_ID/files" \\
  -H "Authorization: Bearer $TOKEN"
```

## 2) 工程別の出力取得（例：step3）

```bash
curl -sS "$API_BASE_URL/api/workflows/$WORKFLOW_ID/files/step3" \\
  -H "Authorization: Bearer $TOKEN"
```

## 3) `file_path` が storage 参照の場合

- presigned URL を返す設計なら、その URL からダウンロードする。
- 直接参照の設計なら、tenant 越境が起きないよう API 側で権限チェックを入れる。
