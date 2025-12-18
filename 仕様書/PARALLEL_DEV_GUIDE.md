# 並列開発ガイド

> **参考**: awakia氏「Gitで並列開発が楽になるブランチモデル」を本プロジェクト用にカスタマイズ
>
> - git worktree による物理的分離
> - サブエージェント（Claude/Codex）による同時実装
> - フォールバック禁止原則との整合性

---

## ブランチ戦略

### ブランチ構成

```
main (master)
  │
  └── develop ← 開発の統合ブランチ
        │
        ├── feat/llm-gemini      ← 機能ブランチ（worktree分離）
        ├── feat/llm-openai      ← 機能ブランチ（worktree分離）
        ├── feat/llm-anthropic   ← 機能ブランチ（worktree分離）
        ├── feat/tools-serp      ← 機能ブランチ（worktree分離）
        └── ...
```

### ブランチ命名規則

| プレフィックス | 用途                     | 例                                       |
| -------------- | ------------------------ | ---------------------------------------- |
| `feat/`        | 新機能開発               | `feat/llm-gemini`, `feat/step4-contract` |
| `fix/`         | バグ修正                 | `fix/json-validator-edge-case`           |
| `refactor/`    | リファクタリング         | `refactor/artifact-store`                |
| `docs/`        | ドキュメント             | `docs/api-specification`                 |
| `hotfix/`      | 緊急修正（mainから分岐） | `hotfix/security-patch`                  |

### ブランチのライフサイクル

```
1. develop から feat/xxx を作成（worktree併用推奨）
2. 機能実装 + テスト
3. smoke テスト通過
4. PR作成 → develop へマージ
5. worktree削除、ブランチ削除
```

---

## Worktree 運用（物理分離）

### なぜ Worktree を使うか

| 課題                               | 解決策                                   |
| ---------------------------------- | ---------------------------------------- |
| 複数AIエージェントが同時編集で衝突 | worktree で物理的にディレクトリ分離      |
| ブランチ切替のオーバーヘッド       | worktree なら切替不要（並列で開ける）    |
| 依存関係の分離                     | 各 worktree で独立した venv/node_modules |

### ディレクトリ構造

```
/home/rozwer/案件/              ← メインワークツリー（develop）
├── .worktrees/                  ← worktree 格納ディレクトリ
│   ├── llm-gemini/             ← feat/llm-gemini ブランチ
│   ├── llm-openai/             ← feat/llm-openai ブランチ
│   ├── llm-anthropic/          ← feat/llm-anthropic ブランチ
│   └── tools-serp/             ← feat/tools-serp ブランチ
└── ...
```

### 基本操作

#### 1. Worktree 作成（新機能開始時）

```bash
# テンプレート
TOPIC="llm-gemini"
mkdir -p .worktrees
git worktree add -b "feat/$TOPIC" ".worktrees/$TOPIC" develop

# 確認
git worktree list
```

#### 2. Worktree での作業

```bash
cd ".worktrees/$TOPIC"
# 通常のgit操作
git add .
git commit -m "feat: Gemini API クライアント実装"
git push -u origin "feat/$TOPIC"
```

#### 3. PRマージ後の削除

```bash
# メインに戻る
cd /home/rozwer/案件

# worktree 削除
git worktree remove ".worktrees/$TOPIC"

# リモートブランチ削除（マージ済みの場合）
git push origin --delete "feat/$TOPIC"

# ローカルブランチ削除
git branch -d "feat/$TOPIC"
```

#### 4. 一括確認

```bash
# 全 worktree の状態確認
for wt in .worktrees/*/; do
  echo "=== $wt ==="
  git -C "$wt" status -sb
done
```

---

## 並列開発パターン（ROADMAP準拠）

### Step 1: LLM クライアント（3並列）

```bash
# 同時に3つの worktree を作成
for topic in llm-gemini llm-openai llm-anthropic; do
  git worktree add -b "feat/$topic" ".worktrees/$topic" develop
done
```

| Worktree                    | 担当                   | 成果物                      |
| --------------------------- | ---------------------- | --------------------------- |
| `.worktrees/llm-gemini/`    | Gemini クライアント    | `apps/api/llm/gemini.py`    |
| `.worktrees/llm-openai/`    | OpenAI クライアント    | `apps/api/llm/openai.py`    |
| `.worktrees/llm-anthropic/` | Anthropic クライアント | `apps/api/llm/anthropic.py` |

