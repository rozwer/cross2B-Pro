---
description: git worktree 運用（並列実装の基本ルール・安全策）
---

## 目的

- 複数の実装タスクを **衝突なく並列** に進める（UI/Worker/API などを同時進行）。

## 基本ルール

- worktree は `./.worktrees/<topic>/` 配下に作る（見通し・掃除を簡単にする）。
- 1 worktree = 1 作業テーマ（例：`frontend-canvas` / `backend-temporal-signals`）。
- **同じファイルを複数 worktree で同時に触らない**（衝突が起きやすい）。
- 共有リソース（DB/ポート/ストレージパス）は worktree ごとに分けるか、起動は1つに絞る。

## ローカル環境の注意

- Python venv は worktree ごとに作る（例：`<worktree>/langgraph-example/.venv`）。共有すると依存やパスが壊れやすい。
- 生成物は `ref/` に集約するか、worktree 側に置くなら命名で衝突を避ける。

## Git運用の注意

- `git push/pull/fetch/remote` などの **リモート操作は行わない**（必要なら人間が実施）。
- worktree 削除前に、対象 worktree がクリーンか（`git status`）を必ず確認する。
