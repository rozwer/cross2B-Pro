# cross2B-Pro Development Rules

## Project Overview

SEO記事自動生成ワークフローシステム。キーワードから競合分析・アウトライン作成・本文生成・ファクトチェック・画像生成までを19ステップで自動実行する。

### Architecture

| Component | Tech | Directory |
|-----------|------|-----------|
| API | FastAPI (Python 3.11) | `apps/api/` |
| Worker | Temporal Workflows (Python) | `apps/worker/` |
| UI | Next.js 14 (TypeScript) | `apps/ui/` |
| DB | PostgreSQL 16 | Docker: `postgres` |
| Storage | MinIO (S3互換) | Docker: `minio` |
| Orchestration | Temporal Server | Docker: `temporal` |

### Docker Services & Ports

| Service | Internal Port | External Port | URL |
|---------|--------------|---------------|-----|
| `api` | 8000 | 28000 | http://localhost:28000 |
| `ui` | 3000 | 23000 | http://localhost:23000 |
| `postgres` | 5432 | 25432 | - |
| `minio` | 9000/9001 | 29000/29001 | http://localhost:29001 (Console) |
| `temporal` | 7233 | 27233 | - |
| `temporal-ui` | 8080 | 28080 | http://localhost:28080 |
| `worker` | - | - | (no HTTP) |

## Quick Start

```bash
# 1. 環境変数を設定
cp .env.example .env   # APIキー等を記入

# 2. 全サービス起動
docker compose up -d

# 3. DB初期化（初回 or リセット時）
./scripts/init-database.sh          # スキーマ + シードデータ適用
./scripts/init-database.sh --reset  # DB再作成から
```

## Workflow Testing Rules (CRITICAL)

- **全ステップ一括実行は禁止** — ユーザーの明示的な許可がない限り、ワークフロー全体を実行してはならない
- **ステップ単体検証が必須** — 修正後はPythonスクリプトで該当ステップのみを個別実行し、出力を確認してから次へ進む
- **検証なしのデプロイ禁止** — workerリビルド後に自動でフロー実行しない。必ずステップごとに検証する

## Development Patterns

- `uv run pytest` でテスト実行（pip不使用）
- Docker Compose サービス名は `api`, `ui`, `worker`, `postgres` 等（`seo-` prefix不要）
- MinIOパス: `seo-artifacts/storage/{tenant_id}/{run_id}/{step}/output.json`
- プロンプトパック: `apps/api/prompts/packs/default.json`
- UI→API通信: ブラウザ側は相対パス `/api/...` を使用（Next.js rewrite経由）

## Step Verification Method

各ステップの検証は以下のパターンで行う:
```bash
set -a && source .env && set +a && uv run python3 <<'SCRIPT'
# 1. MinIOから前ステップの出力を読み込む
# 2. プロンプトを構築
# 3. LLMを直接呼び出す
# 4. 結果を表示して確認
SCRIPT
```

## Database

- **init-db.sql**: Docker初回起動時に自動実行（テーブル作成 + 基本シード）
- **schema.sql**: `pg_dump --schema-only` の出力（スキーマ参照用）
- **seed.sql**: `pg_dump --data-only` の出力（マスタデータのみ、ユーザーデータ除外）
- **init-database.sh**: schema.sql + seed.sql を適用 + シーケンスリセット

シードデータ更新手順:
```bash
# スキーマをダンプ
docker compose exec -T postgres pg_dump -U seo -d seo_articles \
  --schema-only --no-owner --no-privileges > scripts/schema.sql

# マスタデータのみダンプ（runs/steps等は除外）
docker compose exec -T postgres pg_dump -U seo -d seo_articles \
  --data-only --no-owner --no-privileges \
  -t tenants -t llm_providers -t llm_models -t step_llm_defaults \
  -t prompts -t api_settings -t hearing_templates -t help_contents \
  > scripts/seed.sql
```

## Key Conventions

- Python依存管理: `uv` (not pip)
- テストは `tests/` ディレクトリ（gitignore対象だが `scripts/test_*.py` は追跡対象）
- `scripts/` ディレクトリは追跡対象（`*.backup` のみ除外）
- LLMクライアント: `get_step_model_config()` でステップ別モデル設定を取得
- Gemini 2.5 Pro: thinking tokensがmax_output_tokensを消費するため十分な値を設定
