# Claude Setup Instructions

> **このファイルはClaude（AI）がプロジェクトをセットアップするための指示書です。**
> 人間が読む必要はありません。ユーザーから「このプロジェクトのセットアップをお願い」と依頼されたとき、このファイルの手順に従ってください。

---

## 前提条件の確認

セットアップを開始する前に、以下を確認してください:

1. **Docker Desktop が起動しているか** — `docker info` を実行して確認
2. **Docker Compose が利用可能か** — `docker compose version` を実行して確認
3. **プロジェクトディレクトリにいるか** — `docker-compose.yml` が存在する場所

いずれかが失敗した場合は、ユーザーに Docker Desktop の起動を依頼してください。

---

## セットアップ手順

### Step 1: 環境変数ファイルの作成

```bash
cp .env.example .env
```

`.env.example` を `.env` にコピーします。既に `.env` が存在する場合はスキップし、ユーザーに上書きするか確認してください。

### Step 2: APIキーの設定

ユーザーにAPIキーを聞いて、`.env` ファイルに設定します。

**必須のキー（最低1つ）:**

| 変数名 | 用途 |
|--------|------|
| `GEMINI_API_KEY` | 工程0, 1.5, 2, 3A-C, 3.5, 5, 7B, 8で使用 |
| `ANTHROPIC_API_KEY` | 工程4, 6, 6.5, 7A, 9, 10, 12で使用 |
| `OPENAI_API_KEY` | バックアップ/代替用 |

**オプションのキー:**

| 変数名 | 用途 |
|--------|------|
| `SERP_API_KEY` | Google検索結果取得（工程1, 5, 8） |
| `TAVILY_API_KEY` | Web検索代替 |
| `NANO_BANANA_API_KEY` | 画像生成（工程11） |

ユーザーがキーを提供しない項目は空のままで構いません。

**設定方法**: `.env` ファイル内の該当する行に値を設定してください。例:
```
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 3: その他の設定（変更不要）

以下の設定はデフォルト値のまま動作します。ユーザーから特に指示がない限り変更しないでください:

- `POSTGRES_*` — データベース設定
- `MINIO_*` — ストレージ設定
- `TEMPORAL_*` — ワークフローエンジン設定
- `API_*`, `UI_*` — サーバー設定

### Step 4: システム起動

```bash
./納品用_scripts/bootstrap.sh
```

このスクリプトが以下を実行します:
1. Docker イメージのビルド
2. データベースの初期化
3. 全サービスの起動

**初回は5〜10分かかります。** スクリプトの出力を監視し、エラーがあれば対処してください。

### Step 5: ヘルスチェック

起動完了後、以下を実行して全サービスが正常に動作していることを確認:

```bash
# 各サービスの状態確認
docker compose ps

# API ヘルスチェック
curl -s http://localhost:8000/health | python3 -m json.tool

# UI が応答するか確認
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

**正常な状態:**
- `docker compose ps` — 全サービスが `Up` または `running`
- `/health` — `{"status": "ok"}` または類似のレスポンス
- UI — HTTPステータス `200`

### Step 6: ユーザーへの報告

セットアップ完了後、以下をユーザーに伝えてください:

```
セットアップが完了しました。

メイン画面: http://localhost:3000
API:        http://localhost:8000
Temporal:   http://localhost:8080
MinIO:      http://localhost:9001

設定したAPIキー:
- Gemini: ✅ / ❌
- Anthropic: ✅ / ❌
- OpenAI: ✅ / ❌
- SERP: ✅ / ❌

※ APIキーはWeb画面（設定 → APIキー）からも変更できます。
```

---

## トラブルシューティング

### ポート競合

`port already in use` エラーが出た場合:

```bash
# 使用中のプロセスを確認
lsof -i :3000  # UI
lsof -i :8000  # API
lsof -i :5432  # PostgreSQL
```

ユーザーに該当プロセスの停止を提案するか、`.env` でポート番号を変更してください。

### コンテナが起動しない

```bash
# ログを確認
docker compose logs api
docker compose logs worker
docker compose logs postgres
```

よくある原因:
- **postgres**: 初回起動時のDB初期化に時間がかかる（再度 `docker compose up -d` で解決することが多い）
- **api**: `ModuleNotFoundError` → Docker イメージの再ビルドが必要 `docker compose build api`
- **worker**: Temporal への接続待ち → Temporal コンテナが起動するまで自動リトライ

### データの完全リセット

```bash
./納品用_scripts/reset.sh
```

これにより全データ（DB, MinIO, Temporal）が削除されます。実行前にユーザーの確認を取ってください。

---

## プロジェクト構成（参考）

```
apps/
├── api/           # FastAPI バックエンド（Python）
│   ├── routers/   # APIエンドポイント
│   ├── llm/       # LLMクライアント（Gemini/OpenAI/Anthropic）
│   ├── storage/   # MinIO ストレージ
│   ├── tools/     # 外部ツール（SERP, Web取得等）
│   └── prompts/   # プロンプトテンプレート
├── worker/        # Temporal Worker（ワークフロー実行）
│   ├── workflows/ # ワークフロー定義
│   ├── activities/# 各工程の実装
│   └── graphs/    # LangGraph 定義
└── ui/            # Next.js フロントエンド
    ├── src/app/   # ページ
    └── src/components/ # UIコンポーネント
```

## Docker Compose サービス一覧

| サービス名 | ポート | 役割 |
|-----------|--------|------|
| seo-postgres | 5432 | データベース |
| seo-minio | 9000, 9001 | ファイルストレージ |
| seo-temporal | 7233 | ワークフローエンジン |
| seo-temporal-ui | 8080 | Temporal管理画面 |
| seo-api | 8000 | APIサーバー |
| seo-worker | - | ワークフロー実行 |
| seo-ui | 3000 | フロントエンド |
