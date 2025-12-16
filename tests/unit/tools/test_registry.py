"""
ToolRegistry のテスト
"""

import pytest

from apps.api.tools import ToolRegistry, ToolInterface, ToolResult, ToolNotFoundError


class TestToolRegistry:
    """ToolRegistry のテスト"""

    def test_register_and_get_tool(self):
        """ツールの登録と取得"""

        @ToolRegistry.register(
            tool_id="test_tool",
            description="テスト用ツール",
            required_env=["TEST_API_KEY"],
        )
        class TestTool(ToolInterface):
            tool_id = "test_tool"

            async def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, data={"test": "data"})

        # ツールが登録されていることを確認
        assert "test_tool" in ToolRegistry.list_tools()

        # ツールを取得
        tool = ToolRegistry.get("test_tool")
        assert isinstance(tool, TestTool)
        assert tool.tool_id == "test_tool"

    def test_get_manifest(self):
        """マニフェストの取得"""

        @ToolRegistry.register(
            tool_id="manifest_test",
            description="マニフェストテスト",
            required_env=["API_KEY"],
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            output_description="テスト出力",
        )
        class ManifestTestTool(ToolInterface):
            tool_id = "manifest_test"

            async def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True)

        manifest = ToolRegistry.get_manifest("manifest_test")
        assert manifest.tool_id == "manifest_test"
        assert manifest.description == "マニフェストテスト"
        assert manifest.required_env == ["API_KEY"]
        assert "query" in manifest.input_schema.get("properties", {})
        assert manifest.output_description == "テスト出力"

    def test_get_unknown_tool_raises_error(self):
        """存在しないツールの取得でエラー"""
        with pytest.raises(ToolNotFoundError) as exc_info:
            ToolRegistry.get("nonexistent_tool")

        assert "nonexistent_tool" in str(exc_info.value)

    def test_list_tools(self):
        """登録済みツール一覧の取得"""
        tools = ToolRegistry.list_tools()
        assert isinstance(tools, list)

        # 基本ツールが登録されていることを確認
        assert "serp_fetch" in tools
        assert "search_volume" in tools
        assert "related_keywords" in tools
        assert "page_fetch" in tools
        assert "pdf_extract" in tools
        assert "primary_collector" in tools
        assert "url_verify" in tools

    def test_list_manifests(self):
        """全マニフェストの取得"""
        manifests = ToolRegistry.list_manifests()
        assert isinstance(manifests, list)
        assert len(manifests) > 0

        # 各マニフェストに必要な属性があることを確認
        for manifest in manifests:
            assert hasattr(manifest, "tool_id")
            assert hasattr(manifest, "description")
            assert hasattr(manifest, "required_env")

    def test_manifest_to_dict(self):
        """マニフェストの辞書変換"""
        manifest = ToolRegistry.get_manifest("serp_fetch")
        manifest_dict = manifest.to_dict()

        assert isinstance(manifest_dict, dict)
        assert "tool_id" in manifest_dict
        assert "description" in manifest_dict
        assert "required_env" in manifest_dict
        assert "input_schema" in manifest_dict
        assert "output_description" in manifest_dict
