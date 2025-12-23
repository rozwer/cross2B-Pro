# 工程構成変更 JSON レビューレポート

**レビュー日**: 2025-12-23
**対象**: Session A-F の実装計画JSON
**更新**: 2025-12-23 - 全指摘事項を修正完了

---

## 修正サマリー

| # | 優先度 | セッション | 指摘 | 状態 |
|---|--------|------------|------|------|
| 1 | High | E | 既存スキーマとの重複 | ✅ 修正済 |
| 2 | High | D | 4記事生成の実行戦略未定義 | ✅ 修正済 |
| 3 | High | F | step3_5必須化で後方互換性破壊 | ✅ 修正済 |
| 4 | Med | A | step0_output参照不足 | ✅ 修正済 |
| 5 | Med | B | LLMパス誤り | ✅ 修正済 |
| 6 | Med | C | 認可チェック未記載 | ✅ 修正済 |
| 7 | Med | D | breaking_changes不完全 | ✅ 修正済 |
| 8 | Med | F | __init__.py競合リスク | ✅ 修正済 |

---

## High Priority (修正済)

### 1. [Session E] 既存 `article_hearing.py` との重複

- **指摘**: Session E で `apps/api/schemas/hearing.py` を新規作成としているが、既に `apps/api/schemas/article_hearing.py` が存在し、同様のヒアリングスキーマが定義されている
- **根拠**: git logで `feat(ui): add article hearing wizard form for run creation` がコミット済み。既存スキーマと重複するとコードの分散が発生
- **修正案**:
  - Session E のタスク E-1 を「既存 `article_hearing.py` の確認・拡張」に変更
  - 新規ファイル作成ではなく、既存スキーマとの統合を検討

### 2. [Session D] step10 の 4記事並列生成における timeout 設計

- **指摘**: 4記事生成で timeout を 600秒に増加としているが、単一LLM呼び出しで4記事を生成するか、4回呼び出すかが不明確
- **根拠**: 単一呼び出しで4記事生成はLLMのコンテキスト長制限に抵触する可能性。4回呼び出しの場合、並列 vs 順次の設計が必要
- **修正案**:
  ```json
  "details": {
    "execution_strategy": "parallel | sequential",
    "per_article_timeout": "150秒",
    "total_timeout": "600秒"
  }
  ```

### 3. [Session F] step3_5 の必須化による後方互換性破壊

- **指摘**: Session F で step3_5 を必須として追加しているが、既存run（step3_5がない）の再実行時に失敗する
- **根拠**: `prerequisite_checks` で「必須のため、未完了なら待機」としているが、既存runの resume シナリオが未考慮
- **修正案**:
  - step3_5 も最初はオプショナルとして導入
  - 移行期間後に必須化するフラグを設ける
  - `rollback_plan` に既存run対応を追加

---

## Medium Priority

### 4. [Session A] step1_5 の入力に step0 出力が不足

- **指摘**: step1_5 の入力に `keyword` と `related_keywords` があるが、`step0_output` の参照がない
- **根拠**: step0 で生成された `recommended_angles` や `target_audience` が関連KW抽出に有用
- **修正案**:
  ```json
  "input": {
    "step0_output": "dict (キーワード分析結果)",
    "related_keywords": "list[string] (関連キーワード一覧)",
    ...
  }
  ```

### 5. [Session B] LLM設定ファイルパスの誤り

- **指摘**: タスク B-7 で `apps/worker/llm/gemini.py` を編集対象としているが、LLM設定は `apps/api/llm/` 配下にある
- **根拠**: 既存の `apps/api/llm/base.py`, `apps/api/llm/gemini.py` の構造
- **修正案**: ファイルパスを `apps/api/llm/gemini.py` に修正

### 6. [Session C] step12 API の認可チェック不足

- **指摘**: step12 API エンドポイントに tenant_id スコープのチェックが明記されていない
- **根拠**: CLAUDE.md の「マルチテナント越境禁止」ルール
- **修正案**:
  ```json
  "details": {
    "endpoints": [...],
    "security": {
      "tenant_scope": "required",
      "audit_log": "download/preview アクション記録"
    }
  }
  ```

### 7. [Session D] breaking_changes の影響範囲が不完全

