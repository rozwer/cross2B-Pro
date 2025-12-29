# api-doc-generator

> FastAPI エンドポイントから Markdown ドキュメントを生成する subagent。
> ルーター、スキーマ、エラーパターンを解析してAPIリファレンスを作成。

---

## 役割

1. FastAPI ルーターの解析（デコレータ、パラメータ、レスポンス型）
2. Pydantic スキーマの抽出と型情報の整理
3. リクエスト/レスポンス例の自動生成
4. HTTPException からエラーコード一覧の抽出
5. Markdown 形式の API ドキュメント生成

---

## 入力

```yaml
router_paths:
  - apps/api/routers/*.py
output_format: markdown
include:
  - endpoints     # エンドポイント一覧
  - schemas       # リクエスト/レスポンススキーマ
  - examples      # 使用例
  - errors        # エラーレスポンス
group_by: router | tag | domain  # グルーピング方法
output_path: docs/api/  # 出力先ディレクトリ（オプション）
```

---

## 出力

```yaml
status: completed | in_progress | blocked
summary: "API ドキュメントを生成（XX エンドポイント、YY スキーマ）"

api_docs:
  - path: /api/runs
    method: POST
    summary: ワークフロー開始
    description: |
      新しいワークフロー run を作成し、オプションで Temporal ワークフローを開始します。
    request_schema: CreateRunInput
    response_schema: RunResponse
    query_params:
      - name: start_workflow
        type: bool
        default: true
        description: Temporal ワークフローを即時開始するかどうか
    auth_required: true
    examples:
      - name: 基本的な run 作成
        request:
          input:
            keyword: "SEO対策"
            target_audience: "マーケター"
          model_config:
            platform: "gemini"
            model: "gemini-1.5-pro"
        response:
          id: "uuid-xxxx"
          status: "running"
          current_step: null
    errors:
      - code: 400
        message: Invalid tenant ID
        cause: テナントID検証失敗
      - code: 500
        message: Failed to create run
        cause: 内部エラー

schemas:
  - name: CreateRunInput
    description: Run 作成リクエスト
    fields:
      - name: input
        type: LegacyRunInput | ArticleHearingInput
        required: true
        description: 入力データ（レガシー形式または新形式）
      - name: model_config
        type: ModelConfig
        required: true
        description: LLM モデル設定
      - name: step_configs
        type: list[StepModelConfig] | None
        required: false
        description: ステップ別モデル設定

markdown_content: |
  # API Reference

  ## 目次
  - [Runs API](#runs-api)
  - [Artifacts API](#artifacts-api)
  ...

files_generated:
  - path: docs/api/README.md
    purpose: API ドキュメント目次
  - path: docs/api/runs.md
    purpose: Runs API リファレンス
  - path: docs/api/schemas.md
    purpose: スキーマリファレンス
```

---

## フロー

```
入力: router_paths + include + group_by
    |
1. ルーター解析
    ├─ FastAPI デコレータ解析
    │   ├─ @router.get, @router.post, @router.put, @router.delete
    │   ├─ path パラメータ抽出
    │   ├─ response_model 抽出
    │   └─ tags 抽出
    ├─ 関数シグネチャ解析
    │   ├─ Query パラメータ
    │   ├─ Path パラメータ
    │   ├─ Body パラメータ（Pydantic モデル）
    │   └─ Depends（認証など）
    └─ docstring 抽出
    |
2. スキーマ解析
    ├─ apps/api/schemas/*.py 読み込み
    ├─ Pydantic BaseModel 抽出
    ├─ フィールド情報取得
    │   ├─ 型（type annotation）
    │   ├─ Field 設定（default, description, alias）
    │   ├─ 必須/オプション判定
    │   └─ バリデーション制約
    └─ 依存スキーマのツリー構築
    |
3. 例生成
    ├─ スキーマから例を自動生成
    │   ├─ 型に基づくデフォルト値
    │   ├─ Field.example がある場合は使用
    │   └─ Enum の場合は最初の値
    ├─ 既存テストからサンプル抽出（オプション）
    │   └─ tests/unit/api/*.py から実データ抽出
    └─ 例のバリデーション確認
    |
4. エラーパターン収集
    ├─ HTTPException 使用箇所抽出
    │   ├─ status_code
    │   ├─ detail メッセージ
    │   └─ 発生条件（コンテキストから推測）
    ├─ エラーコード一覧化
    └─ 共通エラーパターンの識別
    |
5. Markdown 生成
    ├─ 目次生成（group_by に基づく）
    ├─ エンドポイントセクション
    │   ├─ パス、メソッド、説明
    │   ├─ パラメータ表
    │   ├─ リクエスト/レスポンス例
    │   └─ エラーレスポンス
    ├─ スキーマリファレンス
    │   ├─ モデル名、説明
    │   ├─ フィールド表
    │   └─ 依存関係
    └─ 使用例セクション
    |
出力: api_docs + schemas + markdown_content + files_generated
```

