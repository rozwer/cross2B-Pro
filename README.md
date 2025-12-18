# SEO記事自動生成システム

SEO最適化された記事を自動生成するワークフローシステム。Temporal + LangGraph で工程管理を行い、複数のLLM（Gemini/OpenAI/Anthropic）を活用して高品質な記事を生成します。

## 特徴

- **マルチLLM対応**: Gemini、OpenAI、Anthropic を工程に応じて使い分け
- **Temporal + LangGraph**: 堅牢なワークフロー管理と状態永続化
- **Human-in-the-loop**: 工程3完了後に人間の承認フローを挟む
- **マルチテナント**: 顧客別DB分離でセキュアな運用
- **フォールバック禁止**: 自動切替を許容せず、失敗は明示的にエラー化

## アーキテクチャ

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Next.js   │────▶│   FastAPI   │────▶│  Temporal   │
│     UI      │◀────│     API     │◀────│   Worker    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  PostgreSQL │     │    MinIO    │
                    │  (顧客別DB) │     │  (Storage)  │
                    └─────────────┘     └─────────────┘
```

## ワークフロー概要

```
【半自動フロー】人間確認あり
工程-1 → 工程0 → 工程1 → 工程2 → 工程3A/3B/3C（並列）
                                    ↓
                              [承認待ち]
                                    ↓
【全自動フロー】一気通貫実行
工程4 → 工程5 → 工程6 → 工程6.5 → 工程7A → 工程7B → 工程8 → 工程9 → 工程10
```

詳細は [仕様書/workflow.md](仕様書/workflow.md) を参照。

## ディレクトリ構成

```
.
├── apps/
│   ├── api/           # FastAPI バックエンド
│   │   ├── core/      # 共通型定義（State, Context, Error）
│   │   ├── db/        # データベース（マルチテナント対応）
│   │   ├── llm/       # LLMクライアント（Gemini/OpenAI/Anthropic）
│   │   ├── storage/   # Artifact Store（MinIO）
│   │   ├── tools/     # 外部ツール（SERP, PageFetch等）
│   │   ├── prompts/   # プロンプト管理
│   │   ├── observability/ # ログ・イベント
│   │   └── validation/    # JSON/CSV検証
│   ├── worker/        # Temporal Worker
│   │   ├── workflows/ # Workflow定義
│   │   ├── activities/# Activity実装
│   │   └── graphs/    # LangGraph定義
│   └── ui/            # Next.js フロントエンド
├── docs/
│   ├── guides/        # RUN.md, TEST.md 等の実行ガイド
│   ├── prompts/       # プロンプト設計ドキュメント
│   └── summaries/     # フェーズ完了サマリー
├── scripts/           # ユーティリティスクリプト
├── tests/             # テストスイート
└── 仕様書/            # 設計ドキュメント
```

## 必要条件

| 項目           | 最小バージョン | 確認コマンド             |
| -------------- | -------------- | ------------------------ |
| Docker         | 24.0+          | `docker --version`       |
| Docker Compose | 2.20+          | `docker compose version` |
| Python         | 3.11+          | `python3 --version`      |
| Node.js        | 20+            | `node --version`         |
| uv             | 0.4+           | `uv --version`           |

### 環境確認

```bash
# 全チェック（推奨）
./scripts/check-env.sh

# 最小限チェック
./scripts/check-env.sh --quick

# 個別チェック
./scripts/check-env.sh --docker   # Docker関連のみ
./scripts/check-env.sh --python   # Python関連のみ
./scripts/check-env.sh --node     # Node.js関連のみ
```

## クイックスタート（Docker Compose）

```bash
# 1. 環境確認
./scripts/check-env.sh

# 2. 環境変数を設定
cp .env.example .env
# .env を編集してAPIキーを設定（少なくとも1つのLLM APIキーが必要）

# 3. 全サービスを起動
./scripts/bootstrap.sh

# 4. アクセス
# - UI:          http://localhost:3000
# - API:         http://localhost:8000
# - Temporal UI: http://localhost:8080
# - MinIO:       http://localhost:9001
```

### サービス管理

```bash
# 停止
docker compose down

# ログ確認
docker compose logs -f

# 特定サービスのログ
docker compose logs -f api worker

# 完全リセット（データ削除）
./scripts/reset.sh
```

### Docker Compose サービス

| サービス    | ポート     | 説明                    |
| ----------- | ---------- | ----------------------- |
| postgres    | 5432       | PostgreSQL データベース |
| minio       | 9000, 9001 | オブジェクトストレージ  |
| temporal    | 7233       | ワークフローエンジン    |
| temporal-ui | 8080       | Temporal 管理UI         |
| api         | 8000       | FastAPI バックエンド    |
| worker      | -          | Temporal Worker         |
| ui          | 3000       | Next.js フロントエンド  |

## 手動セットアップ（開発用）

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd 案件
```

### 2. 環境変数の設定

```bash
cp .env.example .env
# .env を編集してAPIキーを設定
```

必須の環境変数:

| 変数名                | 説明                   |
| --------------------- | ---------------------- |
| `GEMINI_API_KEY`      | Google Gemini API キー |
| `OPENAI_API_KEY`      | OpenAI API キー        |
| `ANTHROPIC_API_KEY`   | Anthropic API キー     |
| `POSTGRES_PASSWORD`   | PostgreSQL パスワード  |
| `MINIO_ROOT_PASSWORD` | MinIO ルートパスワード |

