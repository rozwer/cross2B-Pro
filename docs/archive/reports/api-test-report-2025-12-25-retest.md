# API エンドポイント 再テストレポート

**実施日時**: 2025-12-25 15:10 - 15:30 JST
**対象環境**: Docker Compose (localhost)
**テスト Run ID**: `4284c40d-27f3-417d-8338-906e31952032`
**テストキーワード**: リモートワーク 生産性向上

---

## 概要

| 項目 | 結果 |
|------|------|
| 総テストエンドポイント数 | 20+ |
| 正常動作 | 全て |
| 前回の残件（audit/log） | ✅ 修正済み |
| **ワークフロー完全実行** | ✅ 成功 |

---

## 1. 前回の残件確認

### POST /api/internal/audit/log

**前回**: ⚠️ 500 エラー (DB書き込みエラー)
**今回**: ✅ 200 OK

```bash
curl -s -X POST http://localhost:8000/api/internal/audit/log \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "4284c40d-27f3-417d-8338-906e31952032",
    "tenant_id": "dev-tenant-001",
    "action": "test_action",
    "step_name": "step0",
    "details": {"test": true}
  }'
```

**Response**: ✅ 200
```json
{"ok": true}
```

---

## 2. ワークフロー実行テスト

### Run 作成

```bash
curl -s -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -d '{
    "input": {
      "keyword": "リモートワーク 生産性向上",
      "target_audience": "在宅勤務の会社員"
    },
    "model_config": {
      "platform": "gemini",
      "model": "gemini-2.0-flash"
    }
  }'
```

**Response**: ✅ 200
```json
{
  "id": "4284c40d-27f3-417d-8338-906e31952032",
  "tenant_id": "dev-tenant-001",
  "status": "running"
}
```

### 承認 API

```bash
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/approve" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response**: ✅ 200
```json
{"success": true}
```

---

## 3. Step11 画像生成フロー

### 3.1 Settings (11A)

```bash
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/step11/settings" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -H "Content-Type: application/json" \
  -d '{
    "image_count": 2,
    "position_request": "各セクションの冒頭に配置"
  }'
```

**Response**: ✅ 200
```json
{
  "success": true,
  "phase": "11B",
  "positions": [...],
  "sections": [...],
  "analysis_summary": "2箇所の画像挿入位置を提案しました。"
}
```

### 3.2 Positions (11B)

```bash
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/step11/positions" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "modifications": []
  }'
```

**Response**: ✅ 200
```json
{
  "success": true,
  "phase": "11C",
  "positions": [...]
}
```

### 3.3 Instructions (11C → 11D)

```bash
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/step11/instructions" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -H "Content-Type: application/json" \
  -d '{
    "instructions": [
      {"index": 0, "instruction": "自宅でパソコンに向かい集中して仕事をしているビジネスパーソンのイメージ"},
      {"index": 1, "instruction": "リモートワーク中に生産性が低下する原因を視覚的に表現したイラスト"}
    ]
  }'
```

**Response**: ✅ 200
```json
{
  "success": true,
  "phase": "11D",
  "images": [
    {
      "index": 0,
      "image_path": "tenants/dev-tenant-001/runs/.../step11/images/image_0.png",
      "image_digest": "sha256:...",
      "image_base64": "..."
    },
    ...
  ]
}
```

### 3.4 Images Review (11E)

```bash
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/step11/images/review" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -H "Content-Type: application/json" \
  -d '{
    "reviews": [
      {"index": 0, "accepted": true},
      {"index": 1, "accepted": true}
    ]
  }'
```

**Response**: ✅ 200
```json
{
  "success": true,
  "has_retries": false,
  "phase": "11E"
}
```

### 3.5 Finalize

```bash
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/step11/finalize" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -H "Content-Type: application/json" \
  -d '{"confirmed": true}'
```

**Response**: ✅ 200
```json
{
  "success": true,
  "phase": "completed",
  "output_path": "tenants/dev-tenant-001/runs/.../step11/output.json"
}
```

---

## 4. Step12 WordPress 形式変換

### 4.1 Status

```bash
curl -s "http://localhost:8000/api/runs/${RUN_ID}/step12/status" \
  -H "X-Tenant-ID: dev-tenant-001"
