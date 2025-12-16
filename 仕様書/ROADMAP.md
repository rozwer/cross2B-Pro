# SEO記事自動生成システム ロードマップ

> **運用前提**
> - 実装者：AI（主実装 ClaudeCode、コード調査・レビュー Codex）
> - 区切り：成果物（動く縦切り）+ ゲート条件（DoD）
> - 実装思想：分割実装→統合（境界・呼び出し・バリデーション・永続化・冪等性を先に固め、後から中身を埋める）
> - 並列実装：サブエージェント呼び出し + git worktree で衝突回避
> - **フォールバック全面禁止**：正常挙動以外は許可しない
> - ローカル運用固定：Postgres + MinIO + Temporal
> - マルチテナント：顧客別DBの物理分離を最初から採用

---

## Step 1. 各種LLM API呼び出しの有効化

### 目的
後続すべての工程で必要な「LLM呼び出し」を先に安定化する。

### 前提
- 一時的に `.env` の閲覧編集を許可
- ユーザーが手動でAPIキーを `.env` に格納後、疎通作業を開始

### 対象プラットフォーム
| プラットフォーム | 対象モデル（直近3程度） | 備考 |
|------------------|------------------------|------|
| Gemini | gemini-2.0-flash, gemini-2.5-pro 等 | grounding オプション必須 |
| OpenAI | gpt-4o, gpt-4-turbo, o3 等 | |
| Anthropic | claude-sonnet-4, claude-opus-4 等 | |
| Nano Banana | （画像生成系） | |

### 成果物
1. **プラットフォーム別クライアントモジュール**（1プラットフォーム=1ファイル、複数モデル対応）
2. **検証済みリクエストヘッダーJSON**（プラットフォーム・モデルごと）
3. **オプション切替機構**（ファイル上部で変更可能）

### 並列分担（worktree 分離）
```
worktree-gemini/    → Gemini クライアント
worktree-openai/    → OpenAI クライアント
worktree-anthropic/ → Anthropic クライアント
```

### ゲート条件（DoD）
- [ ] `.env` にキー投入後、各プラットフォームで「呼び出し→レスポンス取得」確認
- [ ] grounding 等の重要オプション切替が意図通り動作
- [ ] モデル自動切替などのフォールバック経路が存在しない（明示選択のみ）
- [ ] 各プラットフォームのエラーハンドリングが統一フォーマットで返る

---

## Step 3. LLM以外の呼び出しの有効化（ツール化 + LangGraph接続）

> ※ Step 2 と順序入替（1 → 3 → 2 の順で実施）

### 目的
検索・取得・抽出・検証・SEO指標など、LLM単体より強い処理をツールとして呼べるようにし、論拠の脆弱性を下げる。

### 前提
- 必要ツールの洗い出しを優先
- フォールバック禁止（失敗時に別ツールへ自動切替しない）

### 実装スコープ

#### A. 必須ツール
| tool_id | 機能 | I/O |
|---------|------|-----|
| `serp_fetch` | SERP取得（上位N件URL） | query → urls[] |
| `page_fetch` | ページ取得 + 本文抽出 | url → structured_content |
| `primary_collector` | 一次情報収集器（SERP→取得→保存） | query → evidence_refs[] |
| `url_verify` | URL実在確認 | url → status, final_url, meta |
| `pdf_extract` | PDFテキスト抽出 | pdf_path → text |

#### B. 拡張ツール（SEO強化）
| tool_id | 機能 | 備考 |
|---------|------|------|
| `search_volume` | 検索ボリューム取得 | Google Ads API |
| `related_keywords` | 関連語取得 | Google Ads API |

### 共通設計
- **Tool Manifest**（一覧定義）で `tool_id` 明示呼び出し
- I/O は原則 JSON
- 取得結果は「証拠」として追跡可能（URL / 取得日時 / 抜粋 / ハッシュ）
- エラー分類を統一（`RETRYABLE` / `NON_RETRYABLE` / `VALIDATION_FAIL`）

### 並列分担（worktree 分離）
```
worktree-search/    → SERP, Search Volume
worktree-fetch/     → Page Fetch, PDF Extract
worktree-verify/    → URL Verify, Evidence
worktree-registry/  → Tool Manifest, Registry
```