- **指摘**: step11 と API preview の変更は記載されているが、以下が不足
  - step9 → step10 のデータフロー変更
  - WebSocket 進捗通知の変更
  - 監査ログのフォーマット変更
- **修正案**: breaking_changes に上記を追加

### 8. [Session F] activities/__init__.py の競合リスク

- **指摘**: Session A, B, C で個別にエクスポートを追加し、Session F で最終統合としているが、並列作業時のマージ競合が発生しやすい
- **根拠**: 同一ファイル（`__init__.py`）を複数セッションで編集
- **修正案**:
  - 各セッションでは `__init__.py` を編集せず、Session F でまとめて追加
  - または、各セッションで別行に追加し、マージ時に自動解決可能な形式に

---

## Low Priority

### 9. [Session A] output_spec の命名規則

- **指摘**: `file_name` が日本語（`工程1.5_関連KW競合抽出.json`）だが、storage_path は英語（`step1_5/output.json`）
- **根拠**: 一貫性の観点から統一が望ましい
- **修正案**: UI表示用の日本語名と、ストレージ用の英語名を分離して定義

### 10. [Session B] 入力ファイル数の不一致

- **指摘**: description で「6ファイル入力」としているが、仕様表では工程3.5は「添付数6」でファイルは `step0, 1.1, 1.5, 3A, 3B, 3C`
- **根拠**: 現行実装では step1 の出力ファイル名は `step1_competitors.csv`（1.1ではない）
- **修正案**: ファイル名の対応表を明記

### 11. [Session C] WordPress バージョンターゲットの未定義

- **指摘**: `wordpress_version_target` が出力スキーマにあるが、入力での指定方法がない
- **根拠**: Gutenberg ブロック形式はWPバージョンで互換性が異なる
- **修正案**: config または入力パラメータに `target_wordpress_version` を追加

### 12. [Session E] テンプレート機能の設計不足

- **指摘**: notes に「将来的にテンプレート機能を追加可能な設計に」とあるが、具体的な設計がない
- **根拠**: 後から追加すると既存データとの互換性問題が発生
- **修正案**: 最初から `template_id` フィールドを予約しておく

---

## article_hearing.py 差分レビュー

### 変更内容

```python
# BusinessInput クラス
- @field_validator による単一フィールド検証
+ @model_validator による複合フィールド検証

# KeywordInput クラス
+ status='decided' の場合 main_keyword 必須
+ status='undecided' の場合 theme_topics または selected_keyword 必須

# CTAInput クラス
+ type='single' の場合 single 設定必須
+ type='staged' の場合 staged 設定必須
```

### 評価

| 観点 | 評価 | コメント |
|------|------|----------|
| Correctness | ✅ Good | `model_validator(mode="after")` で適切にクロスフィールド検証 |
| Security | ✅ Good | バリデーションでinvalid dataを早期拒否 |
| Maintainability | ✅ Good | 各条件分岐が明確でテスト可能 |
| Operational safety | ⚠️ Note | エラーメッセージが日本語のみ（i18n考慮が必要な場合） |

### 推奨事項

1. **HttpUrl インポートの確認**: `HttpUrl` がインポートされているが、差分内で使用されていない。不要なら削除を検討
2. **エラーメッセージの一貫性**: `target_cv='other'` のエラーは日本語だが、将来的にi18n対応が必要な場合は定数化を検討

---

## 総合評価（修正後）

| セッション | 評価 | 修正内容 |
|------------|------|----------|
| A (step1_5) | ✅ | step0_output参照を追加、__init__.py編集をSession Fに集約 |
| B (step3_5) | ✅ | LLMパスを apps/api/llm/ に修正、__init__.py編集をSession Fに集約 |
| C (step12) | ✅ | 認可チェック・監査ログを詳細化、__init__.py編集をSession Fに集約 |
| D (step10) | ✅ | 順次実行戦略を明確化、breaking_changesを拡充、後方互換性を追加 |
| E (step-1) | ✅ | 既存article_hearing.pyを活用、テンプレート機能追加に変更 |
| F (統合) | ✅ | 後方互換性セクション追加、feature_flags定義、マージ戦略明確化 |

**次のアクション**:
1. ✅ 全High Priority項目を修正完了
2. ✅ 全Medium Priority項目を修正完了
3. Low Priority項目は実装時に対応（必須ではない）
4. 各セッションの実装を開始可能
