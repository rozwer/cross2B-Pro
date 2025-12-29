# Phase 4: ブループリント展開

> **Claude Code への指示**: `blueprint/` のテンプレートを `options.json` の情報で展開し、プロジェクト固有のファイルを生成せよ。

---

## 前提

- Phase 1 で生成した `options.json` が存在すること
- Phase 3 でテンプレートがコピーされていること

---

## 展開対象

### 必須: CLAUDE.md

`blueprint/CLAUDE.md.template` を展開して `.claude/CLAUDE.md` を生成する。

#### 変数一覧

| 変数 | 値の取得元 | 例 |
|------|-----------|-----|
| `{{PROJECT_NAME}}` | options.json の project.name | "my-project" |
| `{{PROJECT_DESCRIPTION}}` | options.json の project.description | "ECサイト" |
| `{{BACKEND_LANG}}` | options.json の tech_stack.backend.language | "python" |
| `{{BACKEND_FRAMEWORK}}` | options.json の tech_stack.backend.framework | "fastapi" |
| `{{FRONTEND_FRAMEWORK}}` | options.json の tech_stack.frontend.framework | "nextjs" |
| `{{PKG_MANAGER_BE}}` | options.json の tech_stack.backend.package_manager | "uv" |
| `{{PKG_MANAGER_FE}}` | options.json の tech_stack.frontend 依存 | "npm" |
| `{{DATABASE}}` | options.json の tech_stack.database.primary | "postgresql" |
| `{{CONTAINER}}` | options.json の tech_stack.infrastructure.container | "docker" |
| `{{GIT_STRATEGY}}` | options.json の options.git_strategy | "gitflow" |

---

## 展開手順

### Step 1: options.json を読み込む

```bash
# 変数を取得
PROJECT_NAME=$(jq -r '.project.name' .claude-making/options.json)
BACKEND_LANG=$(jq -r '.tech_stack.backend.language' .claude-making/options.json)
BACKEND_FRAMEWORK=$(jq -r '.tech_stack.backend.framework' .claude-making/options.json)
PKG_MANAGER=$(jq -r '.tech_stack.backend.package_manager' .claude-making/options.json)
FRONTEND_FRAMEWORK=$(jq -r '.tech_stack.frontend.framework' .claude-making/options.json)
DATABASE=$(jq -r '.tech_stack.database.primary' .claude-making/options.json)
GIT_STRATEGY=$(jq -r '.options.git_strategy' .claude-making/options.json)
```

### Step 2: CLAUDE.md を生成

`blueprint/CLAUDE.md.template` を読み込み、変数を置換して `.claude/CLAUDE.md` に出力する。

```bash
sed -e "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" \
    -e "s/{{BACKEND_LANG}}/$BACKEND_LANG/g" \
    -e "s/{{BACKEND_FRAMEWORK}}/$BACKEND_FRAMEWORK/g" \
    -e "s/{{PKG_MANAGER}}/$PKG_MANAGER/g" \
    -e "s/{{FRONTEND_FRAMEWORK}}/$FRONTEND_FRAMEWORK/g" \
    -e "s/{{DATABASE}}/$DATABASE/g" \
    -e "s/{{GIT_STRATEGY}}/$GIT_STRATEGY/g" \
    .claude-making/blueprint/CLAUDE.md.template > .claude/CLAUDE.md
```

### Step 3: 条件付きファイル生成

`options.json` の `recommended_assets` に基づいて追加ファイルを生成：

#### Backend Implementer（backend.language が none 以外の場合）

```bash
if [ "$BACKEND_LANG" != "none" ]; then
  sed -e "s/{{BACKEND_LANG}}/$BACKEND_LANG/g" \
      -e "s/{{BACKEND_FRAMEWORK}}/$BACKEND_FRAMEWORK/g" \
      .claude-making/blueprint/agents/be-implementer.md.template > .claude/agents/be-implementer.md
fi
```

#### Frontend Implementer（frontend.framework が none 以外の場合）

