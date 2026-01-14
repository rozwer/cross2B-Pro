# Plans4.md - モデル設定の成果物反映修正

> **作成日**: 2026-01-14
> **目的**: ユーザーが選択したモデル設定が成果物に正しく反映されるように修正

---

## 問題の概要

ユーザーが選択したモデル/プラットフォーム設定が成果物に正しく反映されていない。

### 根本原因

1. **Activity側でのモデル設定取得の不統一**
   - 古いstep: `config.get("llm_provider")` で直接取得（存在しないキー）
   - 新しいstep: `config.get("model_config", {})` から取得（正しい）

2. **成果物へのplatform情報の未記録**
   - `response.model`（LLM応答のモデル名）のみ記録
   - 設定された `platform`（gemini/openai/anthropic）が未保存

---

## 修正対象ファイル

### Phase 1: モデル設定取得 + 成果物追加（初回修正）

| ファイル | 修正内容 | 状態 |
|----------|----------|------|
| `apps/worker/activities/step0.py` | model_config から取得に統一 | `cc:DONE` |
| `apps/worker/activities/step3a.py` | model_config から取得 + 成果物にplatform追加 | `cc:DONE` |
| `apps/worker/activities/step3b.py` | model_config から取得 + 成果物にplatform追加 | `cc:DONE` |
| `apps/worker/activities/step3c.py` | model_config から取得 + 成果物にplatform追加 | `cc:DONE` |
| `apps/worker/activities/step3_5.py` | model_config から取得 + 成果物にplatform追加 | `cc:DONE` |

### Phase 2: 成果物への model_config_data 追加（追加修正）

| ファイル | 修正内容 | 状態 |
|----------|----------|------|
| `apps/worker/activities/schemas/step4.py` | スキーマに model_config_data フィールド追加 | `cc:DONE` |
| `apps/worker/activities/step4.py` | 成果物に model_config_data 追加 | `cc:DONE` |
| `apps/worker/activities/schemas/step5.py` | スキーマに model_config_data フィールド追加 | `cc:DONE` |
| `apps/worker/activities/step5.py` | 成果物に model_config_data 追加 | `cc:DONE` |
| `apps/worker/activities/schemas/step6.py` | スキーマに model_config_data フィールド追加 | `cc:DONE` |
| `apps/worker/activities/step6.py` | 成果物に model_config_data 追加 | `cc:DONE` |
| `apps/worker/activities/schemas/step6_5.py` | スキーマに model_config_data フィールド追加 | `cc:DONE` |
| `apps/worker/activities/step6_5.py` | 成果物に model_config_data 追加 | `cc:DONE` |
| `apps/worker/activities/schemas/step7a.py` | スキーマに model_config_data フィールド追加 | `cc:DONE` |
| `apps/worker/activities/step7a.py` | 成果物に model_config_data 追加 | `cc:DONE` |
| `apps/worker/activities/schemas/step7b.py` | スキーマに model_config_data フィールド追加 | `cc:DONE` |
| `apps/worker/activities/step7b.py` | 成果物に model_config_data 追加 | `cc:DONE` |
| `apps/worker/activities/schemas/step8.py` | スキーマに model_config_data フィールド追加 | `cc:DONE` |
| `apps/worker/activities/step8.py` | 成果物に model_config_data 追加 | `cc:DONE` |
| `apps/worker/activities/schemas/step9.py` | スキーマに model_config_data フィールド追加 | `cc:DONE` |
| `apps/worker/activities/step9.py` | 成果物に model_config_data 追加 | `cc:DONE` |
| `apps/worker/activities/schemas/step10.py` | Step10Metadata に model_config_data フィールド追加 | `cc:DONE` |
| `apps/worker/activities/step10.py` | metadata に model_config_data 追加 | `cc:DONE` |

---

## 実装詳細

### 1. モデル設定取得の統一パターン

**Before（旧式）**:
```python
llm_provider = config.get("llm_provider", "gemini")
llm_model = config.get("llm_model")
```

**After（新式）**:
```python
model_config = config.get("model_config", {})
llm_provider = model_config.get("platform", config.get("llm_provider", "gemini"))
llm_model = model_config.get("model", config.get("llm_model"))
```

### 2. 成果物へのplatform情報追加

**Before**:
```python
result = {
    "model": response.model,  # LLMが返したモデル名のみ
    ...
}
```

**After**:
```python
result = {
    "model": response.model,  # LLMが返した実際のモデル名
    "model_config_data": {
        "platform": llm_provider,  # 設定されたプラットフォーム
        "model": llm_model,        # 設定されたモデル名
    },
    ...
}
```

---

## 完了条件

- [x] すべてのActivityで `model_config` からモデル設定を取得
- [x] すべてのスキーマに `model_config_data` フィールド追加
- [x] すべての成果物に `platform` と `model` が正しく記録される
- [ ] UIで設定したモデルが成果物に表示される（要動作確認）
