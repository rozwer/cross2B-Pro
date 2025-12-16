# Session 1: Gemini クライアント

## Phase 1（並列実行可能: Session 1, 2, 3）

---

## 作業開始手順

```bash
cd /home/rozwer/案件
git fetch origin
git pull origin develop

# Worktree作成
TOPIC="llm-gemini"
mkdir -p .worktrees
git worktree add -b "feat/$TOPIC" ".worktrees/$TOPIC" develop

# 作業ディレクトリへ移動
cd ".worktrees/$TOPIC"
```

---

## 実装指示

あなたはSEO記事自動生成システムのバックエンド実装者です。

### 実装対象

Gemini API クライアントモジュール

### 前提

- 仕様書/ROADMAP.md の Step 1 を参照
- 仕様書/backend/llm.md を参照
- フォールバック全面禁止（別モデルへの自動切替禁止）
- grounding オプション必須対応
- **このセッションで base.py（共通インターフェース）も作成する**（他セッションが参照するため）

### 成果物

```
apps/api/llm/
├── __init__.py
├── base.py          # 共通LLMインターフェース【最優先で作成】
├── schemas.py       # LLMResponse等の型定義【最優先で作成】
├── gemini.py        # Geminiクライアント実装
└── exceptions.py    # LLM関連例外

tests/unit/llm/
├── __init__.py
├── test_gemini.py
└── conftest.py
```

### base.py の実装

```python
from abc import ABC, abstractmethod
from typing import Any

class LLMInterface(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> "LLMResponse":
        pass

    @abstractmethod
    async def generate_json(
        self,
        messages: list[dict],
        system_prompt: str,
        schema: dict[str, Any],
    ) -> dict:
        """JSON出力を保証"""
        pass
```

### schemas.py の実装

```python
from pydantic import BaseModel
from enum import Enum

class ErrorCategory(str, Enum):
    RETRYABLE = "retryable"           # タイムアウト、レート制限等
    NON_RETRYABLE = "non_retryable"   # 認証エラー等
    VALIDATION_FAIL = "validation_fail"  # スキーマ違反等

class TokenUsage(BaseModel):
    input: int
    output: int

class LLMResponse(BaseModel):
    content: str
    token_usage: TokenUsage
    model: str
```

### gemini.py の実装要件

- LLMInterface を継承
- generate() と generate_json() メソッド実装
- 対象モデル: gemini-2.0-flash, gemini-2.5-pro 等
- grounding on/off 切替可能
- token_usage の記録必須
- エラー分類: RETRYABLE / NON_RETRYABLE / VALIDATION_FAIL
- リトライ上限3回、ログ必須

### DoD（完了条件）

- [ ] apps/api/llm/base.py が作成されている
- [ ] apps/api/llm/schemas.py が作成されている
- [ ] .env にキー設定後、呼び出し→レスポンス取得が確認できる
- [ ] grounding オプション切替が動作する
- [ ] エラーハンドリングが統一フォーマット
- [ ] モデル自動切替のフォールバック経路が存在しない
- [ ] pytest が通過
- [ ] mypy が通過

### 禁止事項

- 別モデル/別プロバイダへの自動フォールバック
- モック返却（明示指定時のみ許可）
- base.py を他のセッションに任せる（このセッションで必ず作成）

---

## 完了後

```bash
# smokeテスト
pytest tests/unit/llm/ -v

# 型チェック
mypy apps/api/llm/

# コミット
git add .
git commit -m "feat(llm): Gemini クライアント実装 + 共通インターフェース"

# push & PR作成
git push -u origin feat/llm-gemini
gh pr create --base develop --title "feat(llm): Gemini クライアント + 共通インターフェース" --body "## 概要
- LLMInterface（共通インターフェース）
- LLMResponse, ErrorCategory（型定義）
- GeminiClient（grounding対応）

## テスト
- [x] pytest通過
- [x] mypy通過"
```
