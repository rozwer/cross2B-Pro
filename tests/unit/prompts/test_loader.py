"""Tests for prompt pack loading."""

import pytest

from apps.api.prompts.loader import (
    PromptNotFoundError,
    PromptPack,
    PromptPackError,
    PromptPackLoader,
    PromptTemplate,
)


class TestPromptTemplate:
    """Tests for PromptTemplate."""

    def test_render_simple(self) -> None:
        """Test simple variable substitution."""
        template = PromptTemplate(
            step="step_1",
            version=1,
            content="Hello, {{name}}!",
            variables={"name": {"required": True, "type": "string"}},
        )
        result = template.render(name="World")
        assert result == "Hello, World!"

    def test_render_multiple_variables(self) -> None:
        """Test multiple variable substitution."""
        template = PromptTemplate(
            step="step_1",
            version=1,
            content="Create {{type}} article about {{topic}}",
            variables={
                "type": {"required": True},
                "topic": {"required": True},
            },
        )
        result = template.render(type="SEO", topic="Python")
        assert result == "Create SEO article about Python"

    def test_render_missing_required_variable(self) -> None:
        """Test that missing required variable raises error."""
        template = PromptTemplate(
            step="step_1",
            version=1,
            content="Hello, {{name}}!",
            variables={"name": {"required": True, "type": "string"}},
        )
        with pytest.raises(PromptPackError, match="Missing required variable"):
            template.render()

    def test_render_optional_variable(self) -> None:
        """Test that optional variables don't raise errors."""
        template = PromptTemplate(
            step="step_1",
            version=1,
            content="Hello, {{name}}! Welcome to {{place}}.",
            variables={
                "name": {"required": True},
                "place": {"required": False},
            },
        )
        # place is optional, so this should not raise
        result = template.render(name="User")
        assert "{{place}}" in result  # Unsubstituted placeholder remains


class TestPromptPack:
    """Tests for PromptPack."""

    def test_get_prompt(self) -> None:
        """Test getting prompt by step."""
        pack = PromptPack(
            pack_id="test_pack",
            prompts={
                "step_1": PromptTemplate(
                    step="step_1",
                    version=1,
                    content="Step 1 prompt",
                ),
            },
        )
        template = pack.get_prompt("step_1")
        assert template.content == "Step 1 prompt"

    def test_get_prompt_not_found(self) -> None:
        """Test that missing prompt raises error."""
        pack = PromptPack(pack_id="test_pack", prompts={})
        with pytest.raises(PromptNotFoundError, match="No prompt found"):
            pack.get_prompt("missing_step")

    def test_render_prompt(self) -> None:
        """Test rendering prompt by step."""
        pack = PromptPack(
            pack_id="test_pack",
            prompts={
                "step_1": PromptTemplate(
                    step="step_1",
                    version=1,
                    content="Analyze: {{keyword}}",
                    variables={"keyword": {"required": True}},
                ),
            },
        )
        result = pack.render_prompt("step_1", keyword="SEO")
        assert result == "Analyze: SEO"

    def test_list_steps(self) -> None:
        """Test listing available steps."""
        pack = PromptPack(
            pack_id="test_pack",
            prompts={
                "step_1": PromptTemplate(step="step_1", version=1, content="1"),
                "step_2": PromptTemplate(step="step_2", version=1, content="2"),
            },
        )
        steps = pack.list_steps()
        assert sorted(steps) == ["step_1", "step_2"]


class TestPromptPackLoader:
    """Tests for PromptPackLoader."""

    def test_load_requires_pack_id(self) -> None:
        """Test that load raises error when pack_id is None."""
        loader = PromptPackLoader()
        with pytest.raises(ValueError, match="pack_id is required"):
            loader.load(None)

    def test_load_mock_pack(self) -> None:
        """Test loading mock pack for testing."""
        loader = PromptPackLoader()
        pack = loader.load("mock_pack")
        assert pack.pack_id == "mock_pack"
        assert "step_0_keyword_research" in pack.list_steps()
        assert "step_1_structure" in pack.list_steps()

    def test_mock_pack_renders_correctly(self) -> None:
        """Test that mock pack prompts render correctly."""
        loader = PromptPackLoader()
        pack = loader.load("mock_pack")
        result = pack.render_prompt("step_0_keyword_research", keyword="Python SEO")
        assert "Python SEO" in result

    @pytest.mark.asyncio
    async def test_load_async_requires_pack_id(self) -> None:
        """Test that async load raises error when pack_id is None."""
        loader = PromptPackLoader()
        with pytest.raises(ValueError, match="pack_id is required"):
            await loader.load_async(None)

    @pytest.mark.asyncio
    async def test_load_async_mock_pack(self) -> None:
        """Test async loading of mock pack."""
        loader = PromptPackLoader()
        pack = await loader.load_async("mock_pack")
        assert pack.pack_id == "mock_pack"

    def test_cache_works(self) -> None:
        """Test that packs are cached."""
        loader = PromptPackLoader()
        pack1 = loader.load("mock_pack")
        pack2 = loader.load("mock_pack")
        assert pack1 is pack2

    def test_clear_cache(self) -> None:
        """Test clearing the cache."""
        loader = PromptPackLoader()
        loader.load("mock_pack")
        loader.clear_cache()
        assert "mock_pack" not in loader._cache

    def test_invalidate_specific_pack(self) -> None:
        """Test invalidating specific pack."""
        loader = PromptPackLoader()
        loader.load("mock_pack")
        loader.invalidate("mock_pack")
        assert "mock_pack" not in loader._cache
