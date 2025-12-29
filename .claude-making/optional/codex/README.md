# Codex Integration (Optional)

OpenAI Codex CLI をセカンドオピニオンとして活用するための設定。

## 有効化

`options.json` で `use_codex: true` を設定すると、このディレクトリの内容がコピーされます。

```json
{
  "use_codex": true
}
```

## 含まれるファイル

| ファイル | 説明 |
|----------|------|
| `rules/codex-integration.md` | Codex CLI の使用ガイドライン |
| `agents/codex-reviewer.md` | セルフレビュー用 subagent |
| `commands/review/codex-review.md` | レビューコマンド |

## 前提条件

Codex CLI がインストール済みで、以下の設定が必要：

```
.codex/
├── env.sh          # 環境変数（APIキー等）
├── config.toml     # 設定ファイル
└── instructions.md # カスタム指示（オプション）
```

## 使い方

1. `source .codex/env.sh` で環境変数を読み込み
2. `@codex-reviewer` を呼び出してレビュー実行
3. または `/review:codex-review` コマンドを使用

## 注意

- Codex CLI は別途インストールが必要
- API キーの設定が必要
- Claude Code とは独立した AI エンジンを使用