### ゲート条件（DoD）
- [ ] Tool Manifest により「何が呼べるか / 必要ENVは何か / 何が返るか」が一意
- [ ] SERP → 取得 → 抽出 → 保存（参照可能な形）まで一連で通る
- [ ] 失敗時に自動で別手段へ切替しない（必ず失敗として表出）
- [ ] 全ツールのエラー分類が統一フォーマットで返る

---

## Step 2. 出力確認システムの構築

> ※ Step 3 の後に実施

### 目的
LangGraph に組み込む前段として、全工程で必要になる「テスト形式」と「出力検証」を共通化する。

### 対象フォーマット
| 形式 | 検査項目 |
|------|----------|
| JSON | 構文破損（末尾カンマ等）、スキーマ違反 |
| CSV | 列不一致、クオート崩れ、エンコーディング |

### 成果物
1. **Validator モジュール**（JSON / CSV）
2. **ValidationReport 型**（機械可読な検査結果）
3. **Repairer モジュール**（決定的修正のみ、ログ必須）
4. **破壊パターンテストスイート**

### 修正ポリシー
| 条件 | 許可 | 備考 |
|------|------|------|
| 決定的修正（JSON末尾カンマ除去等） | ✅ | 実施ログ必須 |
| 同一条件リトライ（上限3回） | ✅ | attempt 記録必須 |
| 外部LLMによる再生成 | ⚠️ 明示ON時のみ | 上限・失敗時停止を厳格化 |
| 別モデル/別ツールへの自動切替 | ❌ | 禁止 |

### ゲート条件（DoD）
- [ ] JSON/CSV 入力に対して ValidationReport が必ず機械可読で得られる
- [ ] 修正を行う場合は必ずログに残り、黙って採用されない
- [ ] リトライ/修正の許容範囲がコードで固定されている
- [ ] 破壊パターンテストが全通過

---

## Step 4. 契約・実行コンテキスト基盤の構築（LangGraph共通）

### 目的
Step 1/3/2 を「組み立て可能」にするための共通契約（State / Context / Error / Retry）を固定する。

### 成果物

#### 1. Graph State スキーマ
```python
class GraphState(TypedDict):
    run_id: str
    tenant_id: str
    current_step: str
    step_outputs: dict[str, ArtifactRef]
    validation_reports: list[ValidationReport]
    errors: list[StepError]
    # ...
```

#### 2. 実行コンテキスト
```python
class ExecutionContext:
    run_id: str
    step_id: str
    attempt: int
    tenant_id: str
    started_at: datetime
    # ...
```

#### 3. エラー分類
| 分類 | 意味 | リトライ可否 |
|------|------|-------------|
| `RETRYABLE` | 一時的失敗（タイムアウト等） | ✅ 同一条件のみ |
| `NON_RETRYABLE` | 永続的失敗（認証エラー等） | ❌ |
| `VALIDATION_FAIL` | 出力検証失敗 | ⚠️ 修正可能なら |

### 並列分担（worktree 分離）
```
worktree-contract/  → State, Step I/O 契約
worktree-context/   → ExecutionContext, Error 分類
worktree-adapter/   → Step 1/3/2 との統合アダプタ
```

### ゲート条件（DoD）
- [ ] Step 1/3/2 の出力がすべて同一契約（GraphState）に載る
- [ ] 失敗時に「再試行可能か」が機械判定できる
- [ ] フォールバック経路が設計上存在しない
- [ ] 型チェック（mypy / pyright）が通る

---

## Step 5. 成果物ストア・観測・プロンプト差し替え基盤（LangGraph共通）

### 目的
出力の置き場・追跡・差し替えを先に確定し、後工程の統合で破綻しないようにする。

### 成果物

#### 1. Artifact Store I/F（MinIO）
```python
class ArtifactStore:
    def put(content, content_type) -> ArtifactRef  # path, digest
    def get(ref: ArtifactRef) -> bytes
    def exists(ref: ArtifactRef) -> bool
```

#### 2. DB スキーマ（Postgres）
```sql
-- 最小スキーマ（後で拡張可能）
runs         (id, tenant_id, status, config, created_at, ...)
steps        (id, run_id, step_name, status, started_at, ...)
attempts     (id, step_id, attempt_num, result, ...)
artifacts    (id, step_id, ref_path, digest, content_type, ...)
events       (id, run_id, step_id, event_type, payload, ...)
```

