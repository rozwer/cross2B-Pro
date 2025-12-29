# Claude Code セットアップ - 実行指示書

> **このドキュメントは Claude Code が読んで実行するための指示書である**

## 目的

対象プロジェクトに `.claude/` ディレクトリを構築し、Claude Code が効果的に動作する環境を整える。

---

## 実行フロー

```
Phase 1: プロジェクト分析
    │
    │  [実行内容]
    │  - 技術スタック調査（Backend/Frontend/DB/Infra）
    │  - ディレクトリ構造分析
    │  - 既存規約確認
    │  - options.json を生成
    │
    ↓
Phase 2: ディレクトリ作成
    │
    │  [実行内容]
    │  - .claude/{agents,commands/dev,hooks,rules,skills} 作成
    │
    ↓
Phase 3: テンプレートコピー
    │
    │  [実行内容]
    │  - .claude-making/template/ から .claude/ へコピー
    │  - 汎用ファイルのみ（プロジェクト非依存）
    │
    ↓
Phase 4: ブループリント展開
    │
    │  [実行内容]
    │  - blueprint/ のテンプレートを Phase 1 の結果で展開
    │  - {{VAR}} を実際の値に置換
    │  - CLAUDE.md, 専門スキル, 専門エージェント等を生成
    │
    ↓
Phase 5: 検証
    │
    │  [実行内容]
    │  - 構造確認
    │  - JSON構文チェック
    │  - フロントマター検証
```

---

## 各 Phase の参照先

| Phase | ドキュメント | 目的 |
|-------|-------------|------|
| 1 | [01-project-analysis.md](./01-project-analysis.md) | 何を調査し、どう整理するか |
| 2 | [02-structure-setup.md](./02-structure-setup.md) | どのディレクトリを作るか |
| 3 | [03-template-copy.md](./03-template-copy.md) | どのファイルをコピーするか |
| 4 | [04-blueprint-customize.md](./04-blueprint-customize.md) | どのテンプレートをどう展開するか |
| 5 | [05-validation.md](./05-validation.md) | 何をどう検証するか |

---

## 成果物

セットアップ完了後に生成されるもの：

```
{project-root}/
├── .claude/
│   ├── CLAUDE.md           # メイン指示書（プロジェクト固有）
│   ├── settings.json       # Claude Code 設定
│   ├── agents/             # サブエージェント定義
│   ├── commands/           # カスタムコマンド
│   │   └── dev/            # 開発系コマンド
│   ├── hooks/              # フック設定
│   ├── rules/              # 常時適用ルール
│   └── skills/             # ユーザー向けスキル
└── .codex/                 # (オプション) Codex CLI 設定
```

---

## 実行方法

### 方法1: スキル経由（推奨）

```
/setup-project
```

対話形式でプロジェクト情報を収集し、自動でセットアップを実行。

### 方法2: 手動実行

1. Phase 1 のドキュメントを読み、分析を実行
2. Phase 2 → 3 → 4 → 5 の順に実行
3. 各 Phase 完了後、次の Phase に進む

---

## 注意事項

- 各 Phase は前の Phase の結果に依存する
- Phase 1 で生成した options.json は Phase 4 で使用する
- エラーが発生した場合は、該当 Phase のドキュメントを参照
