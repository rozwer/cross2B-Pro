---
description: git worktree を使った並列開発のルール
---

## 目的

複数の実装タスクを衝突なく並列に進める。

## 基本ルール

- worktree は `./.worktrees/<topic>/` 配下に作る
- 1 worktree = 1 作業テーマ
- 同じファイルを複数 worktree で同時に触らない

## 作成コマンド

```bash
mkdir -p .worktrees
git worktree add -b "feat/topic-name" ".worktrees/topic-name"
```

## 削除コマンド

```bash
git worktree remove ".worktrees/topic-name"
git worktree prune
```

## 注意事項

- リモート操作（push/pull/fetch）は行わない
- 削除前に `git status` でクリーンか確認
