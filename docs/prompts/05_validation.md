# Session 5: Validation (JSON/CSV)

## Phase 2（Phase 1完了後、並列実行可能: Session 4, 5）

---

## 作業開始手順

```bash
cd /home/rozwer/案件
git fetch origin
git pull origin develop

# Phase 1 のマージ確認
git log --oneline develop | head -5

# Worktree作成
TOPIC="validation"
mkdir -p .worktrees
git worktree add -b "feat/$TOPIC" ".worktrees/$TOPIC" develop

# 作業ディレクトリへ移動
cd ".worktrees/$TOPIC"
```

---

## 実装指示

あなたはSEO記事自動生成システムのバックエンド実装者です。

### 実装対象

出力検証システム（JSON/CSV）

### 前提

- 仕様書/ROADMAP.md の Step 2 を参照
- フォールバック禁止

### 成果物

```
apps/api/validation/
├── __init__.py
├── base.py              # 共通 Validator インターフェース
├── schemas.py           # ValidationReport 型
├── json_validator.py    # JSON検証
├── csv_validator.py     # CSV検証
├── repairer.py          # 決定的修正（ログ必須）
└── exceptions.py        # 検証関連例外

tests/unit/validation/
├── __init__.py
├── conftest.py
├── test_json_validator.py
├── test_csv_validator.py
├── test_repairer.py
└── fixtures/            # 破壊パターンテスト用
    ├── valid/
    └── invalid/
```

### schemas.py の実装

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Any

class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ValidationIssue(BaseModel):
    severity: ValidationSeverity
    code: str  # e.g., "JSON_TRAILING_COMMA", "CSV_COLUMN_MISMATCH"
    message: str
    location: str | None = None  # e.g., "line 5, column 10"

class RepairAction(BaseModel):
    code: str  # e.g., "REMOVE_TRAILING_COMMA"
    description: str
    applied_at: datetime
    before: str  # 修正前の該当部分
    after: str   # 修正後の該当部分

class ValidationReport(BaseModel):
    valid: bool
    format: str  # "json" | "csv"
    issues: list[ValidationIssue] = []
    repairs: list[RepairAction] = []
    validated_at: datetime
    original_hash: str  # 元データのsha256
    repaired_hash: str | None = None  # 修正後のsha256（修正した場合）
```

### base.py の実装

```python
from abc import ABC, abstractmethod
from .schemas import ValidationReport

class ValidatorInterface(ABC):
    @abstractmethod
    def validate(self, content: str | bytes) -> ValidationReport:
        pass

    @abstractmethod
    def validate_with_schema(
        self,
        content: str | bytes,
        schema: dict
    ) -> ValidationReport:
        pass
```

### json_validator.py の実装要件

- 構文破損検出（末尾カンマ、不正なエスケープ等）
- スキーマ検証（JSON Schema）
- 位置情報付きエラー報告

### csv_validator.py の実装要件

- 列不一致検出
- クオート崩れ検出
- エンコーディング検証（UTF-8 必須）

### repairer.py の実装要件

```python
class Repairer:
    """決定的修正のみ実行（必ずログ記録）"""

    ALLOWED_REPAIRS = [
        "REMOVE_TRAILING_COMMA",      # JSON末尾カンマ除去
        "FIX_UNESCAPED_QUOTES",       # 不正なクオートのエスケープ
        "NORMALIZE_LINE_ENDINGS",     # 改行コード統一
    ]

    def repair(self, content: str, issues: list[ValidationIssue]) -> tuple[str, list[RepairAction]]:
        """
        修正を適用し、適用したアクションのリストを返す
        修正できない場合は例外を投げる（黙って採用しない）
        """
        pass
```

### 修正ポリシー

| 条件                               | 許可            | 備考                     |
| ---------------------------------- | --------------- | ------------------------ |
| 決定的修正（JSON末尾カンマ除去等） | ✅              | 実施ログ必須             |
| 同一条件リトライ（上限3回）        | ✅              | attempt 記録必須         |
| 外部LLMによる再生成                | ⚠️ 明示ON時のみ | 上限・失敗時停止を厳格化 |
| 別モデル/別ツールへの自動切替      | ❌              | 禁止                     |

### 破壊パターンテストスイート

```
tests/unit/validation/fixtures/invalid/
├── trailing_comma.json
├── unescaped_quotes.json
├── truncated.json
├── invalid_utf8.csv
├── column_mismatch.csv
└── unbalanced_quotes.csv
```

### DoD（完了条件）

- [ ] JSON/CSV 入力に対して ValidationReport が必ず機械可読で得られる
- [ ] 修正を行う場合は必ずログに残り、黙って採用されない
- [ ] リトライ/修正の許容範囲がコードで固定されている
- [ ] 破壊パターンテストが全通過
- [ ] pytest が通過
- [ ] mypy が通過

### 禁止事項

- 修正を黙って適用（ログなし）
- 別手段への自動フォールバック
- 非決定的な修正（LLM再生成は明示ON時のみ）

---

## 完了後

```bash
# smokeテスト
pytest tests/unit/validation/ -v

# 型チェック
mypy apps/api/validation/

# コミット
git add .
git commit -m "feat(validation): JSON/CSV検証 + 決定的修正"

# push & PR作成
git push -u origin feat/validation
gh pr create --base develop --title "feat(validation): JSON/CSV検証システム" --body "## 概要
- ValidationReport（機械可読な検査結果）
- JsonValidator, CsvValidator
- Repairer（決定的修正、ログ必須）
- 破壊パターンテストスイート

## テスト
- [x] pytest通過
- [x] mypy通過
- [x] 破壊パターンテスト全通過"
```
