# SEO記事自動生成システム - Codex 指示書

## プロジェクト概要

マルチテナント対応のSEO記事自動生成システム。
- Temporal でワークフロー制御
- LangGraph で工程ロジック
- FastAPI + Next.js でUI/API

## 最重要ルール

### 1. テナント分離（必須）
- 全てのDB/Storage/APIアクセスに `tenant_id` スコープ
- URLパラメータの `tenant_id` を信用しない（認証から取得）

### 2. フォールバック禁止
- 別モデル/プロバイダへの自動切替禁止
- モック逃げ禁止
- 許可: 同一条件リトライ（3回まで）

### 3. 決定性（Temporal）
- Workflow内で `datetime.now()` 直接呼び出し禁止
- 外部I/OはActivityに閉じ込め

### 4. 成果物管理
- 重いデータはstorage保存、参照（path/digest）のみDB/stateに保持

## ファイル構成

```
apps/
├── api/          # FastAPI
├── ui/           # Next.js
└── worker/       # Temporal Worker + Activities
    └── activities/
        ├── step*.py      # 各工程のActivity
        └── schemas/      # Pydanticスキーマ
```

## レビュー時の注意

1. `tenant_id` が適切にスコープされているか
2. Activity が冪等か
3. エラー時にフォールバックしていないか
4. 監査ログが記録されているか
