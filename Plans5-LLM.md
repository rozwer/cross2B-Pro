# LLMクライアント層 修正計画（Plans-LLM.md）

> **作成日**: 2026-01-12
> **対象**: apps/api/llm/ (gemini.py, openai.py, anthropic.py)
> **ステータス**: 計画中
> **並列実行**: Plans-API, Plans-Worker, Plans-LangGraph, Plans-Frontend, Plans-DB と競合なし

---

## 概要

| 優先度 | 件数 |
|--------|------|
| CRITICAL | 0件 |
| HIGH | 7件 |
| MEDIUM | 4件 |

---

## 🟠 HIGH `cc:TODO`

### H-1. Anthropicクライアントのリトライにバックオフなし `cc:TODO`
**ファイル**: `apps/api/llm/anthropic.py:173-262`
**問題**:
- RateLimitError検出時に即座にリトライ → API側がさらに拒否
- Geminiの実装（指数バックオフ実装済み）と動作が異なる
**修正方針**:
- `asyncio.sleep(delay)`でバックオフを導入（Geminiと同じロジック）
- 指数バックオフ係数（base=1.0, exponential_base=2.0）を設定可能に
**工数**: 30分

### H-2. OpenAIリトライにsleep実装がない `cc:TODO`
**ファイル**: `apps/api/llm/openai.py:160-265`
**問題**:
- RateLimitError時にバックオフなし → API側で更にペナルティ
- Gemini実装との矛盾（保守性低下）
**修正方針**:
- Geminiと同じ指数バックオフロジックを導入
**工数**: 30分

### H-3. JSON パース失敗時の情報喪失 `cc:TODO`
**ファイル**: `apps/api/llm/openai.py:324-339`
**問題**:
- JSONパース失敗時に`raw_output`をカット（`content[:500]`）
- 大きい出力の情報が大幅に失われる
**修正方針**:
- フル内容を保存するが、ログには最初500文字＋「... (全XXX文字)」で表示
- エラー出力を`error_output.json`としてartifactに保存
**工数**: 25分

### H-4. Gemini APIエラー分類が不完全 `cc:TODO`
**ファイル**: `apps/api/llm/gemini.py:855-911`
**問題**:
- エラー分類が文字列パターンマッチングのみ（脆弱）
- Google Genai SDKの例外型を全キャッチしていない
- SDKアップデート時にエラーメッセージフォーマットが変わると動作がずれる
**修正方針**:
- Google Genai SDK例外型をインポートし、`isinstance()`でチェック
- 例外型マッピングテーブルを作成
**工数**: 45分

### H-5. 出力トークン比率の警告ロジックが不正確 `cc:TODO`
**ファイル**:
- `apps/api/llm/gemini.py:840-853`
- `apps/api/llm/anthropic.py:432-446`
**問題**:
- `if ratio < 0.1`で警告（「10%未満は期待より大幅に少ない」と判定）
- 実際には多くの工程が短い出力を期待（JSON パースなら100トークン）
- 誤報告が頻繁に発生 → ログが信頼できなくなる
**修正方針**:
- `finish_reason`で`MAX_TOKENS`を先に確認
- 基準値を工程ごとに設定
**工数**: 30分

### H-6. LLMクライアントインスタンスの永続化による副作用 `cc:TODO`
**ファイル**: `apps/worker/activities/step11.py:295-305`
**問題**:
- Activity インスタンスが同一run内で複数回再利用される場合、同じGemini接続を使いまわす
- Timeout/接続エラーが発生した場合、キャッシュされた不健全なクライアントで再試行される
**修正方針**:
- クライアント毎回作成するか、接続ヘルスチェックを実装
**工数**: 25分

### H-7. コスト/トークン追跡が不完全 `cc:TODO`
**ファイル**: `apps/api/routers/cost.py:129-195`
**問題**:
- step11/step12のusageデータがないと静かにスキップ
- 実際のLLM使用量の~30%が欠落
**修正方針**:
- 全stepでusageデータを必須化
- 欠落時は警告ログ出力
**工数**: 30分

---

## 🟡 MEDIUM `cc:TODO`

### M-1. Gemini generation_config 設定矛盾 `cc:TODO`
**ファイル**: `apps/api/llm/gemini.py:556-618`
**問題**: system_instructionとtoolsの配置がSDKバージョンで異なる可能性
**工数**: 20分

### M-2. Anthropic 予期しないエラーの分類が甘い `cc:TODO`
**ファイル**: `apps/api/llm/anthropic.py:256-259`
**問題**: 予期しない例外を全てNON_RETRYABLEに分類
**工数**: 15分

### M-3. Gemini タイムアウト設定が硬直 `cc:TODO`
**ファイル**: `apps/api/llm/gemini.py:90, 678`
**問題**: デフォルト420秒、Thinking有効時は10分以上かかる可能性
**修正方針**: デフォルトを600秒に増加、LLMRequestConfigにtimeout_seconds追加
**工数**: 20分

### M-4. AsyncClient接続プール設定不十分 `cc:TODO`
**ファイル**: `apps/worker/activities/base.py:680-700`
**問題**: 接続プール設定なし、並列Activity時に枯渇の可能性
**修正方針**: limitsパラメータ設定（max_connections=20）
**工数**: 20分

---

## 完了基準

- [ ] 全HIGH項目の修正完了
- [ ] Python lint/type エラーがない
- [ ] LLMクライアントのリトライロジックが統一されている
- [ ] 関連するユニットテスト追加・通過