#### 3. 観測（イベント/ログ）
| イベント | タイミング |
|----------|----------|
| `step.started` | step 開始時 |
| `step.succeeded` | step 成功時 |
| `step.failed` | step 失敗時 |
| `step.retrying` | リトライ開始時 |
| `repair.applied` | 修正適用時 |

#### 4. Prompt Pack ローダ
```python
class PromptPackLoader:
    def load(pack_id: str) -> PromptPack
    # pack_id 未指定 → 例外（自動実行禁止）
    # mock_pack 明示指定 → モック返却
```

### 並列分担（worktree 分離）
```
worktree-artifact/  → Artifact Store
worktree-db/        → DB スキーマ, migrations
worktree-observe/   → Events, Logging
worktree-prompt/    → Prompt Pack Loader
```

### ゲート条件（DoD）
- [ ] 出力が保存され ref で参照でき、run/step と紐づけて追跡できる
- [ ] prompt pack 未設定で自動実行されない
- [ ] イベントが DB に永続化され、後から追跡可能
- [ ] マルチテナント分離が storage / DB 両方で機能

---

## Step 6. LangGraphメインシステムの構築

### 目的
仕様書の工程に従い、Step 1/3/2/4/5 で分割実装した要素を組み立てて E2E の骨格を完成させる。

### 前提
- 顧客プロンプト未入手のためプロンプト内容はモック
- `mock_pack` 明示指定時のみ動作（未指定は fail）

### 2段構成 Graph

#### pre-approval graph
```
工程-1（入力）
    ↓
工程0（準備）
    ↓
工程1（分析）
    ↓
工程3（構成）  ※順序入替
    ↓
工程2（調査）  ※順序入替
    ↓
┌─────────────────┐
│ 工程3A（並列）  │
│ 工程3B（並列）  │
│ 工程3C（並列）  │
└─────────────────┘
    ↓
[承認待ち State 保存]
```

#### post-approval graph
```
[承認後 State 復元]
    ↓
工程4
    ↓
工程5
    ↓
工程6
    ↓
工程6.5（統合パッケージ）
    ↓
工程7A
    ↓
工程7B
    ↓
工程8
    ↓
工程9
    ↓
工程10
```

### 共通ノードラッパ
```python
def step_wrapper(step_fn, ctx: ExecutionContext, state: GraphState):
    # 1. prompt load
    # 2. call (LLM or Tool)
    # 3. validate
    # 4. store artifact
    # 5. emit event
    # 6. update state
```

### 並列分担（worktree 分離）
```
worktree-pre/       → pre-approval graph
worktree-post/      → post-approval graph
worktree-wrapper/   → 共通ノードラッパ
worktree-e2e/       → E2E テスト, fixtures
```

### ゲート条件（DoD）
- [ ] `mock_pack` 指定で pre が並列含め完走し承認待ち State が保存される
- [ ] 承認後 post が進み、工程6.5 の統合パッケージが生成・保存される
- [ ] 全工程で検証・保存・イベント記録が行われ、黙って採用がない
- [ ] E2E テストが通過

---

## Step 7. UI実装（最小B、社内エンジニア向け）

### 目的
社内エンジニアが運用・デバッグできる UI を提供する。

### 利用者・表示方針
- 利用者：社内エンジニア
- 全情報閲覧可能（後で非表示化を追加できる構造）

### 必須画面/機能

#### 1. Runs 一覧
| 項目 | 内容 |
|------|------|
| 状態 | pending / running / waiting_approval / completed / failed |
| 最終更新 | timestamp |
| 要約 | 入力キーワード、現在工程 |
| 設定サマリ | 選択モデル、オプション |

#### 2. Run 作成
- **工程-1 入力 UI**（スプレッドシート代替）
- **実行オプション切替 UI**
  - プラットフォーム / モデル選択
  - grounding 等の重要オプション
  - ツール設定
  - repair / retry 上限

#### 3. Run 詳細
- Step タイムライン（attempt 含む）
- Validation Report 閲覧
- Artifacts 閲覧
- Logs / Events（全閲覧）
- **承認ボタン**（Approve / Reject）

#### 4. Retry（step 単位）
- 同一条件のみ（フォールバック禁止）
- Retry ボタンで step 単位再実行

#### 5. Clone Run
- 条件変更は別 run として明示作成

#### 6. Preview リンク
- 生成 HTML のビルド成果への遷移リンク

