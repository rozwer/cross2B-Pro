---
name: pr
description: Pull Request を作成する。変更内容を分析し、適切な PR タイトルと説明を生成。
---

# /pr - Pull Request 作成

## 概要

現在のブランチから Pull Request を作成する。コミット履歴を分析し、適切なタイトルと説明を生成。

## 使用例

- `/pr` - PR を作成
- `/pr --draft` - ドラフト PR として作成

## 実行フロー

1. 現在のブランチとベースブランチを確認
2. コミット履歴を分析
3. PR タイトルと説明を生成
4. ユーザーに確認
5. `gh pr create` を実行
6. PR URL を報告

## PR テンプレート

```markdown
## Summary

<変更の概要を1-3行で>

## Changes

- <変更点1>
- <変更点2>

## Test Plan

- [ ] <テスト項目1>
- [ ] <テスト項目2>
```

## 使用するエージェント

- @diff-analyzer: 差分の分析
- @pr-creator: PR 作成
