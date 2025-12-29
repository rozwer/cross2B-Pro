# テスト品質保護ルール

> テストの改ざん・無効化を防止するルール

---

## 禁止事項

### テストの無効化

```
❌ 禁止:
- @pytest.mark.skip / @pytest.mark.xfail の追加
- test_ 接頭辞の削除（test_foo → _test_foo）
- テストファイル全体のコメントアウト
- describe.skip() / it.skip() の追加（JS/TS）
```

### アサーションの削除・弱化

```
❌ 禁止:
- assert 文の削除
- 期待値の変更（テストを通すため）
- try-except でテスト失敗を握りつぶす
- expect().toBe() → expect().toBeDefined() への弱化
```

### lint/CI 設定の緩和

```
❌ 禁止:
- # noqa / # type: ignore の追加
- eslint-disable の追加
- tsconfig.json の strict オプション緩和
- .gitignore へのテストファイル追加
```

---

## テスト失敗時の正しい対応

### 1. 原因の特定

```
- テストが正しく、実装にバグがある → 実装を修正
- テストが古く、仕様変更がある → テストを更新（理由を明記）
- テスト自体にバグがある → テストを修正（理由を明記）
```

### 2. 報告が必要なケース

```
⚠️ 親エージェントに報告:
- テストの意図が不明な場合
- 仕様変更の判断が必要な場合
- 複数のテストが連鎖して失敗する場合
```

---

## 許容される変更

### テストの改善

```
✅ 許容:
- テストケースの追加
- より厳密なアサーションへの強化
- テストの可読性向上（リファクタリング）
- 実装バグ修正に伴うテストの正当な更新（コミットメッセージに理由記載）
```

### 一時的な skip（厳格な条件付き）

```
✅ 許容（条件付き）:
- 外部依存の問題で一時的に skip（Issue 番号必須）
- CI 環境固有の問題（環境条件を明記）
- 必ず TODO コメントで復帰時期を明記
```

例:
```python
@pytest.mark.skip(reason="Issue #123: External API down, restore by 2025-01-15")
def test_external_api():
    ...
```

---

## 監視対象ファイル

以下のファイルへの変更は特に注意：

```
tests/**/*
*.test.ts
*.test.tsx
*.spec.ts
*.spec.tsx
pytest.ini
pyproject.toml（[tool.pytest]セクション）
jest.config.*
tsconfig.json
.eslintrc.*
ruff.toml
```

---

## 参考

- [Claude Codeにテストで楽をさせない技術](https://speakerdeck.com/)
