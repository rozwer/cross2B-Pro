"""
Tool Registry (Manifest)

ツールの登録・取得を管理する。
何が呼べるか / 必要なENVは何か / 何が返るか を一意に定義。
"""

from collections.abc import Callable
from typing import Any

from .base import ToolInterface
from .exceptions import ToolNotFoundError


class ToolManifest:
    """ツールのメタ情報"""

    def __init__(
        self,
        tool_id: str,
        description: str,
        required_env: list[str] | None = None,
        input_schema: dict[str, Any] | None = None,
        output_description: str | None = None,
    ):
        self.tool_id = tool_id
        self.description = description
        self.required_env = required_env or []
        self.input_schema = input_schema or {}
        self.output_description = output_description or ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "description": self.description,
            "required_env": self.required_env,
            "input_schema": self.input_schema,
            "output_description": self.output_description,
        }


class ToolRegistry:
    """
    ツールレジストリ

    全ツールを登録し、tool_idで取得可能にする。
    """

    _tools: dict[str, type[ToolInterface]] = {}
    _manifests: dict[str, ToolManifest] = {}

    @classmethod
    def register(
        cls,
        tool_id: str,
        description: str = "",
        required_env: list[str] | None = None,
        input_schema: dict[str, Any] | None = None,
        output_description: str | None = None,
    ) -> Callable[[type[ToolInterface]], type[ToolInterface]]:
        """
        ツールを登録するデコレータ

        Usage::

            @ToolRegistry.register(
                "serp_fetch", description="SERP取得", required_env=["SERP_API_KEY"]
            )
            class SerpFetchTool(ToolInterface):
                ...
        """

        def decorator(tool_class: type[ToolInterface]) -> type[ToolInterface]:
            tool_class.tool_id = tool_id
            cls._tools[tool_id] = tool_class
            cls._manifests[tool_id] = ToolManifest(
                tool_id=tool_id,
                description=description,
                required_env=required_env,
                input_schema=input_schema,
                output_description=output_description,
            )
            return tool_class

        return decorator

    @classmethod
    def get(cls, tool_id: str) -> ToolInterface:
        """
        tool_idでツールインスタンスを取得

        Raises:
            ToolNotFoundError: ツールが見つからない場合
        """
        if tool_id not in cls._tools:
            raise ToolNotFoundError(tool_id)
        return cls._tools[tool_id]()

    @classmethod
    def get_manifest(cls, tool_id: str) -> ToolManifest:
        """
        tool_idでツールのマニフェストを取得

        Raises:
            ToolNotFoundError: ツールが見つからない場合
        """
        if tool_id not in cls._manifests:
            raise ToolNotFoundError(tool_id)
        return cls._manifests[tool_id]

    @classmethod
    def list_tools(cls) -> list[str]:
        """登録済みツールの一覧を取得"""
        return list(cls._tools.keys())

    @classmethod
    def list_manifests(cls) -> list[ToolManifest]:
        """全ツールのマニフェストを取得"""
        return list(cls._manifests.values())

    @classmethod
    def clear(cls) -> None:
        """レジストリをクリア（テスト用）"""
        cls._tools.clear()
        cls._manifests.clear()
