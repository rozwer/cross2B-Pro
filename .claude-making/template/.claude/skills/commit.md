---
name: commit
description: Git コミットを作成する。変更内容を分析し、Conventional Commits 形式でコミットメッセージを生成。
---

# /commit - コミット作成

## 概要

現在の変更内容を分析し、適切なコミットメッセージを生成してコミットを作成する。

## 使用例

- `/commit` - 現在の変更をコミット
- `/commit --amend` - 直前のコミットを修正

## 実行フロー

1. `git status` で変更内容を確認
2. `git diff` で差分を分析
3. 変更の種類を判定（feat/fix/docs/refactor/test/chore）
4. Conventional Commits 形式でメッセージを生成
5. ユーザーに確認
6. `git commit` を実行

## Conventional Commits 形式

```
<type>(<scope>): <description>

例:
feat(api): add user authentication endpoint
fix(ui): resolve button alignment issue
docs: update README installation steps
refactor(db): extract query helpers
test(api): add unit tests for auth service
chore: update dependencies
```

## 使用するエージェント

- @diff-analyzer: 差分の分析
- @commit-creator: コミットメッセージ生成