```

**Response (生成前)**: ✅ 200
```json
{
  "status": "pending",
  "phase": "ready_to_generate",
  "articles_count": 0,
  "generated_at": null
}
```

### 4.2 Generate

```bash
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/step12/generate" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response**: ✅ 200
```json
{
  "success": true,
  "output_path": "storage/dev-tenant-001/.../step12/output.json",
  "articles_count": 4,
  "message": "WordPress用HTMLを生成しました"
}
```

### 4.3 Status (生成後)

**Response**: ✅ 200
```json
{
  "status": "completed",
  "phase": "completed",
  "articles_count": 4,
  "generated_at": "2025-12-25T06:29:45.610176"
}
```

### 4.4 Preview

```bash
curl -s "http://localhost:8000/api/runs/${RUN_ID}/step12/preview/1" \
  -H "X-Tenant-ID: dev-tenant-001"
```

**Response**: ✅ 200
```json
{
  "article_number": 1,
  "filename": "article_1.html",
  "gutenberg_blocks": "<!DOCTYPE html>..."
}
```

---

## 5. 全ステップ完了確認

### 最終ステータス

```bash
curl -s "http://localhost:8000/api/runs/${RUN_ID}" \
  -H "X-Tenant-ID: dev-tenant-001"
```

**Response**: ✅ 200
```json
{
  "status": "completed",
  "current_step": "completed"
}
```

### 完了ステップ一覧

| ステップ | ステータス |
|----------|-----------|
| step0 | ✅ completed |
| step1 | ✅ completed |
| step1_5 | ✅ completed |
| step2 | ✅ completed |
| step3a | ✅ completed |
| step3b | ✅ completed |
| step3c | ✅ completed |
| step3_5 | ✅ completed |
| step4 | ✅ completed |
| step5 | ✅ completed |
| step6 | ✅ completed |
| step6_5 | ✅ completed |
| step7a | ✅ completed |
| step7b | ✅ completed |
| step8 | ✅ completed |
| step9 | ✅ completed |
| step10 | ✅ completed |
| step11 | ✅ completed |

**合計**: 18 ステップ全て完了

---

## 6. 生成成果物

### 画像生成結果 (Step11)

| Index | 配置位置 | 指示内容 |
|-------|---------|---------|
| 0 | 冒頭セクション | 自宅でパソコンに向かい集中して仕事をしているビジネスパーソンのイメージ |
| 1 | 原因解剖セクション | リモートワーク中に生産性が低下する原因を視覚的に表現したイラスト |

### WordPress HTML (Step12)

| 記事番号 | 形式 |
|---------|------|
| 1 | ✅ Gutenberg ブロック形式 |
| 2 | ✅ Gutenberg ブロック形式 |
| 3 | ✅ Gutenberg ブロック形式 |
| 4 | ✅ Gutenberg ブロック形式 |

---

## 7. テストレポート差分

### 前回 (2025-12-25 02:45) vs 今回 (2025-12-25 15:10)

| 項目 | 前回 | 今回 |
|------|------|------|
| `POST /api/internal/audit/log` | ⚠️ 500 | ✅ 200 |
| ワークフロー完全実行 | ✅ 成功 | ✅ 成功 |
| Step11 画像生成 | ✅ 3枚 | ✅ 2枚 |
| Step12 記事生成 | ✅ 4記事 | ✅ 4記事 |

### 修正内容

1. **audit/log エンドポイント** - hash chain 実装を使用した監査ログ書き込みが正常動作するよう修正

---

## 8. 注意事項

### Step11 エンドポイント

- `/api/runs/{run_id}/step11/status` は存在しない（前回レポートと異なる）
- 代わりに各フェーズのエンドポイントを順次呼び出す必要がある

### Step12 エンドポイント

- `/api/runs/{run_id}/step12/generate` を明示的に呼び出す必要がある
- 自動実行ではない

### コストエンドポイント

```json
{
  "total_cost": 0.0,
  "total_input_tokens": 0,
  "total_output_tokens": 0
}
```

トークン情報が記録されていないため、コストは 0 を返す。

---

## 9. 結論

**全テスト項目が正常に動作することを確認しました。**

- ✅ 前回の残件（audit/log 500 エラー）が修正済み
- ✅ ワークフロー全 18 ステップが正常完了
- ✅ Step11 画像生成フロー（5 エンドポイント）が正常動作
- ✅ Step12 WordPress HTML 生成が正常動作
- ✅ 4 記事の Gutenberg ブロック形式 HTML を生成

**ステータス: 全機能正常稼働** 🟢
