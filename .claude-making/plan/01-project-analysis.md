# Phase 1: プロジェクト分析

> **Claude Code への指示**: このフェーズでは対象プロジェクトを分析し、`.claude-making/options.json` を生成せよ。

---

## 実行手順

### Step 1: ファイル検出による技術スタック判定

以下のコマンドを実行し、存在するファイルから技術スタックを判定する：

```bash
# Python プロジェクト検出
ls pyproject.toml requirements.txt setup.py Pipfile 2>/dev/null && echo "PYTHON_DETECTED=true"

# Node.js プロジェクト検出
ls package.json 2>/dev/null && echo "NODEJS_DETECTED=true"

# Docker 検出
ls Dockerfile docker-compose.yml docker-compose.yaml compose.yml compose.yaml 2>/dev/null && echo "DOCKER_DETECTED=true"

# Git 検出
ls .git 2>/dev/null && echo "GIT_DETECTED=true"
```

### Step 2: 詳細情報の収集

検出結果に応じて追加調査を実行：

#### Python の場合
```bash
# パッケージ管理ツール判定
if [ -f "pyproject.toml" ]; then
  grep -q "uv" pyproject.toml && echo "PKG_MANAGER=uv"
  grep -q "poetry" pyproject.toml && echo "PKG_MANAGER=poetry"
fi
[ -f "requirements.txt" ] && echo "PKG_MANAGER=pip"

# フレームワーク検出
grep -r "fastapi\|FastAPI" --include="*.py" -l 2>/dev/null | head -1 && echo "FRAMEWORK=fastapi"
grep -r "django\|Django" --include="*.py" -l 2>/dev/null | head -1 && echo "FRAMEWORK=django"
grep -r "flask\|Flask" --include="*.py" -l 2>/dev/null | head -1 && echo "FRAMEWORK=flask"
```

#### Node.js の場合
```bash
# package.json から依存関係を抽出
cat package.json | jq -r '.dependencies | keys[]' 2>/dev/null

# フレームワーク判定
cat package.json | jq -r '.dependencies | keys[]' 2>/dev/null | grep -E "next|react|vue|svelte|express"
```

### Step 3: ディレクトリ構造確認

```bash
# ルートディレクトリ一覧
ls -la

# 主要ディレクトリ構造（2階層）
find . -maxdepth 2 -type d -not -path '*/\.*' -not -path './node_modules/*' | head -30
```

### Step 4: 既存規約確認

```bash
# Linter/Formatter 設定
ls .eslintrc* .prettierrc* ruff.toml biome.json 2>/dev/null

# Git hooks
ls .githooks/ .husky/ 2>/dev/null

# CI/CD
ls .github/workflows/*.yml .gitlab-ci.yml 2>/dev/null
```

---

## 出力: options.json

分析結果を以下の形式で `.claude-making/options.json` に出力する：

```json
{
  "project": {
    "name": "<プロジェクト名>",
    "description": "<プロジェクトの説明>",
    "type": "<webapp|api|cli|library|monorepo>"
  },
  "tech_stack": {
    "backend": {
      "language": "<python|go|nodejs|rust|none>",
      "framework": "<fastapi|django|express|gin|none>",
      "package_manager": "<uv|pip|poetry|npm|pnpm|yarn|none>"
    },
    "frontend": {
      "framework": "<nextjs|react|vue|svelte|none>",
      "language": "<typescript|javascript|none>",
      "styling": "<tailwind|css-modules|styled-components|none>"
    },
    "database": {
      "primary": "<postgresql|mysql|mongodb|sqlite|none>",
      "cache": "<redis|memcached|none>",
      "storage": "<minio|s3|gcs|local|none>"
    },
    "infrastructure": {
      "container": "<docker|podman|none>",
      "orchestration": "<docker-compose|kubernetes|none>",
      "ci_cd": "<github-actions|gitlab-ci|none>"
    }
  },
  "options": {
    "use_codex": false,
    "use_temporal": false,
    "use_langgraph": false,
    "multi_tenant": false,
    "git_strategy": "<gitflow|github-flow|trunk-based>"
  },
  "detected_files": {
    "readme": "<README.md のパス または null>",
    "docs_dir": "<docs/ のパス または null>",
    "existing_claude": "<.claude/ が存在するか true/false>"
  },
  "recommended_assets": {
    "skills": ["<推奨スキル名>"],
    "agents": ["<推奨エージェント名>"],
    "rules": ["<推奨ルール名>"],
    "commands": ["<推奨コマンド名>"]
  }
}
```

---

## 推奨資産の判定ロジック

| 条件 | 推奨資産 |
|------|---------|
| Docker 検出 | `docker-manager` agent, `/dev:up`, `/dev:down` commands |
| Python 検出 | `be-implementer` agent, `dev-style` rule (uv/pip) |
| Node.js 検出 | `fe-implementer` agent, `dev-style` rule (npm/pnpm) |
| Git 検出 | `commit`, `push`, `pr` skills, `git-worktree` rule |
| CI/CD 検出 | `deploy` skill |
| Temporal 検出 | `temporal-debugger` agent |

---

## 完了条件

- [ ] options.json が生成された
- [ ] tech_stack の各項目が埋まっている（不明な場合は "none"）
- [ ] recommended_assets が判定されている

---

## 次のフェーズ

options.json の生成が完了したら、[Phase 2: ディレクトリ作成](./02-structure-setup.md) へ進む。
