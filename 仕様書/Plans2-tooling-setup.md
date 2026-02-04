# 開発ツール導入計画

> 補助システム（mise, delta, Biome, lefthook）の導入計画

## 概要

| 項目 | 内容 |
|------|------|
| 目的 | 開発体験向上、ツールチェーン統一、Git hooks の YAML 化 |
| スコープ | システムツール（mise, delta）+ プロジェクトツール（Biome, lefthook） |
| リスク | 中（既存 ESLint / .githooks との共存・移行が必要） |
| Codex 判定 | REJECT → 修正中（P1/P2 対応） |

---

## Codex 指摘事項と修正方針

### P1 (Critical) - 修正済み

| 指摘 | 修正方針 |
|------|---------|
| Biome コマンドのパス問題（`cd apps/ui` 後に repo ルート相対パスを渡すと解決不能） | `cd` をやめて repo ルートで実行、`--config-path apps/ui/biome.json` を指定 |
| `python3 -m json.tool` が複数ファイル非対応 | `for` ループで個別実行に変更 |

### P2 (High) - 修正済み

| 指摘 | 修正方針 |
|------|---------|
| `ruff --fix` 後に再ステージが走らない | `stage_fixed: true` オプションを追加 |
| `mypy || true` / `tsc || true` で失敗を黙殺 | Phase 1 の暫定措置と明記、CI で必須化する計画を追加 |

### P3 (Medium) - 修正済み

| 指摘 | 修正方針 |
|------|---------|
| mise activate 手順が未記載 | シェル別のアクティベート手順を追加 |
| `git config --unset core.hooksPath` の scope 不明 | `--local` を明示 |
| OS 別インストール手順が不足 | macOS/Linux/WSL の手順を明記 |

---

## フェーズ1: システムツール導入 `cc:TODO`

### 1.1 mise インストール

**OS 別インストール手順**:
```bash
# 全 OS 共通（推奨）
curl https://mise.run | sh

# macOS（Homebrew）
brew install mise

# Ubuntu/Debian
apt install -y gpg sudo wget curl
sudo install -dm 755 /etc/apt/keyrings
wget -qO - https://mise.jdx.dev/gpg-key.pub | gpg --dearmor | sudo tee /etc/apt/keyrings/mise-archive-keyring.gpg 1> /dev/null
echo "deb [signed-by=/etc/apt/keyrings/mise-archive-keyring.gpg arch=amd64] https://mise.jdx.dev/deb stable main" | sudo tee /etc/apt/sources.list.d/mise.list
sudo apt update && sudo apt install -y mise
```

**シェル別アクティベート手順**（`~/.bashrc` or `~/.zshrc` に追加）:
```bash
# bash
echo 'eval "$(mise activate bash)"' >> ~/.bashrc

# zsh
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc

# fish
echo 'mise activate fish | source' >> ~/.config/fish/config.fish
```

- [ ] mise をインストール
- [ ] シェルにアクティベート設定を追加
- [ ] `.mise.toml` を作成（Python 3.12, Node 22, bun 1.3）
- [ ] `mise install` で各ツールをインストール
- [ ] `scripts/bootstrap.sh` に `mise install` を追加
- [ ] `.gitignore` に `.mise.local.toml` を追加

**設定ファイル** (`.mise.toml`):
```toml
[tools]
python = "3.12"
node = "22"
bun = "1.3"
```

### 1.2 delta インストール

**OS 別インストール手順**:
```bash
# macOS（Homebrew）
brew install git-delta

# Ubuntu/Debian
sudo apt install git-delta

# Cargo（全 OS）
cargo install git-delta

# Windows (Scoop)
scoop install delta
```

- [ ] delta をインストール
- [ ] `~/.gitconfig` に pager 設定を追加
- [ ] ドキュメントに opt-in として案内

**gitconfig 追記**:
```ini
[core]
    pager = delta
[interactive]
    diffFilter = delta --color-only
[delta]
    navigate = true
    side-by-side = true
    line-numbers = true
```

---

## フェーズ2: Biome 導入（apps/ui） `cc:TODO`

### 2.1 Biome インストール

```bash
cd apps/ui && npm install -D @biomejs/biome
```

- [ ] `@biomejs/biome` をインストール
- [ ] `apps/ui/biome.json` を作成
- [ ] `package.json` に scripts を追加
- [ ] ESLint は Next.js ルール用に残す（共存）

**設定ファイル** (`apps/ui/biome.json`):
```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.0/schema.json",
  "organizeImports": { "enabled": true },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2
  },
  "linter": {
    "enabled": false
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "double",
      "semicolons": "always"
    }
  }
}
```

**package.json 変更**:
```json
{
  "scripts": {
    "format": "biome format --write .",
    "format:check": "biome check ."
  }
}
```

**移行方針**:
- Phase 1: formatter のみ有効化（linter は無効）
- Phase 2: 段階的に lint ルールを有効化（将来）
- ESLint は `next lint` として残す

---

## フェーズ3: lefthook 導入 `cc:TODO`

### 3.1 lefthook インストール

```bash
npm install -D lefthook
npx lefthook install
```