**衝突回避**: 各クライアントは独立したファイル。共通インターフェース（`base.py`）は先に develop で確定。

### Step 3: ツール群（4並列）

```bash
for topic in tools-search tools-fetch tools-verify tools-registry; do
  git worktree add -b "feat/$topic" ".worktrees/$topic" develop
done
```

| Worktree                     | 担当                    | 成果物                       |
| ---------------------------- | ----------------------- | ---------------------------- |
| `.worktrees/tools-search/`   | SERP, Search Volume     | `apps/api/tools/search.py`   |
| `.worktrees/tools-fetch/`    | Page Fetch, PDF Extract | `apps/api/tools/fetch.py`    |
| `.worktrees/tools-verify/`   | URL Verify, Evidence    | `apps/api/tools/verify.py`   |
| `.worktrees/tools-registry/` | Tool Manifest           | `apps/api/tools/registry.py` |

### Step 4: 契約基盤（3並列）

```bash
for topic in contract-state contract-context contract-adapter; do
  git worktree add -b "feat/$topic" ".worktrees/$topic" develop
done
```

---

## マージ戦略

### 基本ルール

1. **Squash Merge** を推奨（履歴をクリーンに）
2. **PR必須**（直接 develop への push 禁止）
3. **smoke テスト必須**（マージ前に `/dev:smoke` 通過）

### マージ順序（依存関係考慮）

```
Step 1 完了後:
  feat/llm-gemini    → develop
  feat/llm-openai    → develop
  feat/llm-anthropic → develop

Step 3 完了後（Step 1 マージ済みが前提）:
  feat/tools-registry → develop  # 先にマージ（他が参照）
  feat/tools-search   → develop
  feat/tools-fetch    → develop
  feat/tools-verify   → develop
```

### コンフリクト解決

```bash
# develop を取り込む
cd ".worktrees/$TOPIC"
git fetch origin
git rebase origin/develop

# コンフリクト解決後
git rebase --continue
git push --force-with-lease
```

---

## サブエージェント分担

### Claude Code（主実装）

```
┌─────────────────────────────────────────────────────────┐
│ メインセッション（develop）                              │
│  ├── 設計決定、契約定義                                  │
│  ├── 共通インターフェース作成                            │
│  └── マージ統合                                          │
├─────────────────────────────────────────────────────────┤
│ サブエージェント1（worktree: llm-gemini）               │
│  └── Gemini クライアント実装                            │
├─────────────────────────────────────────────────────────┤
│ サブエージェント2（worktree: llm-openai）               │
│  └── OpenAI クライアント実装                            │
├─────────────────────────────────────────────────────────┤
│ サブエージェント3（worktree: llm-anthropic）            │
│  └── Anthropic クライアント実装                         │
└─────────────────────────────────────────────────────────┘
```

### Codex（レビュー・調査）

| 役割                 | 呼び出しタイミング |
| -------------------- | ------------------ |
| コードレビュー       | PR作成前           |
| 設計レビュー         | 新規機能設計時     |
| セキュリティレビュー | 認証・入力処理時   |

---

## チェックリスト

### Worktree 作成時

- [ ] develop が最新か確認（`git pull origin develop`）
- [ ] ブランチ命名規則に従っているか
- [ ] 担当範囲が明確か（ファイル衝突なし）

### PR作成時

- [ ] smoke テスト通過
- [ ] 型チェック通過（`mypy`）
- [ ] コミットメッセージが Conventional Commits 形式
- [ ] 依存するブランチがマージ済みか

### マージ後

- [ ] worktree 削除
- [ ] リモートブランチ削除
- [ ] ローカルブランチ削除

---

## トラブルシューティング

### Q: worktree が既に存在するエラー

```bash
fatal: 'feat/xxx' is already checked out at '...'
```

**解決**:

```bash
git worktree list  # どこで使われているか確認
git worktree remove ".worktrees/xxx"  # 削除
```

### Q: worktree でのコンフリクト

```bash
cd ".worktrees/$TOPIC"
git stash
git rebase origin/develop
git stash pop
# 手動でコンフリクト解決
```

### Q: 間違えて main にコミットした

```bash
# コミットを develop に移動
git checkout develop
git cherry-pick <commit-hash>
git checkout main
git reset --hard origin/main
```

---

## 参考リンク

- [Git worktree 公式ドキュメント](https://git-scm.com/docs/git-worktree)
- [Conventional Commits](https://www.conventionalcommits.org/)
- awakia氏「Gitで並列開発が楽になるブランチモデル」