### リアルタイム
- WebSocket でリアルタイム更新（ローカル実行前提）

### ゲート条件（DoD）
- [ ] UI から Run 作成 → 承認 → step retry → Preview 参照が一通りできる
- [ ] モデル/ツールの自動切替や黙った回復が存在しない
- [ ] 全画面でエラー状態が明示される
- [ ] レスポンシブ対応（デスクトップ優先）

---

## Step 8. ローカル運用単位の整備

### 目的
「別ディレクトリに落としてテスト」まで含め、誰が落としても再現できる状態を作る。

### 成果物

#### 1. docker-compose.yml
```yaml
services:
  postgres:
    # healthcheck 付き
  minio:
    # バケット初期化
  temporal:
    # temporal-ui 任意
  api:
    depends_on: [postgres, minio, temporal]
  worker:
    depends_on: [postgres, minio, temporal]
  ui:
    depends_on: [api]
  # redis: 任意
```

#### 2. 環境変数
- `.env.example`（必須 ENV 一覧）
- 起動時に必須 ENV 未設定なら即 fail

#### 3. スクリプト
| スクリプト | 内容 |
|-----------|------|
| `scripts/bootstrap.sh` | compose 起動 → DB migrate → MinIO バケット初期化 |
| `scripts/reset.sh` | 完全初期化 |
| `scripts/clean-room-verify.sh` | 別ディレクトリ検証 |

#### 4. Preview 実体
- `html_bundle` artifact の保存・参照
- `/runs/:id/preview` でアクセス可能

#### 5. クリーンディレクトリ検証
```bash
# 2段階 smoke
1. secrets 未設定 → 明確に失敗すること
2. secrets 設定  → E2E が通ること
```

#### 6. 手順書
| ドキュメント | 内容 |
|--------------|------|
| `docs/LOCAL_RUNBOOK.md` | 導入、起動、操作、トラブルシュート |
| `docs/CLEAN_ROOM_VERIFICATION.md` | 別ディレクトリ検証の実行手順と合格基準 |

### ゲート条件（DoD）
- [ ] 別ディレクトリで `.env` 未設定 → API/Worker が明確に起動失敗
- [ ] 別ディレクトリで `.env` 設定 → `bootstrap` だけで一式が立つ
- [ ] UI から E2E（作成→承認→retry→preview）が再現できる
- [ ] 手順書どおりに社内エンジニアが迷わず再現できる

---

## 依存関係図

```
Step 1 (LLM API)
     │
     ├──────────────┐
     │              │
     ▼              ▼
Step 3 (Tools) ←── Step 2 (Validation) ※3の後に2
     │              │
     └──────┬───────┘
            │
            ▼
      Step 4 (Contract/Context)
            │
            ▼
      Step 5 (Store/Observe/Prompt)
            │
            ▼
      Step 6 (LangGraph Main)
            │
            ▼
      Step 7 (UI)
            │
            ▼
      Step 8 (運用整備)
```

---

## 禁止事項チェックリスト（全 Step 共通）

| 禁止事項 | 確認項目 |
|----------|----------|
| 別モデルへの自動切替 | コードに fallback model の記述がないこと |
| 別プロバイダへの自動切替 | コードに fallback provider の記述がないこと |
| 別ツールへの自動切替 | コードに fallback tool の記述がないこと |
| モックへの自動逃げ | mock は明示指定時のみ動作すること |
| 壊れた出力の黙った採用 | 修正時は必ずログが残ること |
| prompt pack 未指定での自動実行 | 未指定時は例外を投げること |

---

## 許容事項（正常系として明文化）

| 許容事項 | 条件 |
|----------|------|
| 同一条件でのリトライ | 上限回数あり（デフォルト3回）、attempt 記録必須 |
| 決定的修正（JSON末尾カンマ除去等） | 実施ログ必須、repair イベント記録 |
| 外部LLMによるフォーマット再生成 | 明示 ON 時のみ、上限あり、失敗時停止 |

---

## 次のアクション

1. **Step 1 開始準備**
   - `.env.example` 作成
   - APIキー格納の依頼

2. **worktree 構成の決定**
   - 各 Step の並列分担を確定
   - worktree 命名規則の統一

3. **共通型定義の先行実装**
   - `ValidationReport`
   - `ArtifactRef`
   - `StepError`
   - `ExecutionContext`
