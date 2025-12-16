"""
共通 Tool インターフェース

全ツールはこのインターフェースを実装する。
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .schemas import ToolResult


class ErrorCategory(str, Enum):
    """エラー分類（統一フォーマット）"""

    RETRYABLE = "retryable"  # リトライ可能（ネットワーク一時障害等）
    NON_RETRYABLE = "non_retryable"  # リトライ不可（認証エラー、リソース不存在等）
    VALIDATION_FAIL = "validation_fail"  # 検証失敗（入力不正、出力形式異常等）


class ToolInterface(ABC):
    """
    全ツールの共通インターフェース

    実装者は以下を守ること:
    - tool_id: 一意なツール識別子
    - execute(): 非同期実行メソッド
    - エラー時は適切な ErrorCategory を設定
    - 取得結果には Evidence を付与
    - フォールバック禁止（失敗時に別手段へ切替しない）
    """

    tool_id: str

    @abstractmethod
    async def execute(self, **kwargs: Any) -> "ToolResult":
        """
        ツールを実行する

        Returns:
            ToolResult: 実行結果（成功/失敗、データ、エラー情報、証拠）
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(tool_id={self.tool_id})>"
