# Session 3: Anthropic クライアント

## Phase 1（並列実行可能: Session 1, 2, 3）

---

## 作業開始手順

```bash
cd /home/rozwer/案件
git fetch origin
git pull origin develop

# Worktree作成
TOPIC="llm-anthropic"
mkdir -p .worktrees
git worktree add -b "feat/$TOPIC" ".worktrees/$TOPIC" develop

# 作業ディレクトリへ移動
cd ".worktrees/$TOPIC"
```

---

## 依存関係の確認

**重要**: Session 1 (Gemini) が `apps/api/llm/base.py` と `apps/api/llm/schemas.py` を作成する責任を持っています。

### 開始前チェック

```bash
# base.py が存在するか確認
ls apps/api/llm/base.py 2>/dev/null || echo "base.py not found"
```

**base.py が存在しない場合**:
1. Session 1 のマージを待つ（推奨）
2. または、自分で base.py を作成する（以下の最小実装を使用）

### base.py 最小実装（Session 1 が未完了の場合のみ使用）

```python
# apps/api/llm/base.py
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
        pass
```

---

## 実装指示

あなたはSEO記事自動生成システムのバックエンド実装者です。

### 実装対象

Anthropic API クライアントモジュール

### 前提

- 仕様書/ROADMAP.md の Step 1 を参照
- 仕様書/backend/llm.md を参照
- フォールバック全面禁止

### 成果物

```
apps/api/llm/
├── anthropic.py     # Anthropicクライアント実装

tests/unit/llm/
├── test_anthropic.py
```

### anthropic.py の実装要件

- LLMInterface を継承（apps/api/llm/base.py）
- generate() と generate_json() メソッド実装
- 対象モデル: claude-sonnet-4-20250514, claude-opus-4-20250514 等
- token_usage の記録必須
- エラー分類: RETRYABLE / NON_RETRYABLE / VALIDATION_FAIL
- リトライ上限3回、ログ必須

### 実装例

```python
# apps/api/llm/anthropic.py
import os
from anthropic import AsyncAnthropic
from .base import LLMInterface
from .schemas import LLMResponse, TokenUsage, ErrorCategory
from .exceptions import LLMError

class AnthropicClient(LLMInterface):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_retries: int = 3,
    ):
        self.client = AsyncAnthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model
        self.max_retries = max_retries

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        # Anthropic の messages API を使用
        # system は別パラメータで渡す
        pass

    async def generate_json(
        self,
        messages: list[dict],
        system_prompt: str,
        schema: dict,
    ) -> dict:
        # JSON モードを使用（tool_use または structured output）
        pass
```

### DoD（完了条件）

- [ ] apps/api/llm/anthropic.py が作成されている
- [ ] LLMInterface を正しく継承している
- [ ] .env にキー設定後、呼び出し→レスポンス取得が確認できる
- [ ] エラーハンドリングが統一フォーマット
- [ ] モデル自動切替のフォールバック経路が存在しない
- [ ] pytest が通過
- [ ] mypy が通過

### 禁止事項

- 別モデル/別プロバイダへの自動フォールバック
- モック返却（明示指定時のみ許可）

---

## 完了後

```bash
# smokeテスト
pytest tests/unit/llm/test_anthropic.py -v

# 型チェック
mypy apps/api/llm/anthropic.py

# コミット
git add .
git commit -m "feat(llm): Anthropic クライアント実装"

# push & PR作成
git push -u origin feat/llm-anthropic
gh pr create --base develop --title "feat(llm): Anthropic クライアント" --body "## 概要
- AnthropicClient 実装
- claude-sonnet-4, claude-opus-4 対応

## 依存
- feat/llm-gemini (base.py, schemas.py)

## テスト
- [x] pytest通過
- [x] mypy通過"
```
