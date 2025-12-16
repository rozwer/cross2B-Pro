"""LLM クライアントの基底インターフェース.

全てのLLMプロバイダー（Gemini, OpenAI, Anthropic）はこのインターフェースを継承する。
"""

from abc import ABC, abstractmethod
from typing import Any

from .schemas import LLMResponse


class LLMInterface(ABC):
    """LLMクライアントの抽象基底クラス."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """テキスト生成を実行する.

        Args:
            messages: 会話履歴（role/content形式）
            system_prompt: システムプロンプト
            temperature: 生成の多様性（0.0-1.0）
            max_tokens: 最大トークン数

        Returns:
            LLMResponse: 生成結果とメタデータ

        Raises:
            LLMError: API呼び出しエラー時
        """
        pass

    @abstractmethod
    async def generate_json(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """JSON形式での出力を保証する生成を実行する.

        Args:
            messages: 会話履歴
            system_prompt: システムプロンプト
            schema: 期待するJSONスキーマ

        Returns:
            dict: パース済みJSONオブジェクト

        Raises:
            LLMError: API呼び出しエラー時
            ValidationError: JSON検証エラー時
        """
        pass
