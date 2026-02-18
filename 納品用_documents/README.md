# SEO記事自動生成システム セットアップガイド

> このシステムは、AIを活用してSEO最適化された記事を自動生成するワークフローシステムです。

---

## 必要なもの

| 項目 | 説明 |
|------|------|
| **Docker Desktop** | [ダウンロード](https://www.docker.com/products/docker-desktop/) して起動しておく |
| **LLM APIキー** | 下記「APIキーの取得」を参照（最低1つ必要） |

> Python, Node.js 等の開発ツールは**不要**です。すべてDockerコンテナ内で動作します。

---

## セットアップ手順

### 1. Docker Desktop を起動する

Docker Desktop アプリを起動し、画面左下が「Engine running」（緑色）になっていることを確認してください。

### 2. 環境変数ファイルを作成する

プロジェクトフォルダ直下に `.env` ファイルを作成します。
`.env.example` をコピーして編集してください。

```bash
cp .env.example .env
```

最低限設定が必要な項目:

| 変数名 | 説明 | 取得方法 |
|--------|------|----------|
| `GEMINI_API_KEY` | Google Gemini API キー | [Google AI Studio](https://aistudio.google.com/apikey) で発行 |
| `ANTHROPIC_API_KEY` | Anthropic Claude API キー | [Anthropic Console](https://console.anthropic.com/) で発行 |
| `OPENAI_API_KEY` | OpenAI API キー | [OpenAI Platform](https://platform.openai.com/api-keys) で発行 |

> **補足**: 3つすべて設定するのが推奨ですが、工程によって使うAIが異なるため、使いたい工程に対応するキーだけでも動作します。

#### オプションのAPIキー

| 変数名 | 説明 | 取得方法 |
|--------|------|----------|
| `SERP_API_KEY` | Google検索結果の取得（工程1, 5, 8で使用） | [SerpApi](https://serpapi.com/) |
| `TAVILY_API_KEY` | Web検索（工程5, 8で使用） | [Tavily](https://tavily.com/) |
| `NANO_BANANA_API_KEY` | 画像生成（工程11で使用） | [NanoBanana](https://www.nanobanana.com/) |

#### Google Ads API（キーワード調査、オプション）

キーワードプランナーを使った検索ボリューム・関連キーワード取得に使います。
設定しない場合は `USE_MOCK_GOOGLE_ADS=true`（デフォルト）でモックデータが使われます。

| 変数名 | 取得方法 |
|--------|----------|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | [Google Ads API](https://developers.google.com/google-ads/api/docs/get-started/dev-token) |
| `GOOGLE_ADS_CLIENT_ID` | Google Cloud Console > APIs & Services > Credentials |
| `GOOGLE_ADS_CLIENT_SECRET` | 同上 |
| `GOOGLE_ADS_REFRESH_TOKEN` | `python scripts/google_ads_auth.py` で生成 |
| `GOOGLE_ADS_CUSTOMER_ID` | Google Ads アカウント番号 |

### 3. システムを起動する

```bash
./納品用_scripts/bootstrap.sh
```

初回は Docker イメージのビルドに数分かかります。

### 4. アクセスする

| 画面 | URL | 説明 |
|------|-----|------|
| **メイン画面** | http://localhost:3000 | 記事生成のダッシュボード |
| API | http://localhost:8000 | バックエンドAPI |
| Temporal UI | http://localhost:8080 | ワークフロー管理画面 |
| MinIO | http://localhost:9001 | ファイルストレージ管理画面 |

---

## 基本操作

### システムの停止

```bash
docker compose down
```

### システムの完全リセット（データ削除）

```bash
./納品用_scripts/reset.sh
```

### ログの確認

```bash
docker compose logs -f          # 全サービス
docker compose logs -f api      # APIのみ
docker compose logs -f worker   # Workerのみ
```

---

## APIキーの取得方法

### Gemini API キー（推奨: 最初に設定）

1. [Google AI Studio](https://aistudio.google.com/apikey) にアクセス
2. Google アカウントでログイン
3. 「Get API key」→「Create API key」をクリック
4. 表示されたキーをコピーし、`.env` の `GEMINI_API_KEY=` に貼り付け

### Anthropic API キー

1. [Anthropic Console](https://console.anthropic.com/) にアクセス
2. アカウントを作成しログイン
3. Settings → API Keys → 「Create Key」をクリック
4. 表示されたキーをコピーし、`.env` の `ANTHROPIC_API_KEY=` に貼り付け

### OpenAI API キー

1. [OpenAI Platform](https://platform.openai.com/api-keys) にアクセス
2. アカウントを作成しログイン
3. 「+ Create new secret key」をクリック
4. 表示されたキーをコピーし、`.env` の `OPENAI_API_KEY=` に貼り付け

### SERP API キー

1. [SerpApi](https://serpapi.com/) にアクセス
2. アカウントを作成（無料プランあり: 月100回まで）
3. Dashboard → API Key をコピー
4. `.env` の `SERP_API_KEY=` に貼り付け

> **注**: APIキーは `.env` ファイルに設定する方法の他に、起動後に Web UI の「設定 → APIキー」タブからも設定できます。Web UI から設定したキーが優先されます。

---

## Claude（AI）にセットアップを頼む方法

このシステムの環境構築は、Claude Code（AIアシスタント）に依頼することもできます。

### 前提

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) がインストールされていること
- Docker Desktop が起動していること

### 頼み方

Claude Code を起動し、プロジェクトフォルダで以下のように伝えてください:

```
このプロジェクトのセットアップをお願いします。
納品用_documents/CLAUDE_SETUP.md を読んで、手順に従ってください。
```

Claude が以下を自動で行います:
1. `.env.example` を `.env` にコピー
2. 指定されたAPIキーを設定（キーを伝える必要があります）
3. `bootstrap.sh` を実行してシステムを起動
4. 正常起動の確認（ヘルスチェック）

### その他の依頼例

| やりたいこと | 伝え方 |
|-------------|--------|
| APIキーを変更したい | 「.envのGEMINI_API_KEYを `xxx` に変更して、apiコンテナを再起動して」 |
| システムが動かない | 「docker compose logs を確認して、何が問題か教えて」 |
| データをリセットしたい | 「reset.sh を実行して」 |
| 特定のサービスだけ再起動 | 「workerコンテナだけ再起動して」 |

---

## トラブルシューティング

| 症状 | 原因 | 解決策 |
|------|------|--------|
| 画面が表示されない | Docker未起動 | Docker Desktop を起動する |
| 「port already in use」 | ポート競合 | 別のアプリが同じポートを使用中。停止するか `.env` でポート番号を変更 |
| 記事生成が途中で止まる | APIキー未設定 or 残高不足 | 設定画面でAPIキーの接続テストを実行 |
| 「connection refused」 | サービス起動中 | `bootstrap.sh` 完了まで待つ（初回は数分） |

---

## 各画面の操作方法

詳しい画面操作は `説明書/` フォルダ内のガイドを参照してください:

| ファイル | 内容 |
|----------|------|
| [01_ダッシュボード.md](説明書/01_ダッシュボード.md) | トップ画面の見方 |
| [02_新規記事作成.md](説明書/02_新規記事作成.md) | 記事作成ウィザードの使い方 |
| [03_ワークフロー進捗.md](説明書/03_ワークフロー進捗.md) | 工程の進捗確認と承認 |
| [04_成果物閲覧.md](説明書/04_成果物閲覧.md) | 完成した記事の閲覧 |
| [05_設定画面.md](説明書/05_設定画面.md) | モデル・プロンプト・APIキーの設定 |
