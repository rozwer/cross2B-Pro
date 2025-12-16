# 並列開発プロンプト集

このディレクトリには、並列開発用のセッションプロンプトが含まれています。

## 使い方

1. 新しいClaude Codeセッションを開く
2. 該当するセッションのプロンプトをコピー＆ペースト
3. 指示に従って実装を進める

## セッション依存関係

```
Phase 1 (同時並列可能):
  Session 1: Gemini    ─┐
  Session 2: OpenAI    ─┼─→ Phase 2へ
  Session 3: Anthropic ─┘

Phase 2 (Phase 1完了後、同時並列可能):
  Session 4: Tools     ─┐
  Session 5: Validation ─┴─→ Phase 3へ

Phase 3 (Phase 2完了後):
  Session 6: Contract + Store ─→ Phase 4へ

Phase 4 (Phase 3完了後):
  Session 7: LangGraph + Temporal ─→ Phase 5へ

Phase 5 (Phase 4完了後):
  Session 8: Frontend UI
```

## ファイル一覧

| ファイル | 説明 | Phase |
|---------|------|-------|
| [00_common.md](./00_common.md) | 全セッション共通の前提・ルール | - |
| [01_gemini.md](./01_gemini.md) | Gemini クライアント | 1 |
| [02_openai.md](./02_openai.md) | OpenAI クライアント | 1 |
| [03_anthropic.md](./03_anthropic.md) | Anthropic クライアント | 1 |
| [04_tools.md](./04_tools.md) | Tools (SERP/Fetch/Verify) | 2 |
| [05_validation.md](./05_validation.md) | Validation (JSON/CSV) | 2 |
| [06_contract.md](./06_contract.md) | Contract + Store基盤 | 3 |
| [07_langgraph.md](./07_langgraph.md) | LangGraph + Temporal | 4 |
| [08_frontend.md](./08_frontend.md) | Frontend UI | 5 |

## 注意事項

- 各セッションは独立したworktreeで作業
- develop/mainへの直接push禁止
- PR経由でマージ
- Conventional Commits形式必須