```bash
if [ "$FRONTEND_FRAMEWORK" != "none" ]; then
  sed -e "s/{{FRONTEND_FRAMEWORK}}/$FRONTEND_FRAMEWORK/g" \
      .claude-making/blueprint/agents/fe-implementer.md.template > .claude/agents/fe-implementer.md
fi
```

#### dev-style.md ルール

```bash
sed -e "s/{{PKG_MANAGER_BE}}/$PKG_MANAGER/g" \
    -e "s/{{GIT_STRATEGY}}/$GIT_STRATEGY/g" \
    .claude-making/blueprint/rules/dev-style.md.template > .claude/rules/dev-style.md
```

---

## blueprint/ のファイル一覧

### 必須テンプレート

| ファイル | 展開条件 | 出力先 |
|---------|---------|--------|
| `CLAUDE.md.template` | 常に | `.claude/CLAUDE.md` |
| `rules/dev-style.md.template` | 常に | `.claude/rules/dev-style.md` |
| `rules/implementation.md.template` | 常に | `.claude/rules/implementation.md` |

### 技術スタック依存テンプレート

| ファイル | 展開条件 | 出力先 |
|---------|---------|--------|
| `agents/implementer.md.template` | backend/frontend あり | `.claude/agents/implementer.md` |
| `agents/domain-expert.md.template` | domain 指定あり | `.claude/agents/domain-expert.md` |
| `rules/domain-contract.md.template` | domain 指定あり | `.claude/rules/domain-contract.md` |
| `skills/domain-specific.md.template` | domain 指定あり | `.claude/skills/domain-specific.md` |
| `skills/tech-stack.md.template` | 技術スタックあり | `.claude/skills/tech-stack.md` |
| `commands/domain-command.md.template` | domain 指定あり | `.claude/commands/domain/` |

### ワークフロー系テンプレート

| ファイル | 展開条件 | 出力先 |
|---------|---------|--------|
| `skills/workflow-framework-*.md.template` | workflow_framework 指定あり | `.claude/skills/` |
| `skills/workflow-step-impl.md.template` | workflow_framework 指定あり | `.claude/skills/workflow-step-impl.md` |
| `agents/orchestrator-debugger.md.template` | orchestrator 指定あり | `.claude/agents/orchestrator-debugger.md` |
| `commands/debug/*.md.template` | orchestrator 指定あり | `.claude/commands/debug/` |
| `commands/workflow/*.md.template` | orchestrator 指定あり | `.claude/commands/workflow/` |

### LLM 統合テンプレート

| ファイル | 展開条件 | 出力先 |
|---------|---------|--------|
| `skills/llm-prompt-authoring.md.template` | llm_provider 指定あり | `.claude/skills/llm-prompt-authoring.md` |
| `agents/llm-prompt-engineer.md.template` | llm_provider 指定あり | `.claude/agents/llm-prompt-engineer.md` |
| `agents/llm-prompt-tester.md.template` | llm_provider 指定あり | `.claude/agents/llm-prompt-tester.md` |

### テスト系テンプレート

| ファイル | 展開条件 | 出力先 |
|---------|---------|--------|
| `skills/api-test.md.template` | backend あり | `.claude/skills/api-test.md` |
| `skills/integration-test.md.template` | 常に | `.claude/skills/integration-test.md` |
| `skills/e2e-test.md.template` | frontend あり | `.claude/skills/e2e-test.md` |

---

## 完了条件

- [ ] `.claude/CLAUDE.md` が生成され、プロジェクト名が正しい
- [ ] 必要なエージェントが生成された
- [ ] `dev-style.md` がプロジェクトに合った内容になっている
- [ ] 変数 `{{...}}` が残っていない

確認コマンド：

```bash
# 未展開の変数がないか確認
grep -r "{{" .claude/ && echo "[NG] Unexpanded variables found" || echo "[OK] All variables expanded"
```

---

## 次のフェーズ

ブループリント展開が完了したら、[Phase 5: 検証](./05-validation.md) へ進む。