- [ ] `lefthook` をインストール（root package.json）
- [ ] `lefthook.yml` を作成（既存 hooks を移植）
- [ ] `scripts/bootstrap.sh` に `npx lefthook install` を追加
- [ ] 動作確認後、`.githooks/` を削除
- [ ] `git config --local --unset core.hooksPath` で旧設定をクリア（`--local` 明示）

**設定ファイル** (`lefthook.yml`):
```yaml
# lefthook.yml - Git hooks configuration
# Migrated from .githooks/

pre-commit:
  parallel: true
  commands:
    # 秘密情報検出（カスタムスクリプト）
    secrets:
      run: bash .lefthook/check-secrets.sh {staged_files}
      glob: "*"

    # Python: ruff lint + format（修正後に自動再ステージ）
    ruff-check:
      glob: "*.py"
      run: ruff check {staged_files} --fix
      stage_fixed: true
    ruff-format:
      glob: "*.py"
      run: ruff format {staged_files}
      stage_fixed: true

    # Python: mypy（Phase 1: 警告のみ、CI で必須化予定）
    mypy:
      glob: "*.py"
      run: mypy {staged_files} --ignore-missing-imports || true
      # TODO: Phase 2 で || true を削除し、CI でも必須化

    # TypeScript: Biome format（repo ルートから実行、config-path 指定）
    biome:
      glob: "apps/ui/**/*.{ts,tsx}"
      run: npx biome format --write --config-path apps/ui/biome.json {staged_files}
      stage_fixed: true

    # TypeScript: tsc（Phase 1: 警告のみ、CI で必須化予定）
    tsc:
      root: "apps/ui"
      glob: "*.{ts,tsx}"
      run: npx tsc --noEmit || true
      # TODO: Phase 2 で || true を削除し、CI でも必須化

    # JSON 検証（複数ファイル対応: for ループ）
    json:
      glob: "*.json"
      run: |
        for f in {staged_files}; do
          python3 -m json.tool "$f" > /dev/null || exit 1
        done

prepare-commit-msg:
  commands:
    prefix:
      run: bash .lefthook/prepare-commit-msg.sh {1}

commit-msg:
  commands:
    conventional:
      run: bash .lefthook/commit-msg.sh {1}

pre-push:
  commands:
    # main/master 直 push 禁止
    protected-branch:
      run: bash .lefthook/check-protected-branch.sh

    # smoke テスト
    smoke:
      run: uv run pytest tests/smoke/ -q --tb=no || echo "Smoke tests skipped"
```

**Phase 2 での解除計画**:
- `mypy || true` → `|| true` を削除、CI の `mypy` ジョブを必須化
- `tsc || true` → `|| true` を削除、CI の `tsc` ジョブを必須化
- 時期: Biome lint ルール有効化と同時（全員の開発環境が安定した後）

### 3.2 ヘルパースクリプト移行

既存 `.githooks/` のロジックを `.lefthook/` に移植:

- [ ] `.lefthook/check-secrets.sh` - 秘密情報検出
- [ ] `.lefthook/prepare-commit-msg.sh` - プレフィックス自動生成
- [ ] `.lefthook/commit-msg.sh` - Conventional Commits 検証
- [ ] `.lefthook/check-protected-branch.sh` - 保護ブランチチェック

---

## フェーズ4: ドキュメント・CI 更新 `cc:TODO`

- [ ] `docs/guides/TOOLING.md` を作成（bootstrap 手順）
- [ ] `scripts/bootstrap.sh` を更新
- [ ] `.claude/CLAUDE.md` に新ツールを追記
- [ ] CI に commit-msg / pre-push 相当のチェックを追加（将来）

---

## リスク・移行計画

### Biome + ESLint 共存

| 責務 | ツール | 理由 |
|------|--------|------|
| フォーマット | Biome | 高速、設定シンプル |
| Lint（汎用） | Biome（将来） | 段階的移行 |
| Lint（Next.js） | ESLint | Next.js 固有ルール |

**注意**: 同一ファイルに両方の formatter を適用しない

### lefthook 移行

1. `lefthook.yml` 作成
2. 既存 hooks と並行稼働（テスト）
3. 動作確認後、`.githooks/` 削除
4. `core.hooksPath` 設定をクリア

---

## 実行コマンド一覧

```bash
# 1. mise
curl https://mise.run | sh
mise install

# 2. delta
sudo apt install git-delta  # または cargo install git-delta

# 3. Biome
cd apps/ui && npm install -D @biomejs/biome

# 4. lefthook
npm install -D lefthook
npx lefthook install
```

---

## チェックリスト

- [x] インストール対象を JSON でリストアップ
- [x] 既存設定との整合性を調査
- [x] Codex に導入計画の確認を依頼（初回: APPROVE）
- [x] Codex 再レビュー（REJECT → P1/P2/P3 修正）
- [x] **Codex 再レビュー（修正版で APPROVE 取得）** ✅
- [ ] **ユーザー承認を取得**
- [ ] インストール実行

---

## Codex 最終レビュー結果

**判定: APPROVE** ✅

**軽微な指摘（対応推奨）**:
- `for f in {staged_files}` はスペース含むファイル名で問題が起きる可能性あり
- 対策: `IFS` + `read` を使うか、lefthook の `files` 変数を使用

→ 本プロジェクトではスペース含むファイル名は使用しない前提で進行可
