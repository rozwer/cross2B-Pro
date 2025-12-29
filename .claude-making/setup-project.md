# setup-project.md - プロジェクトセットアップ実行指示

> **Claude Code へ**: このファイルを読んだら、以下のフローに従って `.claude/` を構築してください。

## 概要

新規プロジェクトに `.claude/` ディレクトリを構築する。
`.claude-making/` の plan/ に従って、対話形式でセットアップを実行。

## 前提条件

- `.claude-making/` ディレクトリが存在すること
- 対象プロジェクトのルートで実行すること
- このファイル（setup-project.md）は `.claude-making/` 直下に配置されていること

## 実行フロー

### Phase 1: プロジェクト分析

`.claude-making/plan/01-project-analysis.md` に従って実行：

1. 技術スタック検出
   ```bash
   ls pyproject.toml package.json Dockerfile docker-compose.yml 2>/dev/null
   ```

2. 詳細分析（検出結果に応じて）

3. `options.json` を生成
   ```bash
   # .claude-making/options.json に出力
   ```

### Phase 2: ディレクトリ作成

`.claude-making/plan/02-structure-setup.md` に従って実行：

```bash
mkdir -p .claude/{agents,commands/dev,hooks,rules,skills}
```

### Phase 3: テンプレートコピー

`.claude-making/plan/03-template-copy.md` に従って実行：

```bash
TEMPLATE_DIR=".claude-making/template"

# 必須ファイル
cp "$TEMPLATE_DIR/.claude/settings.json" .claude/
cp -r "$TEMPLATE_DIR/.claude/rules/"* .claude/rules/
cp -r "$TEMPLATE_DIR/.claude/commands/dev/"* .claude/commands/dev/

# 条件付き（options.json に基づく）
cp -r "$TEMPLATE_DIR/.claude/skills/"* .claude/skills/
cp -r "$TEMPLATE_DIR/.claude/agents/"* .claude/agents/
cp -r "$TEMPLATE_DIR/.claude/hooks/"* .claude/hooks/
```

### Phase 4: ブループリント展開

`.claude-making/plan/04-blueprint-customize.md` に従って実行：

1. options.json から変数を取得
2. blueprint/*.template を変数置換して出力
3. CLAUDE.md を生成

### Phase 5: 検証

`.claude-making/plan/05-validation.md` に従って実行：

```bash
# 構造検証
for dir in .claude/agents .claude/commands .claude/rules .claude/skills; do
  [ -d "$dir" ] && echo "[OK] $dir" || echo "[NG] $dir"
done

# JSON 検証
jq empty .claude/settings.json && echo "[OK] settings.json"

# 未展開変数チェック
grep -r "{{" .claude/ && echo "[NG] Unexpanded vars" || echo "[OK] All expanded"
```

## 対話ポイント

以下のタイミングでユーザーに確認：

1. **Phase 1 完了時**: 分析結果の確認
   - 「以下の技術スタックを検出しました。正しいですか？」

2. **Phase 4 開始前**: カスタマイズ内容の確認
   - 「以下の設定で CLAUDE.md を生成します。変更はありますか？」

3. **Phase 5 完了時**: 最終確認
   - 「セットアップが完了しました。動作確認を行いますか？」

## エラー時の対処

| エラー | 対処 |
|--------|------|
| `.claude-making/` がない | 「.claude-making ディレクトリが見つかりません」と報告 |
| 分析失敗 | 手動で情報を入力してもらう |
| テンプレートコピー失敗 | 個別ファイルを確認して再試行 |
| 変数展開漏れ | Phase 4 を再実行 |

## 使用例

Claude Code に以下のように依頼：

```
.claude-making/setup-project.md を読んで実行してください
```

または、このファイルを IDE で開いた状態で：

```
開いているファイルの指示に従って実行してください
```

プロジェクトルートで実行すると、対話形式でセットアップが開始される。