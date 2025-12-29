# SEO記事自動生成システム - 開発ガイド

> **Claude Code (Impl)** が開発を担当するプロジェクトです。

## プロジェクト概要

| 項目 | 内容 |
|------|------|
| **目的** | SEO記事の自動生成ワークフローシステム |
| **技術スタック** | Python (FastAPI + Temporal + LangGraph) / Next.js |
| **インフラ** | Docker Compose (Postgres + MinIO + Temporal) |

---

## 開発ワークフロー

### Solo モード

```
ユーザー → Claude Code (Impl)
    ↓
Plan → Work → Review → Commit
```

### コマンド早見表

| やりたいこと | コマンド |
|-------------|---------|
| 計画を立てる | `/plan-with-agent` |
| 作業を開始 | `/work` |
| 状態確認 | `/sync-status` |
| 環境起動 | `/dev:up` |
| 環境停止 | `/dev:down` |

---

## Source of Truth

| 用途 | ファイル |
|------|---------|
| **最高優先指示** | `.claude/CLAUDE.md` |
| **実装計画** | `仕様書/ROADMAP.md` |
| **ワークフロー** | `仕様書/workflow.md` |
| **タスク管理** | `Plans.md` |

---

## 主要サブエージェント

| エージェント | 用途 |
|-------------|------|
| `@architect` | 設計判断・分割方針 |
| `@be-implementer` | Backend 実装 |
| `@fe-implementer` | Frontend 実装 |
| `@codex-reviewer` | コードレビュー |
| `@security-reviewer` | セキュリティ監査 |
| `@temporal-debugger` | Temporal デバッグ |

---

## 重要ルール（抜粋）

### フォールバック禁止

```
❌ 禁止：別モデル/別プロバイダ/別ツールへの自動切替
✅ 許容：同一条件でのリトライ（上限3回）
```

### アーキテクチャ原則

- **Temporal** = 実行の正（待機/再開/リトライ）
- **LangGraph** = 工程ロジック（プロンプト/整形/検証）
- **重い成果物は storage** に保存（path/digest 参照のみ）

### コミット方針

```
✅ Conventional Commits 形式
✅ 一区切りごとにコミット
✅ 大きな変更は分割
```

---

## クイックスタート

```bash
# 環境起動
/dev:up

# ヘルスチェック
/dev:health

# ワークフロー開始
/workflow:new-run
```

---

## 詳細情報

- 詳細なルール → `.claude/CLAUDE.md`
- 実装詳細 → `.claude/rules/implementation.md`
- 開発スタイル → `.claude/rules/dev-style.md`
