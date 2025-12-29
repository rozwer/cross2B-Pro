# push-handler

> git push を実行し、エラー時は親に報告する subagent。

---

## 責務

1. `git push` を実行
2. エラー時は詳細を親に報告
3. 保護ブランチへの push を検出して警告

---

## 入力

```yaml
branch: feature/bulk-delete  # 省略時は現在のブランチ
remote: origin  # 省略時は origin
force: false  # --force オプション
```

---

## 出力

```yaml
status: success | failed | needs_parent
remote_url: "https://github.com/user/repo"
branch: feature/bulk-delete
commits_pushed: 3
error:  # 失敗時
  type: remote_diverged | auth_error | protected_branch | unknown
  message: "..."
  suggestion: "..."
```

---

## 実行手順

```bash
# 1. 事前チェック
git fetch origin

# 2. ブランチ確認
current_branch=$(git branch --show-current)

# 3. 保護ブランチチェック
if [[ "$current_branch" =~ ^(main|master|develop)$ ]]; then
    warn "保護ブランチへの直接 push です"
fi

# 4. remote との差分チェック
git status  # "Your branch is behind" を検出

# 5. push 実行
git push origin "$current_branch"
```

---

## エラーハンドリング

### remote との差分

```
error: failed to push some refs to 'origin'
hint: Updates were rejected because the remote contains work that you do not have locally.

# 報告
親に報告:
  type: remote_diverged
  message: "リモートに新しいコミットがあります"
  suggestion: |
    以下のいずれかを実行してください:
    1. git pull --rebase origin <branch>
    2. git pull origin <branch>（マージコミット作成）
```

### 認証エラー

```
fatal: Authentication failed for 'https://github.com/...'

# 報告
親に報告:
  type: auth_error
  message: "認証に失敗しました"
  suggestion: |
    - SSH キーを確認
    - Personal Access Token を更新
    - gh auth login を実行
```

### 保護ブランチ

```
remote: error: GH006: Protected branch update failed

# 報告
親に報告:
  type: protected_branch
  message: "保護ブランチへの直接 push は禁止されています"
  suggestion: |
    - 別ブランチを作成して PR を作成してください
    - git checkout -b feature/xxx
    - git push origin feature/xxx
```

---

## 保護ブランチルール

| ブランチ | push ルール |
|---------|------------|
| `main` / `master` | 禁止（PR 必須） |
| `develop` | 条件付き許可（smoke テスト通過後） |
| `feature/*` | 許可 |
| `fix/*` | 許可 |
| `hotfix/*` | 条件付き許可 |

---

## 成功時の出力例

```yaml
status: success
remote_url: "https://github.com/user/seo-article-generator"
branch: feature/bulk-delete
commits_pushed: 3
message: |
  3 commits pushed to origin/feature/bulk-delete

  abc1234 feat(api): add bulk delete endpoint
  def5678 feat(ui): add bulk selection checkbox
  ghi9012 docs(api): document bulk delete endpoint
```

---

## push 後のアクション提案

```yaml
next_actions:
  - "PR を作成: gh pr create --base develop"
  - "レビュー依頼: @pr-reviewer でレビュー"
```
