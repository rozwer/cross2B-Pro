---
name: codebase-explore
description: コードベース調査を標準 Explore subagent または Codex に委譲する skill
---

# Codebase Explore

> コード調査、依存分析、パターン抽出を行う skill。
> 単純な検索は標準 Explore subagent、複雑な調査は Codex に委譲する。

---

## 役割

コードベースの調査を効率的に行うためのラッパー skill。
調査の複雑度に応じて適切なツールを選択する。

---

## 入力

```yaml
target: ""           # 調査対象（機能、モジュール、パターン）
type: search | analyze | dependencies | patterns
depth: quick | medium | thorough
context: ""          # 追加コンテキスト（オプション）
```

---

## 出力

```yaml
status: completed | delegated_to_codex
findings:
  files: []          # 関連ファイル一覧
  patterns: []       # 発見したパターン
  dependencies: []   # 依存関係
summary: ""          # 要約
recommendations: []  # 推奨事項
```

---

## フロー

```
入力: 調査対象
    ↓
1. 複雑度判定
    ├─ 単純な検索 → 標準 Explore subagent
    │    - ファイル検索
    │    - キーワード検索
    │    - 定義の特定
    │
    └─ 複雑な調査 → Codex exec
         - 複数モジュールにまたがる分析
         - アーキテクチャ理解
         - パターン抽出
    ↓
2. 結果をまとめて返却
```

---

## 複雑度判定基準

| 複雑度 | 条件 | 使用ツール |
|--------|------|-----------|
| **単純** | キーワード検索、ファイル特定 | Explore subagent |
| **中程度** | 複数ファイルの関連調査 | Explore subagent |
| **複雑** | アーキテクチャ分析、パターン抽出 | Codex exec |

### 単純な検索の例

- 「〇〇の定義はどこ？」
- 「△△を使っているファイルは？」
- 「□□モジュールの構造は？」

### 複雑な調査の例

- 「認証フローの全体像を把握したい」
- 「エラーハンドリングのパターンを抽出」
- 「Temporal と LangGraph の連携方法を理解」

---

## 使用方法

### 標準 Explore subagent を使う場合

Task ツールで Explore subagent を呼び出す:

```
Task(
  subagent_type: "Explore",
  prompt: "{{target}} について調査してください。depth: {{depth}}",
  description: "Codebase exploration"
)
```

### Codex に委譲する場合

```bash
source .codex/env.sh
codex exec "
コードベース調査を依頼します。

## 調査対象
{{target}}

## 調査タイプ
{{type}}

## 出力形式
1. 関連ファイル一覧
2. 発見したパターン
3. 依存関係
4. 要約と推奨事項
"
```

---

## 調査タイプ別ガイドライン

### search: ファイル/コード検索

```yaml
使用ツール: Explore subagent
手順:
  1. Glob でファイルパターン検索
  2. Grep でキーワード検索
  3. Read で詳細確認
```

### analyze: コード分析

```yaml
使用ツール: 複雑度による
単純: Explore subagent（関数/クラスの構造理解）
複雑: Codex（設計意図、問題点の分析）
```

### dependencies: 依存関係調査

```yaml
使用ツール: Explore subagent
手順:
  1. import 文の追跡
  2. 呼び出し元/呼び出し先の特定
  3. 依存グラフの構築
```

### patterns: パターン抽出

```yaml
使用ツール: Codex（ほぼ常に）
理由: パターン抽出は高度な分析が必要
```

---

## 出力例

### 単純な検索結果

```yaml
status: completed
findings:
  files:
    - apps/api/routers/runs.py
    - apps/api/schemas/runs.py
    - apps/worker/activities/base.py
  patterns: []
  dependencies:
    - runs.py → schemas/runs.py
    - runs.py → services/runs.py
summary: "runs 関連のファイルは3つ見つかりました"
recommendations:
  - "runs.py がエントリーポイントです"
```

### 複雑な調査結果（Codex 委譲）

```yaml
status: delegated_to_codex
codex_query: |
  Temporal と LangGraph の連携方法を調査
  - ワークフロー定義の場所
  - Activity の呼び出しパターン
  - 状態管理の方法
summary: "Codex による詳細分析を実施中"
```

---

## 呼び出し例

### 単純な検索

```
codebase-explore で「認証」に関するファイルを探してください
```

```
codebase-explore で step10.py の依存関係を調査してください
```

### 複雑な調査

```
codebase-explore でエラーハンドリングのパターンを抽出してください
```

```
codebase-explore で Temporal ワークフローの全体像を把握してください
```

---

## 注意事項

- **大量のファイルは分割**: 100ファイル以上の場合は範囲を絞る
- **depth を適切に設定**: quick は表面的、thorough は詳細
- **結果はキャッシュ可能**: 同じ調査は再利用を検討
