# 実行ガイド（RUN.md）

本ドキュメントは、SEO記事自動生成システムの起動から動作確認までの手順をまとめたものです。

## 前提条件

以下がインストールされていること:

| 項目 | 最小バージョン | 確認コマンド |
|------|---------------|-------------|
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| Python | 3.11+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| uv | 0.4+ | `uv --version` |

```bash
# 環境一括チェック
./scripts/check-env.sh
```

---

## 1. 環境構築

### 1.1 環境変数の設定

```bash
# テンプレートをコピー
cp .env.example .env

# .env を編集（最低限1つのLLM APIキーが必要）
# GEMINI_API_KEY=your-key
# または
# OPENAI_API_KEY=your-key
# または
# ANTHROPIC_API_KEY=your-key
# または
# USE_MOCK_LLM=true  # モックモード（APIキー不要）
```

### 1.2 依存関係のインストール

```bash
# Python依存関係（uvが.venvを自動作成）
uv sync

# フロントエンド依存関係
cd apps/ui && npm install && cd ../..
```

---

## 2. 起動方法

### 方法A: LangGraph Studio（開発・デバッグ推奨）

LangGraph Studio はグラフの可視化とステップ実行が可能な開発環境です。

#### 2.1 LangGraph Studio のインストール

```bash
# langgraph-cli のインストール（未インストールの場合）
pip install langgraph-cli

# または uv で
uv pip install langgraph-cli
```

#### 2.2 本番グラフの起動

```bash
# プロジェクトルートで起動（本番用グラフ）
cd /home/rozwer/案件
uv run langgraph dev
```

**起動後のアクセス先:**

| サービス | URL | 説明 |
|----------|-----|------|
| LangGraph Studio | http://localhost:8123 | グラフ可視化・実行UI |

#### 2.3 利用可能なグラフ

| グラフ名 | 説明 | 工程 |
|----------|------|------|
| `pre_approval` | 承認前フロー | step0 → step1 → step2 → step3(並列) |
| `post_approval` | 承認後フロー | step4 → step5 → ... → step10 |

#### 2.4 LangGraph Studio の使い方

1. ブラウザで http://localhost:8123 にアクセス
2. 左側のグラフ一覧から `pre_approval` または `post_approval` を選択
3. 入力欄に GraphState を入力して実行
4. グラフの各ノードの実行状態をリアルタイムで確認可能
5. 各ステップの入出力を詳細に確認可能

**langgraph.json の設定（プロジェクトルート）:**

```json
{
  "dependencies": ["."],
  "graphs": {
    "pre_approval": "./apps/worker/graphs/pre_approval.py:pre_approval_graph",
    "post_approval": "./apps/worker/graphs/post_approval.py:post_approval_graph"
  },
  "env": ".env"
}
```

#### 2.5 サンプルエージェント（参考用）

独立したサンプル実装も用意されています：

```bash
# サンプルディレクトリで起動
cd langgraph-example
cp .env.example .env
# .env を編集してAPIキーを設定
langgraph dev
```

---

### 方法B: LangGraph BE + UI（本番相当の動作確認）

本番環境に近い構成で、FastAPI バックエンド + Next.js フロントエンドを使用します。

#### 2.4 インフラの起動

```bash
# インフラサービス（PostgreSQL, MinIO, Temporal）を起動
docker compose up -d postgres minio temporal temporal-ui
```

#### 2.5 バックエンド（LangGraph BE）の起動

```bash
# APIサーバーを起動
uv run uvicorn apps.api.main:app --reload --port 8000

# 別ターミナルで Temporal Worker を起動
uv run python -m apps.worker.main
```

#### 2.6 フロントエンド（UI）の起動

```bash
# apps/ui ディレクトリに移動して起動
cd apps/ui
npm run dev
```

**起動後のアクセス先:**

| サービス | URL | 説明 |
|----------|-----|------|
| UI | http://localhost:3000 | フロントエンド |
| API | http://localhost:8000 | バックエンドAPI |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Temporal UI | http://localhost:8080 | ワークフロー管理 |
| MinIO Console | http://localhost:9001 | ストレージ管理 |

---

### 方法C: Docker Compose（フル起動）

すべてのサービスをコンテナで起動します。

```bash
# 初回起動（推奨）
./scripts/bootstrap.sh

# 通常起動
docker compose up -d

# ログ確認
docker compose logs -f
```

---

## 3. 動作確認

### 3.1 ヘルスチェック

```bash
# API ヘルスチェック
curl http://localhost:8000/health

# 期待レスポンス:
# {"status":"healthy","timestamp":"2025-12-16T...","checks":{...}}
```

### 3.2 smoke テスト実行

```bash
# 全smoke テスト
uv run pytest tests/smoke/ -v

# 期待結果: 19 passed
```

### 3.3 全ユニットテスト実行

```bash
# ユニット + smoke テスト
uv run pytest tests/ -v --ignore=tests/integration --ignore=tests/e2e

# 期待結果: 300 passed
```

### 3.4 型チェック + リント

```bash
# mypy（型チェック）
uv run mypy apps/ --ignore-missing-imports
# 期待結果: Success: no issues found in 68 source files

# ruff（リント）
uv run ruff check apps/
# 期待結果: All checks passed!
```

---

## 4. ワークフロー実行テスト

### 4.1 LangGraph Studio でのテスト

1. `langgraph dev` で Studio を起動
2. http://localhost:8123 にアクセス
3. グラフを選択して入力を与える
4. 各ノードの実行をステップバイステップで確認

### 4.2 API経由でのワークフロー開始

