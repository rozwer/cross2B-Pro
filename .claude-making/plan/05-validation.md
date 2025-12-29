# Phase 5: 検証

> **Claude Code への指示**: セットアップ結果を検証し、問題があれば修正せよ。

---

## 検証項目

### 1. 構造検証

```bash
echo "=== 構造検証 ==="

# 必須ディレクトリ
for dir in .claude .claude/agents .claude/commands .claude/rules .claude/skills; do
  [ -d "$dir" ] && echo "[OK] $dir" || echo "[NG] $dir missing"
done

# 必須ファイル
for file in .claude/CLAUDE.md .claude/settings.json; do
  [ -f "$file" ] && echo "[OK] $file" || echo "[NG] $file missing"
done
```

### 2. JSON 構文検証

```bash
echo "=== JSON 検証 ==="

if jq empty .claude/settings.json 2>/dev/null; then
  echo "[OK] settings.json is valid"
else
  echo "[NG] settings.json has syntax errors"
fi
```

### 3. Markdown フロントマター検証

```bash
echo "=== フロントマター検証 ==="

# skills
for file in .claude/skills/*.md; do
  [ -f "$file" ] || continue
  if head -1 "$file" | grep -q "^---$"; then
    echo "[OK] $file"
  else
    echo "[NG] $file - frontmatter missing"
  fi
done

# agents
for file in .claude/agents/*.md; do
  [ -f "$file" ] || continue
  if head -1 "$file" | grep -q "^---$"; then
    echo "[OK] $file"
  else
    echo "[NG] $file - frontmatter missing"
  fi
done

# rules
for file in .claude/rules/*.md; do
  [ -f "$file" ] || continue
  if head -1 "$file" | grep -q "^---$"; then
    echo "[OK] $file"
  else
    echo "[WARN] $file - frontmatter missing (optional for rules)"
  fi
done
```

### 4. 未展開変数の確認

```bash
echo "=== 変数展開確認 ==="

if grep -r "{{" .claude/ 2>/dev/null; then
  echo "[NG] Unexpanded variables found"
else
  echo "[OK] All variables expanded"
fi
```

### 5. ファイル数サマリー

```bash
echo "=== ファイル数 ==="
echo "skills: $(find .claude/skills -type f -name '*.md' 2>/dev/null | wc -l)"
echo "agents: $(find .claude/agents -type f -name '*.md' 2>/dev/null | wc -l)"
echo "commands: $(find .claude/commands -type f -name '*.md' 2>/dev/null | wc -l)"
echo "rules: $(find .claude/rules -type f -name '*.md' 2>/dev/null | wc -l)"
echo "hooks: $(find .claude/hooks -type f 2>/dev/null | wc -l)"
```

---

## 問題発生時の対処

### NG: ディレクトリが存在しない

```bash
mkdir -p .claude/{agents,commands/dev,hooks,rules,skills}
```

### NG: settings.json が不正

```bash
# バックアップを取って再生成
mv .claude/settings.json .claude/settings.json.bak
cp .claude-making/template/.claude/settings.json .claude/settings.json
```

### NG: フロントマターがない

ファイル先頭に以下を追加：

```markdown
---
name: <ファイル名から拡張子を除いたもの>
description: <説明>
---
```

### NG: 未展開変数がある

Phase 4 を再実行するか、手動で置換：

```bash
sed -i 's/{{PROJECT_NAME}}/actual-name/g' .claude/CLAUDE.md
```

---

## 完了条件

以下がすべて [OK] であること：

- [ ] 必須ディレクトリがすべて存在
- [ ] 必須ファイル（CLAUDE.md, settings.json）が存在
- [ ] settings.json が有効な JSON
- [ ] skills/*.md, agents/*.md にフロントマターがある
- [ ] 未展開の変数 `{{...}}` がない

---

## セットアップ完了後

### Git にコミット

```bash
git add .claude/
git commit -m "chore: setup Claude Code configuration"
```

### 動作確認（手動）

1. プロジェクトルートで Claude Code を起動
2. `/help` でスキル一覧を確認
3. 主要スキル（`/commit`, `/dev:status` 等）を試行
4. エージェント呼び出し（`@architect` 等）を試行

---

## セットアップ完了

すべての検証に合格したら、`.claude/` ディレクトリのセットアップは完了。

以降は通常の開発作業で Claude Code を活用できる。
