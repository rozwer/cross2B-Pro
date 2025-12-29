# readme-generator

> プロジェクトの README.md を自動生成・更新する subagent。
> 技術スタック、構造、使用方法を正確に反映したドキュメントを生成。

---

## 役割

1. プロジェクト構造の解析（package.json / pyproject.toml / docker-compose.yml）
2. 既存 README の差分更新または新規作成
3. セクション別のコンテンツ生成
4. レビュー用 diff 生成
5. 品質検証（リンク切れ、技術スタック整合性）

---

## 入力

```yaml
target: プロジェクトルート or サブディレクトリ
sections:
  - overview      # プロジェクト概要
  - quickstart    # クイックスタート
  - structure     # ディレクトリ構造
  - usage         # 使用方法
  - contributing  # コントリビュートガイド
existing_readme: 既存 README のパス（オプション）
options:
  include_badges: true | false      # バッジ表示（デフォルト: true）
  max_depth: 3                      # ディレクトリツリー深度（デフォルト: 3）
  include_toc: true | false         # 目次生成（デフォルト: true）
```

---

## 出力

```yaml
status: completed | needs_review | blocked
readme_content: |
  生成された README.md 内容（Markdown形式）
changes:
  - section: overview
    type: added | updated | removed
    reason: "プロジェクト説明を技術スタック情報から更新"
  - section: quickstart
    type: updated
    reason: "Docker Compose 起動コマンドを追加"
metadata:
  tech_stack:
    - Python 3.11+
    - FastAPI
    - Next.js
    - Temporal
    - PostgreSQL
  main_files:
    - pyproject.toml
    - package.json
    - docker-compose.yml
next_steps:
  - 生成内容のレビュー
  - README.md への書き込み（ユーザー承認後）
```

---

## フロー

```
入力: target + sections + existing_readme
    |
1. プロジェクト構造解析
    ├─ package.json 解析（name, version, scripts, dependencies）
    ├─ pyproject.toml 解析（name, version, dependencies）
    ├─ docker-compose.yml 解析（services, ports）
    ├─ ディレクトリ構造取得（tree コマンド相当）
    └─ 主要ファイル特定（README, LICENSE, CHANGELOG等）
    |
2. 既存 README チェック
    ├─ 既存あり → 差分更新モード
    │   ├─ セクション単位で解析
    │   ├─ 更新が必要なセクション特定
    │   └─ 変更なしセクションは維持
    └─ 既存なし → 新規作成モード
        └─ 全セクションを新規生成
    |
3. セクション生成
    ├─ overview: プロジェクト名、説明、技術スタック、バッジ
    ├─ quickstart: 前提条件、インストール、起動コマンド
    ├─ structure: ディレクトリツリー（max_depth制限）
    ├─ usage: 主要な使用方法、API例、CLI例
    └─ contributing: PR フロー、コード規約、テスト方法
    |
4. レビュー用 diff 生成（既存ありの場合）
    ├─ before/after を明示
    ├─ 変更セクションのハイライト
    └─ 変更理由を説明
    |
5. 品質検証
    ├─ 技術スタックが正確か
    ├─ クイックスタートコマンドが有効か
    ├─ ディレクトリ構造が最新か
    └─ 内部リンクが有効か
    |
出力: readme_content + changes + metadata
```

---

## セクション生成テンプレート

### overview セクション

```markdown
# {project_name}

{badges}

{description}

## 技術スタック

| カテゴリ | 技術 |
|----------|------|
| Backend | {backend_stack} |
| Frontend | {frontend_stack} |
| Database | {database} |
| Infrastructure | {infrastructure} |
```

### quickstart セクション

```markdown
## クイックスタート

### 前提条件

- {prerequisites}

### インストール

```bash
# リポジトリクローン
git clone {repo_url}
cd {project_dir}

# 依存関係インストール
{install_commands}
```

### 起動

```bash
{start_commands}
```
```

### structure セクション

```markdown
## ディレクトリ構造

```
{project_name}/
├── {dir1}/           # {description1}
│   ├── {subdir1}/    # {subdesc1}
│   └── {subdir2}/    # {subdesc2}
├── {dir2}/           # {description2}
└── {dir3}/           # {description3}
```
```

