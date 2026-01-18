# Plans5: フローブループリント & A/Bテスト機能

> **ステータス**: 要件定義完了 / 実装未着手
> **工数見積**: 大規模（追加工数要相談）
> **最終更新**: 2026-01-18

---

## 概要

### 目的
モデル・プロンプトの組み合わせを「フローブループリント」として管理し、run実行時に選択。分岐によるA/Bテストを可能に。

### 背景
- Settings画面でプロンプトとモデルを個別に設定可能（既存）
- 「この組み合わせで試したい」「別パターンと比較したい」ニーズ
- run作成時ではなく、事前にブループリントとして定義するのがUX的に良い

### コンセプト

```
[Settings: フローブループリント管理]
    │
    ├── Blueprint A: 本番用（デフォルト設定）
    ├── Blueprint B: step3でGemini、step7でGPT-4
    └── Blueprint C: Blueprint Bからstep5で分岐

[Run作成時]
    └── 「どのブループリントを使う？」→ 選択するだけ

[実行中の比較]
    └── 「両方選ぶ」→ runが分岐、両パスを追跡可能
```

---

## Phase 1: DB設計 `TODO`

### 1.1 フローブループリントテーブル

```sql
CREATE TABLE flow_blueprints (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(128) NOT NULL,
    description TEXT,
    parent_blueprint_id INTEGER REFERENCES flow_blueprints(id),
    branch_point VARCHAR(32),
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);
```

### 1.2 ブループリント工程設定テーブル

```sql
CREATE TABLE blueprint_step_configs (
    id SERIAL PRIMARY KEY,
    blueprint_id INTEGER NOT NULL REFERENCES flow_blueprints(id),
    step_name VARCHAR(32) NOT NULL,
    model_id INTEGER REFERENCES models(id),
    prompt_version_id INTEGER REFERENCES prompt_versions(id),
    parameters JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(blueprint_id, step_name)
);
```

### 1.3 Runsテーブル拡張

```sql
ALTER TABLE runs ADD COLUMN blueprint_id INTEGER REFERENCES flow_blueprints(id);
ALTER TABLE runs ADD COLUMN parent_run_id INTEGER REFERENCES runs(id);
ALTER TABLE runs ADD COLUMN branch_point VARCHAR(32);
ALTER TABLE runs ADD COLUMN ab_test_group VARCHAR(64);
```

---

## Phase 2: API設計 `TODO`

### 2.1 ブループリント管理

| メソッド | パス | 用途 |
|----------|------|------|
| GET | `/api/blueprints` | 一覧（ツリー構造） |
| GET | `/api/blueprints/{id}` | 詳細 |
| POST | `/api/blueprints` | 作成 |
| PUT | `/api/blueprints/{id}` | 更新 |
| DELETE | `/api/blueprints/{id}` | 削除 |
| POST | `/api/blueprints/{id}/branch` | 分岐作成 |

### 2.2 Run分岐

| メソッド | パス | 用途 |
|----------|------|------|
| POST | `/api/runs/{id}/fork` | 分岐 |
| GET | `/api/runs/{id}/siblings` | 同グループ一覧 |
| GET | `/api/runs/{id}/tree` | 分岐ツリー |

---

## Phase 3: FE - Settings画面 `TODO`

### 3.1 ブループリント管理 `/settings/blueprints`

```
[ツリービュー]
● デフォルト（本番用）
├── ○ テストA（step3でGemini）
│   └── ○ テストA-1（step7でプロンプトv2）
└── ○ テストB（step5でClaude）
```

- ノードクリック → 詳細パネル
- 「分岐を作成」→ 新ブループリント
- 工程ごとにモデル/プロンプト/パラメータ設定
- コスト見積もり表示

---

## Phase 4: FE - Run作成/実行 `TODO`

### 4.1 ウィザードでブループリント選択

### 4.2 比較UI（A/Bテスト時）

```
┌─────────────────┬─────────────────┐
│ A案（Gemini）    │ B案（GPT-4）     │
│ [プレビュー]     │ [プレビュー]     │
│ コスト: ¥12     │ コスト: ¥18     │
└─────────────────┴─────────────────┘
[ A案で続行 ] [ B案で続行 ] [ 両方で続行 ]
```

### 4.3 分岐後のグループ表示

---

## Phase 5: Temporal/Worker `TODO`

- ブループリント設定読み込み
- Run分岐実装
- 成果物の共有/コピー管理

---

## 工数・優先度

| Phase | 見積 |
|-------|------|
| 1: DB | 中 |
| 2: API | 大 |
| 3: Settings UI | 大 |
| 4: Run UI | 大 |
| 5: Worker | 大 |
| **合計** | **特大** |

**推奨順序**: Phase 1-2 → 3 → 4 → 5（分岐は後回し可）

> この機能は大規模変更を伴います。実装依頼時は追加工数について事前にご相談ください。