※ LLM APIキーは少なくとも1つ設定するか、`USE_MOCK_LLM=true` でモックモードを使用

### 3. Python環境のセットアップ（uv）

[uv](https://docs.astral.sh/uv/) を使用してパッケージ管理を行います。

```bash
# uv のインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存関係のインストール（.venv が自動作成されます）
uv sync
```

**よく使うコマンド:**

```bash
uv sync              # 依存関係をインストール/同期
uv add <package>     # パッケージを追加
uv remove <package>  # パッケージを削除
uv run <command>     # 仮想環境でコマンドを実行
uv lock              # lockファイルを更新
```

### 4. フロントエンドのセットアップ

```bash
cd apps/ui
npm install
cd ../..
```

### 5. インフラの起動（ローカル）

```bash
# PostgreSQL, MinIO, Temporal のみ起動
docker compose up -d postgres minio temporal temporal-ui
```

### 6. データベースのマイグレーション

```bash
uv run alembic upgrade head
```

## 開発

### Docker Compose を使用した開発

```bash
# 全サービス起動
docker compose up -d

# アプリケーションのみ再ビルド
docker compose build api worker ui
docker compose up -d api worker ui
```

### 手動での開発（インフラはDocker）

```bash
# インフラのみ起動
docker compose up -d postgres minio temporal temporal-ui

# API サーバー
uv run uvicorn apps.api.main:app --reload --port 8000

# Temporal Worker
uv run python -m apps.worker.main

# フロントエンド
cd apps/ui && npm run dev
```

### LangGraph Studio での開発

```bash
cd langgraph-example
langgraph dev
```

## テスト

### 環境確認 + smoke テスト（推奨）

```bash
# 環境確認 + smoke テスト一括実行
./scripts/check-env.sh --quick && uv run pytest tests/smoke/ -v --tb=short
```

### テストコマンド

```bash
# 環境確認
./scripts/check-env.sh

# smoke テスト（依存・構文・起動チェック）
uv run pytest tests/smoke/ -v

# ユニットテスト
uv run pytest tests/unit/ -v

# 統合テスト（Docker必須）
uv run pytest tests/integration/ -v

# E2Eテスト（全サービス起動必須）
uv run pytest tests/e2e/ -v

# 型チェック
uv run mypy apps/ --ignore-missing-imports

# リント
uv run ruff check apps/
```

### テストレベル

| レベル      | 対象            | 実行タイミング | コマンド                              |
| ----------- | --------------- | -------------- | ------------------------------------- |
| env-check   | 環境要件        | 作業開始前     | `./scripts/check-env.sh`              |
| smoke       | 依存/構文/起動  | commit前       | `uv run pytest tests/smoke/ -v`       |
| unit        | 関数単位        | push前         | `uv run pytest tests/unit/ -v`        |
| integration | API/DB/Temporal | PR前           | `uv run pytest tests/integration/ -v` |
| e2e         | 全工程通し      | merge前        | `uv run pytest tests/e2e/ -v`         |

## スクリプト一覧

| スクリプト               | 説明                       |
| ------------------------ | -------------------------- |
| `./scripts/check-env.sh` | 環境要件の確認             |
| `./scripts/bootstrap.sh` | 初期化・全サービス起動     |
| `./scripts/reset.sh`     | 完全リセット（データ削除） |

## スラッシュコマンド

開発時に使用できるClaude Codeコマンド:

| コマンド                | 説明                 |
| ----------------------- | -------------------- |
| `/dev:up`               | ローカル環境起動     |
| `/dev:down`             | ローカル環境停止     |
| `/dev:smoke`            | smoke テスト実行     |
| `/workflow:new-run`     | 新規ワークフロー開始 |
| `/workflow:approve-run` | ワークフロー承認     |

## トラブルシューティング

| 症状                  | 原因                   | 解決策                                 |
| --------------------- | ---------------------- | -------------------------------------- |
| `ModuleNotFoundError` | 依存関係未インストール | `uv sync`                              |
| Docker接続エラー      | Docker未起動           | Docker Desktop を起動                  |
| ポート競合            | 既存プロセス           | `.env` でポート変更 or `lsof -i :PORT` |
| 型エラー              | mypy 設定              | `--ignore-missing-imports` を使用      |
| インポートエラー      | パス設定               | `PYTHONPATH=.` を設定                  |

詳細は [.claude/rules/implementation.md](.claude/rules/implementation.md#トラブルシューティング) を参照。

## 禁止事項

このプロジェクトでは以下を**禁止**しています:

- 別モデル/別プロバイダへの自動切替（フォールバック）
- 壊れた出力の黙った採用
- prompt pack 未指定での自動実行

詳細は [.claude/CLAUDE.md](.claude/CLAUDE.md) を参照。

## ドキュメント

| ドキュメント                                                       | 説明               |
| ------------------------------------------------------------------ | ------------------ |
| [仕様書/ROADMAP.md](仕様書/ROADMAP.md)                             | 実装計画           |
| [仕様書/workflow.md](仕様書/workflow.md)                           | ワークフロー詳細   |
| [仕様書/PARALLEL_DEV_GUIDE.md](仕様書/PARALLEL_DEV_GUIDE.md)       | 並列開発ガイド     |
| [仕様書/backend/](仕様書/backend/)                                 | バックエンド仕様   |
| [仕様書/frontend/](仕様書/frontend/)                               | フロントエンド仕様 |
| [.claude/rules/implementation.md](.claude/rules/implementation.md) | 実装ルール         |

## ライセンス

Private
