# 共通プロンプト（全セッション冒頭に含める）

---

````markdown
## 作業開始手順

### 1. Worktree作成（初回のみ）

```bash
cd /home/rozwer/案件
git fetch origin
git pull origin develop  # developを最新化

# Worktree作成
TOPIC="<ここにトピック名>"  # 例: llm-gemini, tools, validation
mkdir -p .worktrees
git worktree add -b "feat/$TOPIC" ".worktrees/$TOPIC" develop

# 作業ディレクトリへ移動
cd ".worktrees/$TOPIC"
````

### 2. 作業ディレクトリ確認

```bash
pwd  # /home/rozwer/案件/.worktrees/<TOPIC> であること
git branch  # feat/<TOPIC> にいること
```

### 3. 完了後の手順

```bash
# コミット（Conventional Commits形式）
git add .
git commit -m "feat: <変更内容>"

# リモートへpush
git push -u origin "feat/$TOPIC"

# PR作成
gh pr create --base develop --title "feat: <タイトル>" --body "<説明>"
```

## 絶対ルール

1. **develop/mainへ直接push禁止** - 必ずPR経由
2. **フォールバック全面禁止** - 別モデル/別ツールへの自動切替禁止
3. **Conventional Commits必須** - `feat:`, `fix:`, `docs:` 等
4. **テスト必須** - 新機能には必ずテストを書く
5. **型チェック必須** - mypy/pyright が通ること

## ディレクトリ構造（作成するもの）

```
apps/
├── api/                 # FastAPI バックエンド
│   ├── __init__.py
│   ├── main.py
│   ├── llm/            # LLMクライアント
│   ├── tools/          # 外部ツール
│   ├── validation/     # 検証
│   ├── core/           # 契約基盤
│   ├── storage/        # ストレージ
│   ├── db/             # データベース
│   ├── observability/  # 観測
│   └── prompts/        # プロンプト
├── worker/              # Temporal Worker
│   ├── __init__.py
│   ├── workflows/
│   ├── activities/
│   └── graphs/         # LangGraph
└── ui/                  # Next.js フロントエンド
    ├── pages/
    ├── components/
    ├── hooks/
    └── lib/

tests/
├── unit/
├── integration/
└── e2e/
```

## 参照すべき仕様書

- `仕様書/ROADMAP.md` - 実装計画
- `仕様書/workflow.md` - ワークフロー定義
- `仕様書/backend/*.md` - バックエンド仕様
- `仕様書/frontend/ui.md` - フロントエンド仕様

```

```
