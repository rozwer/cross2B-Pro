# GitHub 統合ガイド

このドキュメントでは、SEO記事自動生成システムとGitHubの連携方法について説明します。

## 概要

GitHub統合により、以下のことが可能になります：

1. **成果物のバージョン管理**: 各工程の出力をGitHubリポジトリに保存
2. **Claude Code による編集**: GitHub Issue で @claude をメンションして AI 編集を依頼
3. **差分管理**: GitHub と MinIO 間の差分を検出・同期

## セットアップ手順

### 1. GitHub Personal Access Token の作成

1. GitHub にログイン
2. Settings > Developer settings > Personal access tokens > Tokens (classic)
3. "Generate new token (classic)" をクリック
4. 以下の権限を付与:
   - `repo` (Full control of private repositories)
   - `workflow` (Update GitHub Action workflows)
5. トークンを安全な場所に保存

### 2. 環境変数の設定

`.env` ファイルに以下を追加:

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

### 3. リポジトリの準備

成果物を保存するリポジトリを作成（または既存のリポジトリを使用）:

```bash
# 新規作成の場合
gh repo create my-seo-articles --private

# または UI から作成
```

### 4. Claude Code Action の設定

成果物リポジトリに Claude Code Action を設定します。

#### 4.1 ワークフローファイルの配置

`docs/templates/claude-code.yml` を対象リポジトリの `.github/workflows/` にコピー:

```bash
# 対象リポジトリで実行
mkdir -p .github/workflows
cp /path/to/claude-code.yml .github/workflows/
git add .github/workflows/claude-code.yml
git commit -m "Add Claude Code workflow"
git push
```

#### 4.2 Secrets の設定

リポジトリの Settings > Secrets and variables > Actions で以下を追加:

- `ANTHROPIC_API_KEY`: Anthropic API キー

### 5. ワークフロー開始時の設定

記事生成ワークフローを開始する際:

1. Step 6（確認画面）で GitHub リポジトリ URL を入力
2. 「アクセス確認」ボタンでアクセス権限を確認
3. または「新規リポジトリ作成」で新しいリポジトリを作成

## 使用方法

### 成果物の確認

ワークフロー実行中・完了後:

1. 成果物ページで各ステップの出力を確認
2. 「GitHub で開く」ボタンで GitHub 上のファイルを直接表示

### Claude Code による編集

1. 成果物ページで「Claude Code で編集」ボタンをクリック
2. 編集指示を入力（例: "見出しをより魅力的にしてください"）
3. Issue が自動作成され、Claude Code が編集を開始
4. 編集完了後、「差分を確認」で変更内容を確認
5. 「GitHub から同期」で MinIO に反映

### 差分管理

- **同期済み（緑）**: GitHub と MinIO が同じ内容
- **差分あり（オレンジ）**: GitHub で編集があり、同期が必要
- 警告アイコンが表示されたら「差分を確認」→「同期」で解消

## ディレクトリ構造

GitHub リポジトリ内の構造:

```
{リポジトリ}/
└── {キーワード}_{タイムスタンプ}/
    ├── .claude/
    │   └── CLAUDE.md        # Claude Code 用の指示書
    ├── step0/
    │   └── output.json      # 入力データ
    ├── step1/
    │   └── output.json      # 競合分析
    ├── step3a/
    │   └── output.json      # クエリ分析
    ...
    ├── step10/
    │   └── output.json      # 記事本文
    ├── step11/
    │   ├── output.json      # 画像メタデータ
    │   └── images/          # 生成画像
    └── step12/
        └── output.html      # WordPress HTML
```

## トラブルシューティング

### アクセス確認が失敗する

- トークンの権限を確認（`repo` 権限が必要）
- トークンの有効期限を確認
- リポジトリ URL の形式を確認（`https://github.com/owner/repo`）

### Claude Code が動作しない

- `ANTHROPIC_API_KEY` が正しく設定されているか確認
- ワークフローファイルが正しい場所にあるか確認
- Actions タブでワークフローの実行ログを確認

### 同期が失敗する

- GitHub API のレート制限に達していないか確認
- ファイルが GitHub に存在するか確認
- ネットワーク接続を確認

## API リファレンス

### エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/github/check-access` | リポジトリアクセス確認 |
| POST | `/api/github/create-repo` | 新規リポジトリ作成 |
| POST | `/api/github/create-issue` | Claude Code 用 Issue 作成 |
| GET | `/api/github/diff/{run_id}/{step}` | 差分取得 |
| POST | `/api/github/sync/{run_id}/{step}` | GitHub → MinIO 同期 |
| GET | `/api/github/sync-status/{run_id}` | 同期状態一括取得 |

## セキュリティ考慮事項

- GitHub トークンは環境変数で管理し、コードにハードコードしない
- プライベートリポジトリを推奨
- 機密情報を含むファイルは `.gitignore` に追加
- Anthropic API キーは Secrets で管理

## 関連リンク

- [Claude Code Action](https://github.com/anthropics/claude-code-action)
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
