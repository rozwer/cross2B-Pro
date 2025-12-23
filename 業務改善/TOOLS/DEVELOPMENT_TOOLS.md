# 開発環境ツール一覧

> 本プロジェクトで使用しているツールのバージョンと用途

## システム環境

| カテゴリ | ツール | バージョン | 用途 |
|---------|--------|------------|------|
| OS | WSL2 (Linux) | 5.15.167.4 | Windows上のLinux開発環境 |
| VCS | Git | 2.43.0 | バージョン管理 |

---

## 言語ランタイム

| ツール | バージョン | 最小要件 | 用途 |
|--------|------------|----------|------|
| Python | 3.12.3 | 3.11+ | Backend (FastAPI, Temporal Worker, LangGraph) |
| Node.js | 22.21.1 | 20+ | Frontend (Next.js) |
| npm | 10.9.4 | - | Node.jsパッケージ管理 |

---

## パッケージ管理

| ツール | バージョン | 用途 | 備考 |
|--------|------------|------|------|
| uv | 0.9.17 | Python依存管理 | **推奨**（pip/poetryより高速） |
| pip | 24.0 | Python依存管理 | 非推奨（uvを使用） |

---

## コンテナ・インフラ

| ツール | バージョン | 最小要件 | 用途 |
|--------|------------|----------|------|
| Docker | 27.5.1 | 24.0+ | コンテナ実行 |
| Docker Compose | 2.37.1 | 2.20+ | マルチコンテナ管理 |
| lazydocker | 0.24.2 | - | TUI形式のDocker管理 |

### lazydocker の使い方

```bash
# 起動
lazydocker

# キーバインド
# - j/k: 上下移動
# - Enter: 選択
# - l: ログ表示
# - d: コンテナ削除
# - s: 停止
# - r: 再起動
# - q: 終了
```

---

## ワークフロー・DB

| ツール | バージョン | 用途 |
|--------|------------|------|
| Temporal CLI | 1.5.1 | Temporalワークフロー操作・デバッグ |
| psql | 16.11 | PostgreSQL接続・クエリ実行 |

### Temporal CLI の使い方

```bash
# ワークフロー一覧
temporal workflow list

# ワークフロー詳細
temporal workflow describe --workflow-id <id>

# ワークフロー履歴
temporal workflow show --workflow-id <id>

# シグナル送信
temporal workflow signal --workflow-id <id> --name <signal-name>

# ワークフロー終了
temporal workflow terminate --workflow-id <id>
```

### psql の使い方

```bash
# Docker内のPostgreSQLに接続
docker compose exec postgres psql -U seo -d seo_articles

# ローカルから接続（ポートフォワード時）
psql -h localhost -p 5432 -U seo -d seo_articles

# よく使うコマンド
# \dt          テーブル一覧
# \d <table>   テーブル構造
# \q           終了
```

---

## コード品質

| ツール | バージョン | 用途 | 実行方法 |
|--------|------------|------|----------|
| mypy | 1.19.1 | Python型チェック | `uv run mypy apps/` |
| ruff | 0.14.9 | Pythonリンター/フォーマッター | `uv run ruff check apps/` |
| pytest | 9.0.2 | Pythonテスト | `uv run pytest tests/` |
| TypeScript | 5.7.2 | 型付きJavaScript | `npx tsc --noEmit` |
| ESLint | 8.57.1 | JS/TSリンター | `npm run lint` |
| oxlint | - | 高速JS/TSリンター | `bunx oxlint` |
| oxfmt | - | JS/TSフォーマッター | `bunx oxfmt` (pre-commit) |

---

## CLI ツール

| ツール | バージョン | 用途 |
|--------|------------|------|
| gh | 2.81.0 | GitHub CLI（PR/Issue操作） |
| jq | 1.7 | JSONパーサー |
| curl | 8.5.0 | HTTP通信 |
| wget | 1.21.4 | ファイルダウンロード |
| direnv | 2.32.1 | ディレクトリ別環境変数管理 |

### direnv の使い方

```bash
# .envrc ファイルを作成
echo 'export MY_VAR=value' > .envrc

# 許可（初回のみ必要）
direnv allow

# ディレクトリに入ると自動で環境変数がロードされる
cd /path/to/project
# direnv: loading .envrc
```

### gh CLI の使い方

```bash
# PR作成
gh pr create --title "feat: 新機能" --body "説明"

# PR一覧
gh pr list

# Issue作成
gh issue create --title "バグ報告" --body "詳細"

# PRレビュー
gh pr review --approve
gh pr review --request-changes --body "修正してください"
```

---

## Docker Compose サービス

| サービス | ポート | 用途 |
|----------|--------|------|
| postgres | 5432 | PostgreSQL データベース |
| minio | 9000, 9001 | オブジェクトストレージ（S3互換） |
| temporal | 7233 | ワークフローエンジン |
| temporal-ui | 8080 | Temporal管理UI |
| api | 8000 | FastAPI バックエンド |
| worker | - | Temporal Worker |
| ui | 3000 | Next.js フロントエンド |

---

## 主要なPython依存

| パッケージ | 用途 |
|-----------|------|
| FastAPI | REST API フレームワーク |
| Pydantic | データバリデーション |
| SQLAlchemy | ORM |
| asyncpg | PostgreSQL非同期ドライバ |
| Alembic | DBマイグレーション |
| temporalio | Temporal SDK |
| langgraph | LLMワークフロー |
| langchain-* | LLM統合 |
| minio | オブジェクトストレージ |
| google-genai | Gemini API |
| anthropic | Claude API |
| openai | OpenAI API |

---

## 主要なNode.js依存

| パッケージ | 用途 |
|-----------|------|
| Next.js | Reactフレームワーク |
| React | UIライブラリ |
| @xyflow/react | ワークフロー可視化 |
| Tailwind CSS | CSSフレームワーク |
| Zod | スキーマバリデーション |
| react-hook-form | フォーム管理 |
| lucide-react | アイコン |

---

## クイックリファレンス

### 環境確認

```bash
# 全ツールバージョン確認
python3 --version && node --version && docker --version && uv --version

# Docker状態確認
lazydocker  # または docker compose ps

# Temporal状態確認
temporal workflow list
```

### 開発起動

```bash
# インフラ起動
docker compose up -d postgres minio temporal temporal-ui

# 全サービス起動
docker compose up -d

# ログ確認
docker compose logs -f api worker
```

### テスト実行

```bash
# smoke テスト
uv run pytest tests/smoke/ -v

# 単体テスト
uv run pytest tests/unit/ -v

# 型チェック
uv run mypy apps/

# リント
uv run ruff check apps/
```
