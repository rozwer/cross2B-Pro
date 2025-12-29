# Phase 2: ディレクトリ作成

> **Claude Code への指示**: 対象プロジェクトに `.claude/` ディレクトリ構造を作成せよ。

---

## 実行コマンド

```bash
# .claude ディレクトリ構造を作成
mkdir -p .claude/{agents,commands/dev,hooks,rules,skills}

# 構造確認
ls -la .claude/
```

---

## Codex 使用時（options.json の use_codex が true の場合）

```bash
mkdir -p .codex
```

---

## 完了条件

以下のディレクトリが存在すること：

```
.claude/
├── agents/
├── commands/
│   └── dev/
├── hooks/
├── rules/
└── skills/
```

確認コマンド：

```bash
for dir in .claude/agents .claude/commands/dev .claude/hooks .claude/rules .claude/skills; do
  [ -d "$dir" ] && echo "[OK] $dir" || echo "[NG] $dir"
done
```

---

## 次のフェーズ

ディレクトリ作成が完了したら、[Phase 3: テンプレートコピー](./03-template-copy.md) へ進む。