### usage セクション

```markdown
## 使用方法

### 基本操作

{basic_usage}

### API

{api_examples}

### CLI

{cli_examples}
```

### contributing セクション

```markdown
## コントリビュート

### 開発フロー

1. フォーク & クローン
2. ブランチ作成: `git checkout -b feat/xxx`
3. 実装 & テスト
4. プルリクエスト

### コード規約

{code_conventions}

### テスト

```bash
{test_commands}
```
```

---

## 解析ロジック

### package.json 解析

```yaml
抽出項目:
  name: プロジェクト名
  version: バージョン
  description: 説明
  scripts:
    dev: 開発起動コマンド
    build: ビルドコマンド
    test: テストコマンド
    start: 本番起動コマンド
  dependencies: 主要依存関係
  devDependencies: 開発依存関係
```

### pyproject.toml 解析

```yaml
抽出項目:
  project.name: プロジェクト名
  project.version: バージョン
  project.description: 説明
  project.dependencies: 主要依存関係
  tool.pytest: テスト設定
  tool.ruff: リンター設定
  tool.mypy: 型チェック設定
```

### docker-compose.yml 解析

```yaml
抽出項目:
  services: サービス一覧
    name: サービス名
    ports: 公開ポート
    depends_on: 依存サービス
  volumes: ボリューム設定
```

### ディレクトリ構造取得

```yaml
設定:
  max_depth: 3             # デフォルト深度
  exclude:
    - node_modules/
    - .venv/
    - __pycache__/
    - .git/
    - .DS_Store
    - "*.pyc"
  include_descriptions: true  # 主要ディレクトリの説明を付与
```

---

## 差分更新ロジック

### セクション識別

```yaml
パターン:
  overview: "^# " で始まる最初のセクション
  quickstart: "## クイックスタート" or "## Quick Start" or "## Getting Started"
  structure: "## ディレクトリ" or "## Directory" or "## Structure" or "## Project Structure"
  usage: "## 使用方法" or "## Usage"
  contributing: "## コントリビュート" or "## Contributing"
```

### 更新判定

```yaml
更新トリガー:
  overview:
    - package.json/pyproject.toml のバージョン変更
    - 技術スタック変更
  quickstart:
    - scripts 変更
    - docker-compose.yml 変更
  structure:
    - ディレクトリ追加/削除
    - 主要ファイル追加/削除
  usage:
    - API 変更
    - CLI 変更
  contributing:
    - テストコマンド変更
    - リンター設定変更
```

---

## 品質チェック項目

### 技術スタック検証

```yaml
checks:
  - package.json の dependencies と README の記述が一致
  - pyproject.toml の dependencies と README の記述が一致
  - docker-compose.yml の services と README の記述が一致
```

### クイックスタート検証

```yaml
checks:
  - インストールコマンドが有効（npm/uv/pip）
  - 起動コマンドが package.json/pyproject.toml に存在
  - 前提条件のバージョンが正確
```

### ディレクトリ構造検証

```yaml
checks:
  - 記載ディレクトリが実在
  - 削除されたディレクトリが含まれていない
  - 新規追加ディレクトリが反映されている
```

### リンク検証

```yaml
checks:
  - 内部リンク: ファイル存在確認
  - 相対パス: 正しいパス指定
  - アンカーリンク: セクション存在確認
```

---

## 参照ファイル

| ファイル | 用途 |
|---------|------|
| `package.json` | Node.js プロジェクト情報 |
| `pyproject.toml` | Python プロジェクト情報 |
| `docker-compose.yml` | Docker サービス情報 |
| `仕様書/ROADMAP.md` | 実装計画参照 |
| 既存 `README.md` | 差分更新のベース |
| `.gitignore` | 除外パターン参照 |

---

## 出力例

### 新規作成の場合