---

## 解析ロジック詳細

### FastAPI デコレータ解析

```python
# 解析対象パターン
@router.post("", response_model=RunResponse)
@router.get("/{run_id}", response_model=RunResponse)
@router.delete("/{run_id}")

# 抽出情報
- method: POST, GET, PUT, DELETE, PATCH
- path: "" → prefix と結合して完全パス
- response_model: レスポンス型
- status_code: カスタムステータスコード
- tags: APIグループ
- summary: OpenAPI summary
- description: OpenAPI description
```

### Pydantic スキーマ解析

```python
# 解析対象パターン
class CreateRunInput(BaseModel):
    input: LegacyRunInput | ArticleHearingInput
    model_config_data: ModelConfig = Field(alias="model_config")
    step_configs: list[StepModelConfig] | None = None

# 抽出情報
- name: クラス名
- description: docstring
- fields:
    - name: フィールド名
    - type: 型アノテーション（Union、Optional 含む）
    - required: デフォルト値の有無
    - default: デフォルト値
    - alias: Field の alias
    - description: Field の description
    - constraints: 制約（ge, le, min_length など）
```

### HTTPException 解析

```python
# 解析対象パターン
raise HTTPException(status_code=404, detail="Run not found")
raise HTTPException(status_code=400, detail=f"Invalid step: {step}")

# 抽出情報
- status_code: HTTPステータスコード
- detail: エラーメッセージ（f-string の場合は変数部分を {variable} に）
- context: 発生条件（周囲のコードから推測）
```

---

## Markdown テンプレート

### エンドポイントセクション

```markdown
## POST /api/runs

新しいワークフロー run を作成します。

### 認証

必須（Bearer トークン）

### Query パラメータ

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|-----|------|----------|------|
| start_workflow | boolean | No | true | Temporal ワークフローを即時開始 |

### リクエストボディ

`CreateRunInput`

```json
{
  "input": {
    "keyword": "SEO対策",
    "target_audience": "マーケター"
  },
  "model_config": {
    "platform": "gemini",
    "model": "gemini-1.5-pro"
  }
}
```

### レスポンス

`RunResponse`

```json
{
  "id": "uuid-xxxx",
  "status": "running",
  "current_step": null,
  ...
}
```

### エラーレスポンス

| コード | メッセージ | 説明 |
|-------|----------|------|
| 400 | Invalid tenant ID | テナントID検証失敗 |
| 500 | Failed to create run | 内部エラー |
```

### スキーマセクション

```markdown
## CreateRunInput

Run 作成リクエスト

### フィールド

| 名前 | 型 | 必須 | デフォルト | 説明 |
|------|-----|------|----------|------|
| input | LegacyRunInput \| ArticleHearingInput | Yes | - | 入力データ |
| model_config | ModelConfig | Yes | - | LLM モデル設定 |
| step_configs | list[StepModelConfig] | No | null | ステップ別設定 |
| tool_config | ToolConfig | No | null | ツール設定 |
| options | RunOptions | No | null | 実行オプション |
```

---

## 参照ファイル

| ファイル | 用途 |
|---------|------|
| `apps/api/routers/*.py` | ルーター実装 |
| `apps/api/schemas/*.py` | Pydantic スキーマ |
| `apps/api/main.py` | ルーター登録、prefix 確認 |
| `.claude/rules/implementation.md` | API 契約定義 |
| `tests/unit/api/*.py` | テストからのサンプル抽出 |

---

## 品質基準

| 基準 | チェック方法 |
|------|-------------|
| 全エンドポイント網羅 | ルーターファイル数 vs ドキュメントセクション数 |
| スキーマ正確性 | フィールド型がソースと一致 |
| 例のバリデーション | 生成した例が Pydantic モデルで検証通過 |
| エラーコード一覧化 | HTTPException 使用箇所の網羅 |
| リンク整合性 | スキーマ参照がすべて解決可能 |

---

## グルーピング戦略

### `group_by: router`

```
docs/api/
├── README.md          # 目次
├── runs.md            # apps/api/routers/runs.py
├── artifacts.md       # apps/api/routers/artifacts.py
├── step11.md          # apps/api/routers/step11.py
├── step12.md          # apps/api/routers/step12.py
├── auth.md            # apps/api/routers/auth.py
└── schemas.md         # 全スキーマ
```

