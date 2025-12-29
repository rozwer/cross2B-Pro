---
name: docs
description: API ドキュメント・README・技術仕様書を自動生成する
---

# docs

> ドキュメント生成のワークフローを自動化するスキル

---

## 使用方法

```bash
/docs [options]
```

---

## オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--type <type>` | 生成タイプ（readme / api / all） | all |
| `--target <path>` | 対象ディレクトリ | . |
| `--output <path>` | 出力先ディレクトリ | docs/ |
| `--force` | 既存ファイルを上書き | false |
| `--dry-run` | 実行せずプレビューのみ | false |

---

## 使用例

### 基本的な使い方

```bash
# 全てのドキュメントを生成（デフォルト）
/docs

# README のみ生成
/docs --type readme

# API ドキュメントのみ生成
/docs --type api

# 両方生成（明示的）
/docs --type all
```

### ディレクトリ指定

```bash
# 特定ディレクトリの README を生成
/docs --type readme --target apps/api

# Worker の API ドキュメント生成
/docs --type api --target apps/worker

# 出力先を指定
/docs --type all --output docs/generated
```

### 組み合わせ例

```bash
# apps/api の README を上書き生成
/docs --type readme --target apps/api --force

# ドライラン（生成内容をプレビュー）
/docs --type all --dry-run

# 特定ディレクトリの API ドキュメントを上書き
/docs --type api --target apps/api --force --output docs/api
```

---

## 実行フロー

```
1. オプション解析
   |- type 判定（readme / api / all）
   |- target 判定（デフォルト: .）
   |- output 判定（デフォルト: docs/）
   |- force / dry-run フラグ判定

2. Agent 呼び出し
   |- type=readme の場合
   |     └─ @readme-generator を呼び出し
   |- type=api の場合
   |     └─ @api-doc-generator を呼び出し
   |- type=all の場合
         |- @readme-generator を呼び出し
         └─ @api-doc-generator を呼び出し

3. ドキュメント生成
   |- target ディレクトリを解析
   |- コード構造・コメント・docstring を抽出
   └─ テンプレートに基づき生成

4. 結果を表示
   |- status: success / skipped / failed
   |- generated_files: 生成ファイル一覧
   |- summary: 生成内容の概要
   └─ warnings: 警告事項

5. ファイル出力（dry-run でない場合）
   |- README.md（type=readme / all）
   └─ API.md（type=api / all）
```

---

## 出力形式

### 成功時（success）

```
[OK] ドキュメント生成完了

[FILE] 生成ファイル:
  - docs/README.md
  - docs/API.md

[INFO] サマリー:
  README: プロジェクト概要、セットアップ手順、使用方法を生成
  API: 15 エンドポイント、3 スキーマを文書化

[OK] 2 ファイルを生成しました。
```

### スキップ時（skipped）

```
[SKIP] ドキュメント生成スキップ

[FILE] 既存ファイル:
  - docs/README.md（既存）
  - docs/API.md（既存）

[WARN] 既存ファイルをスキップしました。
[INFO] 上書きするには --force オプションを使用してください。
```

### ドライラン時

```
[DRY-RUN] ドキュメント生成プレビュー

[FILE] 生成予定:
  - docs/README.md（新規）
  - docs/API.md（上書き）

[INFO] プレビュー:
  README:
    - タイトル: SEO記事自動生成システム
    - セクション: 概要、セットアップ、使用方法、API、開発
  API:
    - エンドポイント数: 15
    - スキーマ数: 3
    - カテゴリ: runs, artifacts, step11, step12

[INFO] 実際に生成するには --dry-run を外してください。
```

### 失敗時（failed）

```
[NG] ドキュメント生成失敗

[NG] エラー:
  - target ディレクトリが見つかりません: apps/unknown

[INFO] 確認事項:
  - ディレクトリパスが正しいか確認してください
  - 読み取り権限があるか確認してください
```

---

## type オプション詳細

| 値 | 生成内容 | 呼び出す Agent |
|----|---------|---------------|
| `readme` | README.md（概要、セットアップ、使用方法） | @readme-generator |
| `api` | API.md（エンドポイント、スキーマ、使用例） | @api-doc-generator |
| `all` | 両方 | @readme-generator, @api-doc-generator |

### type の選び方

| 変更内容 | 推奨 type |
|---------|----------|
| 新規プロジェクト作成 | `all` |
| 機能追加・変更 | `readme` |
| API エンドポイント追加 | `api` |
| 大規模リファクタリング | `all` |
| ドキュメント更新のみ | 該当する type |

---

## 生成されるドキュメント

### README.md（type=readme）

```markdown
# {プロジェクト名}

## 概要
{プロジェクトの説明}

## セットアップ
{インストール手順}

## 使用方法
{基本的な使い方}

## 設定
{設定項目}

## 開発
{開発者向け情報}

## ライセンス
{ライセンス情報}
```

### API.md（type=api）

```markdown
# API ドキュメント

## エンドポイント一覧

### Runs
| メソッド | パス | 説明 |
|---------|------|------|
| POST | /api/runs | ワークフロー開始 |
| GET | /api/runs | 一覧取得 |
...

## スキーマ

### RunCreate
| フィールド | 型 | 必須 | 説明 |
|-----------|---|------|------|
| keyword | string | Yes | 検索キーワード |
...

## 使用例
{curl / Python / TypeScript の例}
```

---

## 関連

- **@readme-generator**: README 生成を担当する agent
- **@api-doc-generator**: API ドキュメント生成を担当する agent
- **@architect**: 設計ドキュメントのレビュー
- **/codebase-explore**: コードベース探索（ドキュメント生成の前準備）

---

## 推奨ワークフロー

```
1. コード変更を作成

2. /codebase-explore で構造を確認
   |- ディレクトリ構成
   |- 主要ファイル
   └─ 依存関係

3. /docs で ドキュメント生成
   |- --dry-run でプレビュー
   └─ 問題なければ生成

4. 生成されたドキュメントを確認
   |- 内容の正確性
   |- フォーマット
   └─ リンク切れ

5. 必要に応じて手動修正

6. git add && git commit
```

---

## 注意事項

- 既存ファイルは `--force` なしでは上書きされません
- 生成されたドキュメントは人間によるレビューを推奨します
- コード内のコメント・docstring が生成品質に影響します
- 大規模プロジェクトでは生成に時間がかかる場合があります
