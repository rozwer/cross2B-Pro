---
description: テスト実行（scope に応じて分岐）
allowed-tools: Bash
---

## 実行フロー

1. 引数を解析
2. scope に応じて分岐:
   - なし / \`all\` → 全テスト実行
   - \`smoke\` → smoke テスト実行
   - \`unit\` → ユニットテストのみ
   - \`integration\` → 統合テストのみ
   - \`<module>\` → 指定モジュールのテスト

## 使用例

\`\`\`
/dev:test             # 全テスト
/dev:test smoke       # smoke テスト
/dev:test unit        # 全ユニットテスト
/dev:test integration # 統合テスト
/dev:test api         # api モジュールのテスト
\`\`\`

---

## scope 別コマンド

### \`all\` / 引数なし

\`\`\`bash
uv run pytest -v --tb=short
\`\`\`

### \`smoke\`

\`\`\`bash
uv run pytest tests/smoke/ -v --tb=short
\`\`\`

### \`unit\`

\`\`\`bash
uv run pytest tests/unit/ -v --tb=short
\`\`\`

### \`integration\`

\`\`\`bash
uv run pytest tests/integration/ -v --tb=short
\`\`\`

### \`<module>\` (例: api, worker)

\`\`\`bash
uv run pytest src/<module>/tests/ -v --tb=short
# または
uv run pytest tests/unit/test_<module>.py -v --tb=short
\`\`\`

---

## クイックリファレンス

### pytest マーカー

\`\`\`bash
# slow テストを除外
uv run pytest -m "not slow" -v

# Docker 必須テストのみ
uv run pytest -m docker -v

# 特定ファイル
uv run pytest tests/unit/test_example.py -v
\`\`\`

### カバレッジ

\`\`\`bash
uv run pytest --cov=src --cov-report=html
\`\`\`

### 並列実行

\`\`\`bash
uv run pytest -n auto -v
\`\`\`
