"""Prompt pack loading and management.

IMPORTANT: Auto-execution without explicit pack_id is forbidden.
All prompt loading requires an explicit pack_id parameter.
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PromptPackError(Exception):
    """Error in prompt pack operations."""

    pass


class PromptPackNotFoundError(PromptPackError):
    """Prompt pack does not exist."""

    pass


class PromptNotFoundError(PromptPackError):
    """Prompt for step does not exist in pack."""

    pass


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
    """Loads prompt packs from database.

    CRITICAL: Auto-execution without explicit pack_id is FORBIDDEN.
    All load operations require a non-None pack_id.
    """

    def __init__(self, session_factory: Any | None = None) -> None:
        """Initialize loader.

        Args:
            session_factory: Async session factory for DB access
        """
        self._session_factory = session_factory
        self._cache: dict[str, PromptPack] = {}

    def load(self, pack_id: str | None) -> PromptPack:
        """Load a prompt pack by ID (sync wrapper).

        CRITICAL: pack_id is REQUIRED. Auto-execution is forbidden.

        Args:
            pack_id: Prompt pack identifier

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

        # This is a sync wrapper - actual DB loading happens in async version
        raise PromptPackNotFoundError(
            f"Pack '{pack_id}' not found. Use async load_async() for DB access."
        )

    async def load_async(self, pack_id: str | None) -> PromptPack:
        """Load a prompt pack by ID from database.

        CRITICAL: pack_id is REQUIRED. Auto-execution is forbidden.

        Args:
            pack_id: Prompt pack identifier

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

        # Load from database
        pack = await self._load_from_db(pack_id)
        self._cache[pack_id] = pack
        return pack

    async def _load_from_db(self, pack_id: str) -> PromptPack:
        """Load prompt pack from database.

        Pack ID format: "{tenant_id}:{version}" or just version number.
        """
        if not self._session_factory:
            raise PromptPackError("No session factory configured")

        async with self._session_factory() as session:
            return await self._load_from_session(pack_id, session)

    async def _load_from_session(
        self,
        pack_id: str,
        session: AsyncSession,
    ) -> PromptPack:
        """Load prompt pack using provided session."""
        # Query active prompts for this pack
        result = await session.execute(
            text(
                """
                SELECT step, version, content, variables
                FROM prompts
                WHERE is_active = true
                ORDER BY step, version DESC
            """
            )
        )
        rows = result.fetchall()

        if not rows:
            raise PromptPackNotFoundError(f"No prompts found for pack '{pack_id}'")

        # Build prompt pack - take latest version per step
        prompts: dict[str, PromptTemplate] = {}
        for row in rows:
            if row.step not in prompts:
                prompts[row.step] = PromptTemplate(
                    step=row.step,
                    version=row.version,
                    content=row.content,
                    variables=row.variables or {},
                )

        return PromptPack(pack_id=pack_id, prompts=prompts)

    def _load_mock_pack(self) -> PromptPack:
        """Load mock prompt pack for testing."""
        return PromptPack(
            pack_id="mock_pack",
            prompts={
                "step_0_keyword_research": PromptTemplate(
                    step="step_0_keyword_research",
                    version=1,
                    content="Analyze the keyword: {{keyword}}",
                    variables={"keyword": {"required": True, "type": "string"}},
                ),
                "step_1_structure": PromptTemplate(
                    step="step_1_structure",
                    version=1,
                    content="Create article structure for: {{topic}}",
                    variables={"topic": {"required": True, "type": "string"}},
                ),
                "step_2_draft": PromptTemplate(
                    step="step_2_draft",
                    version=1,
                    content="Write draft based on structure: {{structure}}",
                    variables={"structure": {"required": True, "type": "string"}},
                ),
                "step_3_review": PromptTemplate(
                    step="step_3_review",
                    version=1,
                    content="Review draft for quality: {{draft}}",
                    variables={"draft": {"required": True, "type": "string"}},
                ),
            },
        )

    def clear_cache(self) -> None:
        """Clear the prompt pack cache."""
        self._cache.clear()

    def invalidate(self, pack_id: str) -> None:
        """Remove a specific pack from cache."""
        self._cache.pop(pack_id, None)