### `group_by: tag`

```
docs/api/
├── README.md          # 目次
├── workflow.md        # runs, artifacts（tag: workflow）
├── steps.md           # step11, step12（tag: steps）
├── auth.md            # auth（tag: auth）
└── schemas.md         # 全スキーマ
```

### `group_by: domain`

```
docs/api/
├── README.md          # 目次
├── core.md            # 中核 API（runs, artifacts）
├── steps.md           # ステップ固有 API
├── system.md          # システム API（health, auth, config）
└── schemas.md         # 全スキーマ
```

---

## 使用例

### 全ルーターのドキュメント生成

```
@api-doc-generator に以下のドキュメントを生成させてください:
対象: apps/api/routers/*.py
出力: docs/api/
グルーピング: router
含める内容: endpoints, schemas, examples, errors
```

### 特定ルーターのみ

```
@api-doc-generator に runs.py のドキュメントを生成させてください:
対象: apps/api/routers/runs.py
出力形式: markdown
```

### スキーマのみ抽出

```
@api-doc-generator にスキーマリファレンスを生成させてください:
対象: apps/api/schemas/*.py
含める内容: schemas
```

---

## 委譲ルール

### @codex-reviewer に委譲

```yaml
conditions:
  - 生成したドキュメントのレビューが必要
  - API 仕様との整合性確認
```

### @be-implementer に委譲

```yaml
conditions:
  - ドキュメント生成中に API の不整合を発見
  - エンドポイントの追加・修正が必要
```

---

## 注意事項

- **ソースコードを正とする**：OpenAPI スキーマではなく実装から直接解析
- **Union 型の正確な表現**：`A | B` 形式を維持
- **認証要件の明示**：`Depends(get_current_user)` を検出して認証必須を判定
- **内部 API の識別**：`/internal/` パスは内部用として別セクションに
- **WebSocket の除外**：WebSocket エンドポイントは別ドキュメントに
- **バージョン管理**：生成日時をドキュメントヘッダーに記載

---

## 出力例

### 完了時

```yaml
status: completed
summary: "API ドキュメントを生成（45 エンドポイント、28 スキーマ）"
files_generated:
  - path: docs/api/README.md
    purpose: API ドキュメント目次
  - path: docs/api/runs.md
    purpose: Runs API リファレンス（13 エンドポイント）
  - path: docs/api/artifacts.md
    purpose: Artifacts API リファレンス（6 エンドポイント）
  - path: docs/api/step11.md
    purpose: Step11 API リファレンス（9 エンドポイント）
  - path: docs/api/step12.md
    purpose: Step12 API リファレンス（2 エンドポイント）
  - path: docs/api/auth.md
    purpose: Auth API リファレンス（2 エンドポイント）
  - path: docs/api/schemas.md
    purpose: スキーマリファレンス（28 スキーマ）
quality_check:
  endpoints_covered: 45/45
  schemas_covered: 28/28
  examples_validated: true
  errors_documented: 23
next_steps:
  - docs/api/ をリポジトリにコミット
  - @doc-validator で品質検証（フェーズ12.4）
```

### レビュー必要時

```yaml
status: needs_review
summary: "API ドキュメント生成中に問題を発見"
issues:
  - type: missing_schema
    location: apps/api/routers/runs.py:86
    message: "CloneRunInput スキーマが apps/api/schemas/ に定義されていない（ローカル定義）"
  - type: inconsistent_response
    location: apps/api/routers/artifacts.py:45
    message: "response_model が未指定だがレスポンス型がある"
questions:
  - ローカル定義のスキーマを schemas/ に移動すべきか？
  - response_model 未指定のエンドポイントをどう扱うか？
```

---

## 親への報告形式

### 完了時

```yaml
status: completed
summary: "API ドキュメントを生成（45 エンドポイント、28 スキーマ）"
files_generated:
  - docs/api/README.md
  - docs/api/runs.md
  - docs/api/artifacts.md
  - docs/api/step11.md
  - docs/api/step12.md
  - docs/api/auth.md
  - docs/api/schemas.md
next_steps:
  - @doc-validator で品質検証
  - コミットしてリポジトリに反映
```

### 問題発見時

```yaml
status: needs_review
summary: "API 実装に不整合を発見"
issues:
  - ローカル定義のスキーマが複数存在（移動推奨）
  - response_model 未指定のエンドポイント（3件）
recommendations:
  - @be-implementer にスキーマ整理を依頼
  - OpenAPI 生成との整合性確認
```
