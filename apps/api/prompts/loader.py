"""Prompt pack loading and management.

IMPORTANT: Auto-execution without explicit pack_id is forbidden.
All prompt loading requires an explicit pack_id parameter.

Prompts are loaded from JSON files in the packs/ directory.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class PromptPackError(Exception):
    """Error in prompt pack operations."""

    pass


class PromptPackNotFoundError(PromptPackError):
    """Prompt pack does not exist."""

    pass


class PromptNotFoundError(PromptPackError):
    """Prompt for step does not exist in pack."""

    pass


# Directory containing prompt pack JSON files
PACKS_DIR = Path(__file__).parent / "packs"


@dataclass
class PromptTemplate:
    """A single prompt template with variables."""

    step: str
    version: int
    content: str
    variables: dict[str, Any] = field(default_factory=dict)

    def render(self, **kwargs: Any) -> str:
        """Render the prompt with provided variables.

        Args:
            **kwargs: Variable values to substitute

        Returns:
            Rendered prompt string

        Raises:
            PromptPackError: If required variable is missing
        """
        result = self.content

        # Check for required variables
        for var_name, var_info in self.variables.items():
            if var_info.get("required", False) and var_name not in kwargs:
                raise PromptPackError(f"Missing required variable: {var_name}")

        # Substitute variables
        for key, value in kwargs.items():
            placeholder = f"{{{{{key}}}}}"  # {{variable}}
            result = result.replace(placeholder, str(value))

        return result


@dataclass
class PromptPack:
    """Collection of prompts for a workflow.

    A prompt pack contains all prompts needed for a complete workflow run.
    Each step has exactly one prompt template.
    """

    pack_id: str
    prompts: dict[str, PromptTemplate] = field(default_factory=dict)

    def get_prompt(self, step: str) -> PromptTemplate:
        """Get prompt template for a step.

        Args:
            step: Step identifier

        Returns:
            PromptTemplate for the step

        Raises:
            PromptNotFoundError: If no prompt exists for the step
        """
        if step not in self.prompts:
            raise PromptNotFoundError(
                f"No prompt found for step '{step}' in pack '{self.pack_id}'"
            )
        return self.prompts[step]

    def render_prompt(self, step: str, **kwargs: Any) -> str:
        """Render a prompt for a step with variables.

        Args:
            step: Step identifier
            **kwargs: Variable values

        Returns:
            Rendered prompt string
        """
        template = self.get_prompt(step)
        return template.render(**kwargs)

    def list_steps(self) -> list[str]:
        """List all steps with prompts in this pack."""
        return list(self.prompts.keys())


class PromptPackLoader:
    """Loads prompt packs from JSON files.

    CRITICAL: Auto-execution without explicit pack_id is FORBIDDEN.
    All load operations require a non-None pack_id.

    Packs are loaded from apps/api/prompts/packs/{pack_id}.json
    """

    def __init__(self, packs_dir: Path | None = None) -> None:
        """Initialize loader.

        Args:
            packs_dir: Directory containing prompt pack JSON files.
                      Defaults to apps/api/prompts/packs/
        """
        self._packs_dir = packs_dir or PACKS_DIR
        self._cache: dict[str, PromptPack] = {}

    def load(self, pack_id: str | None) -> PromptPack:
        """Load a prompt pack by ID from JSON file.

        CRITICAL: pack_id is REQUIRED. Auto-execution is forbidden.

        Args:
            pack_id: Prompt pack identifier (corresponds to {pack_id}.json)

        Returns:
            PromptPack instance

        Raises:
            ValueError: If pack_id is None
            PromptPackNotFoundError: If pack does not exist
        """
        if pack_id is None:
            raise ValueError(
                "pack_id is required. Auto-execution without explicit pack_id is forbidden."
            )

        # Check cache
        if pack_id in self._cache:
            return self._cache[pack_id]

        # Handle mock pack for testing
        if pack_id == "mock_pack":
            pack = self._load_mock_pack()
            self._cache[pack_id] = pack
            return pack

        # Load from JSON file
        pack = self._load_from_json(pack_id)
        self._cache[pack_id] = pack
        return pack

    async def load_async(self, pack_id: str | None) -> PromptPack:
        """Load a prompt pack by ID (async wrapper).

        CRITICAL: pack_id is REQUIRED. Auto-execution is forbidden.

        This is an async wrapper for compatibility. JSON file loading
        is synchronous but wrapped for API consistency.

        Args:
            pack_id: Prompt pack identifier

        Returns:
            PromptPack instance

        Raises:
            ValueError: If pack_id is None
            PromptPackNotFoundError: If pack does not exist
        """
        return self.load(pack_id)

    def _load_from_json(self, pack_id: str) -> PromptPack:
        """Load prompt pack from JSON file.

        Args:
            pack_id: Pack identifier (filename without .json)

        Returns:
            PromptPack instance

        Raises:
            PromptPackNotFoundError: If JSON file not found
            PromptPackError: If JSON is invalid
        """
        json_path = self._packs_dir / f"{pack_id}.json"

        if not json_path.exists():
            raise PromptPackNotFoundError(
                f"Prompt pack '{pack_id}' not found at {json_path}"
            )

        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise PromptPackError(f"Invalid JSON in pack '{pack_id}': {e}") from e

        # Parse prompts from JSON
        prompts: dict[str, PromptTemplate] = {}
        prompts_data = data.get("prompts", {})

        for step_id, prompt_data in prompts_data.items():
            prompts[step_id] = PromptTemplate(
                step=prompt_data.get("step", step_id),
                version=prompt_data.get("version", 1),
                content=prompt_data.get("content", ""),
                variables=prompt_data.get("variables", {}),
            )

        return PromptPack(pack_id=pack_id, prompts=prompts)

    def _load_mock_pack(self) -> PromptPack:
        """Load mock prompt pack for testing."""
        return PromptPack(
            pack_id="mock_pack",
            prompts={
                "step0": PromptTemplate(
                    step="step0",
                    version=1,
                    content="Analyze the keyword: {{keyword}}\n\nJSON形式で出力してください。",
                    variables={"keyword": {"required": True, "type": "string"}},
                ),
                "step3a": PromptTemplate(
                    step="step3a",
                    version=1,
                    content="Query analysis for: {{keyword}}\n"
                    "Analysis: {{keyword_analysis}}\n"
                    "Competitors: {{competitor_count}}",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "keyword_analysis": {"required": False, "type": "string"},
                        "competitor_count": {"required": False, "type": "number"},
                    },
                ),
                "step3b": PromptTemplate(
                    step="step3b",
                    version=1,
                    content="Co-occurrence analysis for: {{keyword}}\n"
                    "Summaries: {{competitor_summaries}}",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "competitor_summaries": {"required": False, "type": "array"},
                    },
                ),
                "step3c": PromptTemplate(
                    step="step3c",
                    version=1,
                    content="Competitor analysis for: {{keyword}}\nCompetitors: {{competitors}}",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "competitors": {"required": False, "type": "array"},
                    },
                ),
                "step6_5": PromptTemplate(
                    step="step6_5",
                    version=1,
                    content="Create integration package for: {{keyword}}",
                    variables={"keyword": {"required": True, "type": "string"}},
                ),
                "step7a": PromptTemplate(
                    step="step7a",
                    version=1,
                    content="Generate draft for: {{keyword}}\nPackage: {{integration_package}}",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "integration_package": {"required": True, "type": "string"},
                    },
                ),
                "step7b": PromptTemplate(
                    step="step7b",
                    version=1,
                    content="Polish draft for: {{keyword}}\nDraft: {{draft}}",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "draft": {"required": True, "type": "string"},
                    },
                ),
                "step9": PromptTemplate(
                    step="step9",
                    version=1,
                    content="Final rewrite for: {{keyword}}\nPolished: {{polished_content}}",
                    variables={
                        "keyword": {"required": True, "type": "string"},
                        "polished_content": {"required": True, "type": "string"},
                        "faq": {"required": False, "type": "string"},
                        "verification_notes": {"required": False, "type": "string"},
                    },
                ),
            },
        )

    def list_packs(self) -> list[str]:
        """List available prompt pack IDs."""
        if not self._packs_dir.exists():
            return []
        return [p.stem for p in self._packs_dir.glob("*.json")]

    def clear_cache(self) -> None:
        """Clear the prompt pack cache."""
        self._cache.clear()

    def invalidate(self, pack_id: str) -> None:
        """Remove a specific pack from cache."""
        self._cache.pop(pack_id, None)
