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

| ファイル | 修正内容 | 状態 |
|----------|----------|------|
| `apps/worker/activities/step0.py` | model_config から取得に統一 | `cc:DONE` |
| `apps/worker/activities/step3a.py` | model_config から取得 + 成果物にplatform追加 | `cc:DONE` |
| `apps/worker/activities/step3b.py` | model_config から取得 + 成果物にplatform追加 | `cc:DONE` |
| `apps/worker/activities/step3c.py` | model_config から取得 + 成果物にplatform追加 | `cc:DONE` |
| `apps/worker/activities/step3_5.py` | model_config から取得 + 成果物にplatform追加 | `cc:DONE` |

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
    "model_config": {
        "platform": llm_provider,  # 設定されたプラットフォーム
        "model": llm_model,        # 設定されたモデル名
    },
    ...
}
```

---

## 作業順序

1. [x] `step0.py` - モデル設定取得の修正 `cc:DONE`
2. [x] `step3a.py` - モデル設定取得 + 成果物修正 `cc:DONE`
3. [x] `step3b.py` - モデル設定取得 + 成果物修正 `cc:DONE`
4. [x] `step3c.py` - モデル設定取得 + 成果物修正 `cc:DONE`
5. [x] `step3_5.py` - モデル設定取得 + 成果物修正 `cc:DONE`
6. [ ] 動作確認（ワークフロー実行テスト）`cc:TODO`

---

## 完了条件

- [x] すべてのActivityで `model_config` からモデル設定を取得
- [x] 成果物に `platform` と `model` が正しく記録される
- [ ] UIで設定したモデルが成果物に表示される（要動作確認）
