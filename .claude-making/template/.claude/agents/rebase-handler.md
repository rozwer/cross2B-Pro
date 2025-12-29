# rebase-handler

> rebase を実行し、コンフリクト発生時は conflict-resolver と連携する subagent。

---

## 責務

1. `git rebase` を実行
2. コンフリクト発生時は `@conflict-resolver` を呼び出し
3. rebase 完了または中断の報告

---

## 入力

```yaml
target: develop  # rebase 先
interactive: false  # -i オプション
autosquash: false  # --autosquash オプション
```

---

## 出力

```yaml
status: success | conflict | aborted | needs_parent
commits_rebased: 5
conflicts_resolved: 2
conflicts_remaining: 1
current_commit: abc1234  # コンフリクト時、処理中のコミット
```

---

## 実行手順

```bash
# 1. 事前チェック
git status  # クリーンな状態か確認

# 2. fetch して最新化
git fetch origin

# 3. rebase 実行
git rebase origin/develop

# 4. コンフリクト発生時
if has_conflicts; then
    call @conflict-resolver

    if all_resolved; then
        git rebase --continue
    else
        report_to_parent
    fi
fi

# 5. 完了報告
```

---

## rebase vs merge の判断

| 状況 | 推奨 | 理由 |
|------|------|------|
| feature ブランチの更新 | rebase | 履歴がきれいに |
| 共有ブランチ | merge | 履歴改変を避ける |
| 長期ブランチの統合 | merge | コンフリクト範囲が広い |
| PR 前の整理 | rebase | レビューしやすく |

---

## コンフリクト発生時のフロー

```
git rebase develop
        ↓
    コンフリクト発生
        ↓
┌───────────────────────────────┐
│  @conflict-resolver を呼び出し │
└───────────────────────────────┘
        ↓
    ┌─────────────────┐
    │  自動解決可能？  │
    └─────────────────┘
      ↓ Yes      ↓ No
  解決 & add    親に報告
      ↓
  git rebase --continue
      ↓
  次のコンフリクト or 完了
```

---

## 親に報告が必要なケース

1. 自動解決不可能なコンフリクト
2. rebase 対象のコミットが多すぎる（10+）
3. 大規模なコンフリクト（複数ファイル）
4. --force-push が必要な状況

---

## 親への報告形式

### コンフリクト報告

```yaml
status: conflict
target: develop
progress: "3/5 commits rebased"
current_commit:
  sha: abc1234
  message: "feat(api): add bulk delete endpoint"

conflict_details:
  file: apps/api/routers/runs.py
  type: content
  auto_resolved: false

instructions: |
  コンフリクトを手動で解決してください:

  1. apps/api/routers/runs.py を編集
  2. git add apps/api/routers/runs.py
  3. git rebase --continue

  または中断する場合:
  git rebase --abort
```

### 完了報告

```yaml
status: success
target: develop
commits_rebased: 5
conflicts_resolved: 2
message: "develop の最新に rebase しました"

next_steps:
  - "git push --force-with-lease origin feature/bulk-delete"
  - "または /git-commit-flow で push"

warning: |
  rebase 後は force push が必要です。
  共有ブランチの場合は注意してください。
```

---

## 安全オプション

### --force-with-lease

```bash
# 安全な force push（他の人の変更を上書きしない）
git push --force-with-lease origin feature/bulk-delete
```

### rebase 中断

```bash
# コンフリクト解決を諦める
git rebase --abort

# 特定のコミットをスキップ
git rebase --skip
```

---

## interactive rebase

```yaml
input:
  interactive: true

# 以下の操作は親に確認が必要
operations:
  - squash: "複数コミットをまとめる"
  - reword: "コミットメッセージを変更"
  - drop: "コミットを削除"
  - reorder: "コミット順序を変更"
```

**注意**: interactive rebase は TUI 操作が必要なため、基本的には親が実行。subagent は `--autosquash` など自動化可能なオプションのみ対応。
