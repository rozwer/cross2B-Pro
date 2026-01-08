# 技術的影響範囲分析

**作成日**: 2026-01-08

## 影響サマリー

| 層 | 変更スコープ | 影響度 |
|----|-----------|-------|
| State (LangGraph) | +4フィールド | 低 |
| Activity | 既存12個修正 + 新規1個 | 中 |
| API | 既存1個修正 + 新規3個 | 低 |
| PromptLoader | 統合機能追加 | 中 |

## 1. LangGraph State 変更

### 追加フィールド

| フィールド | 型 | 目的 |
|-----------|-----|------|
| `system_prompt_context` | `dict` | unified_knowledge.jsonキャッシュ |
| `prompt_pack_id` | `str` | 使用中パック識別子 |
| `prompt_version_used` | `dict` | ステップ別バージョン |
| `system_knowledge_loaded_at` | `str` | ロード時刻 |

## 2. Temporal Activity

### 修正が必要なActivity
- Step0〜Step12の全Activity

### 新規Activity
- `LoadSystemPromptContext`: unified_knowledge.jsonロード

## 3. API エンドポイント

### 新規
- `GET /api/prompts/system-knowledge/{step}`
- `GET /api/prompts/integrated/{step}`
- `POST /api/prompts/reload-cache`

## 4. PromptLoader

### 追加メソッド
- `load_system_knowledge(step_dir)`
- `load_integrated(pack_id, step)`

### 変数システム拡張
- `{{__system_guidelines}}`: unified_knowledgeから注入
