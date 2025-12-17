# ステップ統合プロンプト

このディレクトリには、共通ヘルパーを各ステップに統合するためのプロンプトが含まれています。

## 前提条件

以下のヘルパーが実装済みであること：

- `apps/worker/helpers/output_parser.py` - OutputParser
- `apps/worker/helpers/schemas.py` - 共通Pydanticモデル
- `apps/worker/helpers/input_validator.py` - InputValidator
- `apps/worker/helpers/quality_validator.py` - QualityValidator
- `apps/worker/helpers/content_metrics.py` - ContentMetrics
- `apps/worker/helpers/checkpoint_manager.py` - CheckpointManager
- `apps/worker/helpers/quality_retry_loop.py` - QualityRetryLoop

## 統合順序（推奨）

### Batch 1: 基盤ステップ（最優先）
1. **Step5** - フォールバック禁止違反の修正（緊急）
2. **Step10** - フォールバック禁止違反の修正（緊急）
3. **Step4** - 後続全ステップの品質に影響

→ [batch1-step5.md](batch1-step5.md), [batch1-step10.md](batch1-step10.md), [batch1-step4.md](batch1-step4.md)

### Batch 2: 並列ステップ
4. **Step3a** - 検索意図・ペルソナ
5. **Step3b** - 共起キーワード（心臓部）
6. **Step3c** - 競合分析

→ [batch2-step3.md](batch2-step3.md)

### Batch 3: 収集・検証ステップ
7. **Step0** - キーワード選択
8. **Step1** - 競合取得
9. **Step2** - CSV検証

→ [batch3-collection.md](batch3-collection.md)

### Batch 4: コンテンツ生成ステップ
10. **Step6** - 拡張アウトライン
11. **Step6.5** - 統合パッケージ
12. **Step7a** - ドラフト生成

→ [batch4-generation.md](batch4-generation.md)

### Batch 5: 仕上げステップ
13. **Step7b** - ブラッシュアップ
14. **Step8** - ファクトチェック
15. **Step9** - 最終リライト

→ [batch5-finishing.md](batch5-finishing.md)

## 使用方法

各プロンプトファイルを Claude に渡して実装を依頼してください。

```
@docs/step-improvements/integration-prompts/batch1-step5.md を読んで、
apps/worker/activities/step5.py にヘルパーを統合してください。
```

## ファイル一覧

| ファイル | 対象ステップ | 優先度 | 主な内容 |
|----------|-------------|--------|----------|
| batch1-step5.md | Step5 | 緊急 | フォールバック違反修正 |
| batch1-step10.md | Step10 | 緊急 | フォールバック違反修正 |
| batch1-step4.md | Step4 | 高 | 戦略アウトライン品質 |
| batch2-step3.md | Step3a/3b/3c | 高 | 並列分析ステップ |
| batch3-collection.md | Step0/1/2 | 中 | データ収集・検証 |
| batch4-generation.md | Step6/6.5/7a | 中 | コンテンツ生成 |
| batch5-finishing.md | Step7b/8/9 | 中〜低 | 仕上げ処理 |
