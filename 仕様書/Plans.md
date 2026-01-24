# 関連KW処理のバグ修正

> **作成日**: 2026-01-20
> **目的**: アンケートで入力した関連KWリストがStep1.5で使われていないバグを修正

---

## 概要

### 現状の問題

1. **アンケート入力**: ユーザーが関連キーワードを入力
   - 格納先: `config["input"]["data"]["keyword"]["related_keywords"]`

2. **Step1.5 の取得方法**:
   ```python
   related_keywords = config.get("related_keywords", [])  # 常に []
   ```

3. **結果**: ユーザー入力が無視され、`step0.recommended_angles` からの推定値のみ使用

### 期待する動作

1. アンケートで入力した `related_keywords` が優先的に使われる
2. `related_keywords` が未入力の場合のみ `step0.recommended_angles` から推定

---

## 修正方針

### 選択肢A: Step1.5 で正しいパスから取得（推奨）

**メリット**:
- 修正箇所が1ファイルのみ
- configの構造を変えない
- 後方互換性を維持

**修正箇所**: `apps/worker/activities/step1_5.py`

### 選択肢B: config構成時に `related_keywords` を直下に配置

**メリット**:
- Step1.5 の取得ロジックがシンプルに保たれる
- 他のstepからも参照しやすい

**デメリット**:
- 複数ファイルの修正が必要
- データ構造の変更

---

## フェーズ1: バグ修正 ✅完了

### 1.1 Step1.5 の関連KW取得ロジック修正 `[bugfix:reproduce-first]`

**対象ファイル**: `apps/worker/activities/step1_5.py`

**修正内容**: ✅ 実装済み（2026-01-20）

- 正しいパスから関連KWを取得: `config["input"]["data"]["keyword"]["related_keywords"]`
- `RelatedKeyword` 型（dict）からキーワード文字列を抽出
- ユーザー入力を優先、入力がない場合のみ `step0.recommended_angles` からフォールバック

**検証結果**:
- ✅ 構文チェック成功
- ✅ Ruff lint チェック成功

---

## フェーズ2: テスト追加 `cc:TODO`（オプション）

### 2.1 ユニットテスト追加

**対象ファイル**: `tests/unit/worker/activities/test_step1_5.py`（新規）

**テストケース**:
- [ ] ユーザー入力の関連KWが正しく取得される
- [ ] ユーザー入力がない場合、step0からフォールバック
- [ ] RelatedKeyword型（dict）からkeyword抽出
- [ ] 文字列型の関連KWも処理可能

---

## 修正対象ファイル一覧

| ファイル | 変更 | 優先度 |
|----------|------|--------|
| `apps/worker/activities/step1_5.py` | 関連KW取得ロジック修正 | 高 |
| `tests/unit/worker/activities/test_step1_5.py` | テスト追加（新規） | 中 |

---

## 検証手順

1. アンケートで関連KWを3つ入力してrunを作成
2. Step1.5のログを確認
   - 期待: `Using 3 user-provided related keywords`
3. Step1.5の出力を確認
   - 期待: 入力した関連KWで競合取得されている