```bash
# 新規ワークフロー作成（UI型に合致した形式）
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: test_tenant" \
  -d '{
    "input": {
      "keyword": "テストキーワード",
      "target_audience": "SEO初心者",
      "additional_requirements": "分かりやすく解説してください"
    },
    "model_config": {
      "platform": "gemini",
      "model": "gemini-2.0-flash",
      "options": {
        "grounding": true,
        "temperature": 0.7
      }
    },
    "tool_config": {
      "serp_fetch": true,
      "page_fetch": true,
      "url_verify": true,
      "pdf_extract": false
    },
    "options": {
      "retry_limit": 3,
      "repair_enabled": true
    }
  }'

# ワークフローキャンセル（DELETE メソッド）
curl -X DELETE http://localhost:8000/api/runs/{run_id} \
  -H "X-Tenant-ID: test_tenant"

# ワークフロー承認
curl -X POST http://localhost:8000/api/runs/{run_id}/approve \
  -H "X-Tenant-ID: test_tenant"

# 成果物一覧取得
curl http://localhost:8000/api/runs/{run_id}/files \
  -H "X-Tenant-ID: test_tenant"
```

### 4.3 UI からのワークフロー操作

1. http://localhost:3000 にアクセス
2. 新規ワークフローを作成
3. 工程の進捗をリアルタイムで確認
4. 工程3完了後、承認/却下を実行

### 4.4 Temporal UI での確認

1. http://localhost:8080 にアクセス
2. "seo-article-generation" namespace を選択
3. ワークフロー一覧で実行状態を確認

---

## 5. 停止・リセット

### 停止スクリプト（推奨）

```bash
# 全サービス停止（アプリ + Docker）
./scripts/stop.sh

# アプリケーションプロセスのみ停止
./scripts/stop.sh --apps

# Dockerコンテナのみ停止
./scripts/stop.sh --docker

# 全サービス停止 + ボリューム削除
./scripts/stop.sh --all
```

### 手動停止

```bash
# Docker コンテナ停止
docker compose down

# 停止（ボリューム保持）
docker compose stop

# LangGraph Studio 停止
# Ctrl+C で終了
```

### 完全リセット（データ削除）

```bash
./scripts/reset.sh
```

---

## 6. トラブルシューティング

### LangGraph Studio が起動しない

```bash
# langgraph-cli のバージョン確認
langgraph --version

# 依存関係の再インストール
cd langgraph-example
pip install -e .
```

### ポート競合

```bash
# 使用中のポートを確認
lsof -i :8000  # API
lsof -i :3000  # UI
lsof -i :8123  # LangGraph Studio
lsof -i :5432  # PostgreSQL

# .env でポート変更可能
# API_PORT=8001
# UI_PORT=3001
```

### Docker関連

```bash
# コンテナ状態確認
docker compose ps

# 特定サービスの再起動
docker compose restart api

# コンテナログ確認
docker compose logs -f api worker
```

### データベース接続

```bash
# PostgreSQL 接続確認
docker compose exec postgres psql -U seo -d seo_articles -c "SELECT 1"
```

### MinIO接続

```bash
# MinIO バケット確認
docker compose exec minio mc ls local
```

---

## 7. 開発時のコマンド一覧

### 起動・停止

```bash
# LangGraph Studio（本番グラフ）
uv run langgraph dev

# Docker Compose
docker compose up -d      # 起動
docker compose down       # 停止
docker compose restart    # 再起動
docker compose logs -f    # ログ監視

# 手動起動（開発時）
uv run uvicorn apps.api.main:app --reload --port 8000  # API
uv run python -m apps.worker.main                       # Worker
cd apps/ui && npm run dev                               # UI
```

### テスト

```bash
uv run pytest tests/smoke/ -v                   # smoke テスト
uv run pytest tests/unit/ -v                    # ユニットテスト
uv run pytest tests/ --ignore=tests/e2e -v     # 全テスト（e2e除く）
```

### コード品質

```bash
uv run mypy apps/ --ignore-missing-imports    # 型チェック
uv run ruff check apps/                        # リント
uv run ruff check apps/ --fix                  # 自動修正
```

### スラッシュコマンド（Claude Code）

| コマンド | 説明 |
|----------|------|
| `/dev:up` | ローカル環境起動 |
| `/dev:down` | ローカル環境停止 |
| `/dev:smoke` | smoke テスト実行 |
| `/workflow:new-run` | 新規ワークフロー開始 |
| `/workflow:approve-run` | ワークフロー承認 |

---

## 8. 現在の実装状況

### 完了済み

- [x] Docker Compose 環境構築
- [x] FastAPI バックエンド基盤
- [x] Temporal Worker 基盤
- [x] LLM クライアント（Gemini/OpenAI/Anthropic）
- [x] ツール実装（SERP, PageFetch, PDF抽出等）
- [x] Activity実装（step0〜step10）
- [x] LangGraph グラフ定義（pre_approval, post_approval）
- [x] Workflow実装（ArticleWorkflow）
- [x] テストスイート（300テスト）

### 実行テスト結果（最新）

```
smoke tests:     19/19 passed
unit tests:      300/300 passed
mypy:            Success (68 files)
ruff:            All checks passed
```

---

## 参考

- [README.md](../../README.md) - プロジェクト概要
- [TEST.md](TEST.md) - テスト戦略
- [仕様書/workflow.md](../../仕様書/workflow.md) - ワークフロー詳細
- [.claude/rules/implementation.md](../../.claude/rules/implementation.md) - 実装ルール
