# Phase 3: テンプレートコピー

> **Claude Code への指示**: `.claude-making/template/` から対象プロジェクトの `.claude/` へ汎用ファイルをコピーせよ。

---

## 前提

- `.claude-making/` ディレクトリが存在すること
- Phase 1 で生成した `options.json` を参照すること

---

## コピー対象

### 必須コピー

| ソース | コピー先 | 説明 |
|--------|---------|------|
| `template/.claude/settings.json` | `.claude/settings.json` | 基本設定 |
| `template/.claude/rules/` | `.claude/rules/` | 汎用ルール |
| `template/.claude/commands/dev/` | `.claude/commands/dev/` | 開発コマンド |

### 条件付きコピー

`options.json` の設定に基づいて判断：

| 条件 | ソース | コピー先 |
|------|--------|---------|
| 常に | `template/.claude/skills/` | `.claude/skills/` |
| 常に | `template/.claude/agents/` | `.claude/agents/` |
| 常に | `template/.claude/memory/` | `.claude/memory/` |
| hooks 使用 | `template/.claude/hooks/` | `.claude/hooks/` |
| use_codex: true | `optional/codex/` | `.claude/` (マージ) |

---

## 実行コマンド

```bash
# 変数設定（.claude-making の場所を指定）
TEMPLATE_DIR=".claude-making/template"

# 必須: settings.json
cp "$TEMPLATE_DIR/.claude/settings.json" .claude/settings.json

# 必須: rules/
cp -r "$TEMPLATE_DIR/.claude/rules/"* .claude/rules/ 2>/dev/null || true

# 必須: commands/dev/
cp -r "$TEMPLATE_DIR/.claude/commands/dev/"* .claude/commands/dev/ 2>/dev/null || true
```

### 条件付きコピー（options.json に基づく）

```bash
# skills/ をコピー
cp -r "$TEMPLATE_DIR/.claude/skills/"* .claude/skills/ 2>/dev/null || true

# agents/ をコピー
cp -r "$TEMPLATE_DIR/.claude/agents/"* .claude/agents/ 2>/dev/null || true

# memory/ をコピー
cp -r "$TEMPLATE_DIR/.claude/memory/"* .claude/memory/ 2>/dev/null || true

# hooks/ をコピー（hooks 使用時）
cp -r "$TEMPLATE_DIR/.claude/hooks/"* .claude/hooks/ 2>/dev/null || true

# Codex 連携（use_codex: true の場合）
USE_CODEX=$(jq -r '.options.use_codex' .claude-making/options.json)
if [ "$USE_CODEX" = "true" ]; then
  cp -r ".claude-making/optional/codex/rules/"* .claude/rules/ 2>/dev/null || true
  cp -r ".claude-making/optional/codex/agents/"* .claude/agents/ 2>/dev/null || true
  mkdir -p .claude/commands/review
  cp -r ".claude-making/optional/codex/commands/review/"* .claude/commands/review/ 2>/dev/null || true
fi
```

---

## コピー後の確認

```bash
echo "=== Copied files ==="
find .claude/ -type f -name "*.md" -o -name "*.json" -o -name "*.sh" -o -name "*.py" | head -30

echo ""
echo "=== File counts ==="
echo "skills/: $(find .claude/skills -type f 2>/dev/null | wc -l)"
echo "agents/: $(find .claude/agents -type f 2>/dev/null | wc -l)"
echo "commands/: $(find .claude/commands -type f 2>/dev/null | wc -l)"
echo "rules/: $(find .claude/rules -type f 2>/dev/null | wc -l)"
echo "hooks/: $(find .claude/hooks -type f 2>/dev/null | wc -l)"
```

---

## 完了条件

- [ ] `.claude/settings.json` が存在する
- [ ] `.claude/rules/` に 1 つ以上のファイルがある
- [ ] `.claude/commands/dev/` に 1 つ以上のファイルがある
- [ ] (条件付き) 必要な skills/agents/hooks がコピーされた

---

## 次のフェーズ

テンプレートコピーが完了したら、[Phase 4: ブループリント展開](./04-blueprint-customize.md) へ進む。
