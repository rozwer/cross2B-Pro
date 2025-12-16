"""Execution context for workflow steps.

ExecutionContext provides runtime information for each step execution,
including retry tracking and timeout configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ExecutionContext:
    """Runtime context passed to each step execution."""

    run_id: str
    step_id: str
    attempt: int
    tenant_id: str
    started_at: datetime
    timeout_seconds: int
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "step_id": self.step_id,
            "attempt": self.attempt,
            "tenant_id": self.tenant_id,
            "started_at": self.started_at.isoformat(),
            "timeout_seconds": self.timeout_seconds,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionContext":
        """Create from dictionary."""
        return cls(
            run_id=data["run_id"],
            step_id=data["step_id"],
            attempt=data["attempt"],
            tenant_id=data["tenant_id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            timeout_seconds=data["timeout_seconds"],
            config=data.get("config", {}),
        )

    def is_first_attempt(self) -> bool:
        """Check if this is the first execution attempt."""
        return self.attempt == 1

    def next_attempt(self) -> "ExecutionContext":
        """Create context for next retry attempt."""
        return ExecutionContext(
            run_id=self.run_id,
            step_id=self.step_id,
            attempt=self.attempt + 1,
            tenant_id=self.tenant_id,
            started_at=datetime.now(),
            timeout_seconds=self.timeout_seconds,
            config=self.config,
        )
