# E2Eテストサマリー - 2025年12月17日 (2回目)

## テスト概要

| 項目 | 値 |
|------|-----|
| **Run ID** | `1c4ca12e-0bfd-4d7b-9bfa-bdbc6d25fe99` |
| **Tenant ID** | `dev-tenant-001` |
| **キーワード** | クラウドネイティブアプリケーション |
| **モデル** | `gemini-2.0-flash` |
| **開始時刻** | 2025-12-17 19:11:39 JST |
| **完了時刻** | 2025-12-17 19:19:23 JST |
| **所要時間** | 約8分 |
| **最終ステータス** | ⚠️ **成果物生成成功、状態同期エラー** |

## 全ステップ完了状況

| ステップ | 説明 | 状態 | 出力サイズ |
|---------|------|------|-----------|
| Step0 | キーワード選定 | ✅ | 1.6KB |
| Step1 | 競合記事取得 | ✅ | 207KB |
| Step2 | CSV検証 | ✅ | 207KB |
| Step3A | クエリ分析 | ✅ | 1.2KB |
| Step3B | 共起語分析 | ✅ | 2.0KB |
| Step3C | 競合分析 | ✅ | 0.8KB |
| **承認** | Human-in-the-loop | ✅ | - |
| Step4 | 戦略的アウトライン | ✅ | 4.9KB |
| Step5 | 一次情報収集 | ✅ | 438KB |
| Step6 | 強化アウトライン | ✅ | 6.0KB |
| Step6.5 | 統合パッケージ | ✅ | 14KB |
| Step7A | ドラフト生成 | ✅ | 14KB |
| Step7B | ブラッシュアップ | ✅ | 23KB |
| Step8 | ファクトチェック | ✅ | 26KB |
| Step9 | 最終リライト | ✅ | 28KB |
| Step10 | 最終出力（HTML） | ✅ | 63KB |

## 発生したエラー

### sync_run_status アクティビティ未登録

```
temporalio.exceptions.ApplicationError: NotFoundError: Activity function sync_run_status
for workflow 1c4ca12e-0bfd-4d7b-9bfa-bdbc6d25fe99 is not registered on this worker
```

**原因:** Workerに `sync_run_status` アクティビティが登録されていない

**影響:** 成果物生成は全て成功。APIの最終ステータス更新のみ失敗。

**修正案:** `apps/worker/main.py` に `sync_run_status` アクティビティを追加登録

## 実行コマンド

### 1. 新規ワークフロー作成

```bash
curl -s -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -d '{
    "input": {"keyword": "クラウドネイティブアプリケーション"},
    "model_config": {"platform": "gemini", "model": "gemini-2.0-flash"}
  }' | jq '{id, status}'
```

### 2. 状態確認

```bash
curl -s "http://localhost:8000/api/runs/1c4ca12e-0bfd-4d7b-9bfa-bdbc6d25fe99" \
  -H "X-Tenant-ID: dev-tenant-001" | jq '{status, current_step}'
```

### 3. 承認

```bash
curl -s -X POST "http://localhost:8000/api/runs/1c4ca12e-0bfd-4d7b-9bfa-bdbc6d25fe99/approve" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -d '{}'
```

### 4. 成果物確認

```bash
docker compose exec minio mc ls --recursive local/seo-gen-artifacts/ | grep "1c4ca12e-0bfd-4d7b-9bfa-bdbc6d25fe99"
```

### 5. Worker ログ確認

```bash
docker compose logs worker --tail 50
```

## ストレージパス

```
storage/dev-tenant-001/1c4ca12e-0bfd-4d7b-9bfa-bdbc6d25fe99/
├── step0/output.json      (1.6KB)
├── step1/output.json      (207KB)
├── step2/output.json      (207KB)
├── step3a/output.json     (1.2KB)
├── step3b/output.json     (2.0KB)
├── step3c/output.json     (0.8KB)
├── step4/output.json      (4.9KB)
├── step5/output.json      (438KB)
├── step6/output.json      (6.0KB)
├── step6_5/output.json    (14KB)
├── step7a/output.json     (14KB)
├── step7b/output.json     (23KB)
├── step8/output.json      (26KB)
├── step9/output.json      (28KB)
└── step10/output.json     (63KB)
```

## 結論

**全15ステップの成果物生成は成功**しました。

Human-in-the-loopの承認フローも正常に動作しました。

唯一の問題は `sync_run_status` アクティビティ未登録による最終ステータス更新エラーです。
これはWorkerの設定修正で解決可能です。
