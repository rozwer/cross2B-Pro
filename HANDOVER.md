# SEO Article Generator 引継書

## 1. 環境構築手順

### 前提条件
- Docker / Docker Compose がインストール済み
- Git でリポジトリをclone済み

### セットアップ

```bash
# 1. リポジトリ取得
git pull origin master

# 2. 環境変数ファイルを作成
cp .env.example .env

# 3. .env を編集（下記「必須設定」参照）

# 4. 全サービスをビルド＆起動
docker compose up -d --build

# 5. ブラウザでアクセス
open http://localhost:23000
```

### 初回以外（既にDBがある場合）

以前のバージョンで `docker compose up` したことがある場合、DBスキーマが古い可能性があります。
**DBを作り直してください**：

```bash
docker compose down -v          # volume削除（DB・MinIOデータ全消去）
docker compose up -d --build    # 再構築
```

> `init-db.sql` はPostgres初回起動時にのみ自動実行されます。
> volume を削除しない限り再実行されません。

---

## 2. 必須設定（.env ファイル）

`.env.example` をコピーした後、以下を設定してください。

### 必須

| 変数名 | 説明 | 取得方法 |
|--------|------|----------|
| `GEMINI_API_KEY` | Google Gemini API キー | [Google AI Studio](https://aistudio.google.com/apikey) |
| `SERP_API_KEY` | SERP API キー（Google検索結果取得） | [SerpApi](https://serpapi.com/) |
| `SETTINGS_ENCRYPTION_KEY` | APIキーDB保存用暗号化キー | 下記コマンドで生成 |

```bash
# SETTINGS_ENCRYPTION_KEY の生成
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

### 任意（Gemini以外のLLMを使う場合）

| 変数名 | 説明 |
|--------|------|
| `OPENAI_API_KEY` | OpenAI API キー |
| `ANTHROPIC_API_KEY` | Anthropic Claude API キー |

### Google Ads（キーワードプランナー）

検索ボリューム取得に使用。モックモードでも動作します。

| 変数名 | 説明 |
|--------|------|
| `USE_MOCK_GOOGLE_ADS` | `true`: モックデータ使用 / `false`: 実API使用 |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads 開発者トークン |
| `GOOGLE_ADS_CLIENT_ID` | OAuth クライアントID |
| `GOOGLE_ADS_CLIENT_SECRET` | OAuth クライアントシークレット |
| `GOOGLE_ADS_REFRESH_TOKEN` | OAuth リフレッシュトークン |
| `GOOGLE_ADS_CUSTOMER_ID` | Google Ads アカウントID |

> Google Ads の各キーは別途 `shared-api-keys.txt` にまとめてあります（git管理外）。

### その他はデフォルトでOK

ポート番号・DB接続情報・MinIO設定等は `.env.example` のデフォルト値で動作します。
変更不要です。

---

## 3. サービス一覧とポート

| サービス | コンテナ名 | ポート | URL |
|----------|-----------|--------|-----|
| UI（Next.js） | seo-ui | 23000 | http://localhost:23000 |
| API（FastAPI） | seo-api | 28000 | http://localhost:28000/docs |
| Worker（Temporal） | seo-worker | - | (内部通信のみ) |
| PostgreSQL | seo-postgres | 25432 | - |
| MinIO | seo-minio | 29000 / 29001 | http://localhost:29001 (Console) |
| Temporal | seo-temporal | 27233 | - |
| Temporal UI | seo-temporal-ui | 28080 | http://localhost:28080 |

---

## 4. 基本的な使い方

### 記事生成の流れ

1. **http://localhost:23000** にアクセス
2. 左メニュー「Settings」→ モデル設定を確認（デフォルト: Gemini 2.5 Pro）
3. 「新規Run」ボタン → キーワードとURL等を入力 → 「記事生成を開始」
4. ダッシュボードで進捗を確認（step0〜step12 まで自動実行）
5. 完了後「成果物」から生成記事を確認

### モデル設定について

- デフォルトモデルは **Gemini 2.5 Pro**（`docker-compose.override.yml` で設定）
- Settings画面で各ステップごとにモデルを変更可能
- **設定はブラウザのlocalStorageにキャッシュされます**
  - バックエンドのデフォルトモデルが変更された場合、自動でキャッシュが更新されます
  - 手動リセット: Settings画面の「リセット」ボタン

---

## 5. トラブルシューティング

### UIにアクセスできない

```bash
docker compose ps          # 全コンテナが running か確認
docker compose logs ui     # UIログ確認
docker compose logs api    # APIログ確認
```

### 記事生成が失敗する

```bash
# Workerログで原因確認
docker compose logs -f worker

# よくある原因:
# - GEMINI_API_KEY が未設定 or 無効
# - SERP_API_KEY が未設定（step1 で失敗）
# - モデル名が存在しない（404エラー）→ Settings画面でリセット
```

### モデルが見つからないエラー (404 NOT_FOUND)

Settings画面の「リセット」ボタンを押してください。
ブラウザの古いキャッシュが残っている場合に発生します。

### DBの状態がおかしい

```bash
docker compose down -v      # volume削除
docker compose up -d        # 再構築（init-db.sql が再実行される）
```

---

## 6. 今回の変更内容（2025/02 更新分）

### ポート変更
全サービスのポートを **2xxxx 系** に変更しました（他サービスとの競合回避）。

### localStorage キャッシュ自動修正
UIの Settings画面が、バックエンドのデフォルトモデルと localStorage のキャッシュを比較し、
古いキャッシュを自動で最新に更新するようになりました。
これにより「バックエンドのモデルを変えたのにUIが古いモデルを送り続ける」問題が解消されています。

### DB-aware LLM クライアント
Worker が DB（api_settings テーブル）に保存された API キーを優先的に使用するようになりました。
UI の Settings > APIキー 画面から設定したキーが自動で使われます。