```yaml
status: completed
readme_content: |
  # SEO記事自動生成システム

  [![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
  [![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org)

  SEO最適化された記事を自動生成するワークフローシステム。

  ## 技術スタック

  | カテゴリ | 技術 |
  |----------|------|
  | Backend | Python 3.11+, FastAPI, SQLAlchemy |
  | Frontend | Next.js 14, React, TypeScript |
  | Workflow | Temporal, LangGraph |
  | Database | PostgreSQL |
  | Storage | MinIO |

  ## クイックスタート

  ### 前提条件

  - Docker 24.0+
  - Docker Compose 2.20+
  - Python 3.11+
  - Node.js 20+

  ### 起動

  ```bash
  git clone <repo_url>
  cd seo-article-generator

  # 初回セットアップ
  ./scripts/bootstrap.sh

  # 起動
  docker compose up -d
  ```

  ## ディレクトリ構造

  ```
  .
  ├── apps/
  │   ├── api/        # FastAPI バックエンド
  │   ├── ui/         # Next.js フロントエンド
  │   └── worker/     # Temporal Worker
  ├── docs/           # ドキュメント
  ├── scripts/        # 運用スクリプト
  └── 仕様書/          # 設計仕様
  ```

changes:
  - section: overview
    type: added
    reason: "プロジェクト情報から新規生成"
  - section: quickstart
    type: added
    reason: "docker-compose.yml と scripts から生成"
  - section: structure
    type: added
    reason: "ディレクトリ構造から生成"

metadata:
  tech_stack:
    - Python 3.11+
    - FastAPI
    - Next.js 14
    - Temporal
    - PostgreSQL
    - MinIO
  main_files:
    - pyproject.toml
    - docker-compose.yml

next_steps:
  - 生成内容のレビュー
  - README.md への書き込み確認
```

### 差分更新の場合

```yaml
status: completed
readme_content: |
  （更新後の README 全文）

changes:
  - section: quickstart
    type: updated
    reason: "Docker Compose サービス構成の変更を反映"
  - section: structure
    type: updated
    reason: "apps/worker/graphs/ ディレクトリを追加"

diff:
  quickstart:
    before: |
      ```bash
      docker compose up -d postgres minio
      ```
    after: |
      ```bash
      docker compose up -d postgres minio temporal temporal-ui
      ```
  structure:
    before: |
      └── worker/     # Temporal Worker
    after: |
      └── worker/     # Temporal Worker
          ├── activities/
          ├── graphs/     # LangGraph ワークフロー（新規）
          └── workflows/

next_steps:
  - 差分のレビュー
  - README.md への反映確認
```

---

## 親への報告形式

### 完了時

```yaml
status: completed
summary: "README.md を新規生成（5セクション）"
readme_content: |
  （生成内容）
changes:
  - section: overview
    type: added
    reason: "技術スタック情報から生成"
next_steps:
  - ユーザー確認後、README.md に書き込み
  - @doc-validator で品質検証（オプション）
```

### レビュー必要時

```yaml
status: needs_review
summary: "既存 README との差分が大きいため確認が必要"
questions:
  - overview セクションのバッジを更新してよいか？
  - 削除予定のディレクトリを structure から除外してよいか？
diff:
  （変更箇所）
```

### ブロック時

```yaml
status: blocked
summary: "プロジェクト構造解析に失敗"
blockers:
  - package.json と pyproject.toml の両方が見つからない
  - target ディレクトリが存在しない
required_input:
  - プロジェクトのメイン設定ファイルのパス
```

---

## 呼び出し例

```
@readme-generator でプロジェクトルートの README を生成してください
target: /home/user/project
sections: [overview, quickstart, structure, usage]
```

```
@readme-generator で既存 README を更新してください
target: /home/user/project
sections: [quickstart, structure]
existing_readme: /home/user/project/README.md
```

```
@readme-generator で apps/api/ のサブ README を生成してください
target: /home/user/project/apps/api
sections: [overview, usage]
options:
  max_depth: 2
  include_badges: false
```

---

## 注意事項

- **自動書き込み禁止**: 生成内容は必ずユーザー確認後に書き込み
- **技術スタック精度**: 設定ファイルから正確に抽出し、推測しない
- **コマンド検証**: クイックスタートのコマンドは実在を確認
- **リンク検証**: 内部リンクは必ずファイル存在を確認
- **除外パターン遵守**: .gitignore のパターンを structure から除外
- **日本語/英語対応**: 既存 README の言語に合わせる
