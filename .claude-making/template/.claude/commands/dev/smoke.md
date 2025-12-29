---
description: 簡易スモーク（環境/依存/構文/起動の最低限チェック）
allowed-tools: Bash
---

## クイック実行

\`\`\`bash
# Python プロジェクト
uv run pytest tests/smoke/ -v --tb=short

# Node.js プロジェクト
npm test -- --testPathPattern=smoke
\`\`\`

## 失敗時

- 依存修復: \`uv sync\` / \`npm install\`
- 詳細: 下記のガイドを参照

---

> commit 前に必ず実行

## 1. 環境確認

### 確認項目（一般的）

| 項目           | 最小バージョン | 確認コマンド             |
| -------------- | -------------- | ------------------------ |
| Python         | 3.11+          | \`python3 --version\`      |
| Node.js        | 20+            | \`node --version\`         |
| Docker         | 24.0+          | \`docker --version\`       |
| Docker Compose | 2.20+          | \`docker compose version\` |

---

## 2. 依存チェック

\`\`\`bash
# Python
uv sync --frozen  # lockファイルと一致するか確認

# Node.js
npm audit --audit-level=high
\`\`\`

---

## 3. 型・構文チェック

\`\`\`bash
# Python
uv run python3 -m compileall src/
uv run mypy src/ --ignore-missing-imports
uv run ruff check src/

# TypeScript
npx tsc --noEmit
\`\`\`

---

## 4. インポートテスト

\`\`\`bash
# 主要モジュールのインポート確認
uv run python3 -c "from src.main import app; print(OK)"
\`\`\`

---

## 5. Docker 検証

\`\`\`bash
# 設定ファイルの検証
docker compose config --quiet

# サービス一覧
docker compose config --services

# ビルド確認（オプション、時間がかかる）
docker compose build --dry-run
\`\`\`

---

## 6. pytest smoke テスト

\`\`\`bash
# smoke テストスイート実行
uv run pytest tests/smoke/ -v --tb=short

# 特定テストのみ
uv run pytest tests/smoke/test_imports.py -v
\`\`\`

---

## 失敗時の対処

| 症状             | 原因                     | 解決策                                 |
| ---------------- | ------------------------ | -------------------------------------- |
| 依存エラー       | パッケージ不足           | \`uv sync\` / \`npm install\`              |
| 型エラー         | 型定義の問題             | 該当ファイルを修正                     |
| 構文エラー       | リント違反               | \`uv run ruff check --fix src/\`         |
| Docker エラー    | Docker未起動             | Docker Desktop を起動                  |
| ポート競合       | 既存プロセス             | \`.env\` でポート変更 or \`lsof -i :PORT\` |
| インポートエラー | パス設定                 | \`PYTHONPATH=.\` を設定                  |

---

## チェックリスト

commit 前に以下を確認：

- [ ] \`uv run pytest tests/smoke/ -v\` が成功
- [ ] \`uv run ruff check src/\` がエラーなし
- [ ] \`uv run mypy src/ --ignore-missing-imports\` がエラーなし
