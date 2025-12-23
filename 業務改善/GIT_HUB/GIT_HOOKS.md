# Git Hooks 設定ガイド

> プロジェクトで使用している Git hooks の一覧と機能説明

## 設定状況

```bash
# hooks パスの確認
git config core.hooksPath  # → .githooks

# 有効なフック一覧
ls -la .githooks/
```

| フック | 実行タイミング | 主な機能 |
|--------|---------------|----------|
| pre-commit | コミット前 | コード品質チェック |
| prepare-commit-msg | メッセージ編集前 | プレフィックス自動生成 |
| commit-msg | コミット確定前 | Conventional Commits 検証 |
| post-checkout | ブランチ切替後 | 依存更新通知 |
| post-merge | マージ後 | 依存自動更新・キャッシュクリア |
| pre-push | push 前 | 品質チェック・保護ブランチ |

---

## 1. pre-commit

コミット前に自動実行されるコード品質チェック。

### チェック内容

| 項目 | ツール | 動作 |
|------|--------|------|
| 秘密情報検出 | regex | APIキー等の漏洩防止 |
| Python lint | ruff check | エラー検出・自動修正 |
| Python format | ruff format | 自動整形（ステージに追加） |
| Python 型 | mypy | 型エラー検出（警告のみ） |
| TS/JS lint | oxlint | エラー検出 |
| TS/JS format | oxfmt | 自動整形（実験的） |
| JSON 検証 | python json.tool | 構文エラー検出 |
| YAML 検証 | python yaml | 構文エラー検出 |

### 検出される秘密情報パターン

- `OPENAI_API_KEY=sk-...`
- `ANTHROPIC_API_KEY=sk-ant-...`
- `GEMINI_API_KEY=...`
- `AWS_SECRET_ACCESS_KEY=...`
- `.env` ファイル（.env.example 以外）

### スキップ方法

```bash
git commit --no-verify
```

---

## 2. prepare-commit-msg

ブランチ名からコミットメッセージのプレフィックスを自動生成。

### 変換ルール

| ブランチ名 | 生成されるプレフィックス |
|------------|-------------------------|
| `feat/user-auth` | `feat(user-auth):` |
| `fix/api-timeout` | `fix(api-timeout):` |
| `hotfix/critical` | `fix(critical):` |
| `docs/readme` | `docs(readme):` |

### Issue 番号の自動追加

| ブランチ名 | フッター |
|------------|----------|
| `feat/123-user-auth` | `Refs #123` |
| `fix/issue-456-bug` | `Refs #456` |
| `bugfix/GH-789` | `Refs #789` |

### 対応する type

`feat`, `feature`, `fix`, `bugfix`, `hotfix`, `docs`, `doc`, `style`, `refactor`, `perf`, `performance`, `test`, `tests`, `build`, `ci`, `chore`, `revert`

---

## 3. commit-msg

Conventional Commits 形式を強制。

### 許可される形式

```
<type>(<scope>): <subject>

例:
feat(llm): Gemini API クライアント実装
fix(validator): JSON末尾カンマの処理修正
docs(api): エンドポイント仕様を追記
```

### 許可される type

`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

---

## 4. post-checkout

ブランチ切替後に依存関係の変更を通知。

### 通知内容

| 変更ファイル | 通知メッセージ |
|-------------|---------------|
| `pyproject.toml`, `uv.lock` | `uv sync` を実行してください |
| `package.json`, `package-lock.json` | `npm install` を実行してください |
| `.env.example` | 不足している環境変数を表示 |
| `migrations/`, `alembic/` | マイグレーション実行を促す |
| `docker-compose.yml`, `Dockerfile` | `docker compose up --build` を促す |

---

## 5. post-merge

マージ後に依存関係を自動更新し、キャッシュをクリア。

### 自動更新

| 対象 | 条件 | コマンド |
|------|------|----------|
| Python | `pyproject.toml` 変更時 | `uv sync` |
| Node.js | `apps/ui/package.json` 変更時 | `npm install` |

### キャッシュクリア

| 対象 | 条件 | 削除先 |
|------|------|--------|
| Python | `.py` 10ファイル以上変更 | `__pycache__/`, `*.pyc` |
| pytest | `tests/` 変更時 | `.pytest_cache/` |
| mypy | `.py` 変更時 | `.mypy_cache/` |
| ruff | `pyproject.toml` 変更時 | `.ruff_cache/` |
| Next.js | `apps/ui/` 変更時 | `apps/ui/.next/` |

---

## 6. pre-push

push 前の品質チェックと保護ブランチへの直接 push 防止。

### チェック内容

| 項目 | 動作 |
|------|------|
| 保護ブランチ | `main`, `master` への push をブロック |
| ブランチ命名 | 推奨形式でない場合に警告 |
| WIP 検出 | `WIP`, `fixup`, `squash` コミットを警告 |
| smoke テスト | `tests/smoke/` を実行（失敗時ブロック） |

### 推奨ブランチ命名

```
feat/<機能名>
fix/<バグ名>
hotfix/<緊急修正>
docs/<内容>
refactor/<内容>
test/<内容>
chore/<内容>
ci/<内容>
release/<バージョン>
```

### スキップ方法

```bash
# 全チェックをスキップ
git push --no-verify

# smoke テストのみスキップ
SKIP_SMOKE_TEST=1 git push
```

---

## トラブルシューティング

### hooks が実行されない

```bash
# hooks パスを確認
git config core.hooksPath

# 設定されていない場合
git config core.hooksPath .githooks

# 実行権限を確認
ls -la .githooks/
chmod +x .githooks/*
```

### 特定のチェックで失敗する

```bash
# ruff が見つからない
uv sync  # または pip install ruff

# oxlint が見つからない
bun add -g oxlint

# mypy が見つからない
uv sync  # または pip install mypy
```

### 緊急時の回避

```bash
# コミット時
git commit --no-verify -m "fix: 緊急修正"

# push 時
git push --no-verify
```

---

## カスタマイズ

### 新しいチェックを追加

`.githooks/pre-commit` を編集：

```bash
# 例: 特定ファイルの存在チェック
if [ ! -f "README.md" ]; then
    echo "README.md が見つかりません"
    HAS_ERROR=1
fi
```

### 環境変数による制御

| 変数 | 効果 |
|------|------|
| `SKIP_SMOKE_TEST=1` | smoke テストをスキップ |
| `--no-verify` | 全 hooks をスキップ |
