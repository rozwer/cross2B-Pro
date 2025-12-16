"""Core contract module for SEO article generation system.

This module provides:
- GraphState: Central state schema for LangGraph workflows
- ExecutionContext: Runtime execution context
- Error classification: ErrorCategory and StepError
"""

from .context import ExecutionContext
from .errors import ErrorCategory, StepError
from .state import GraphState

__all__ = [
    "GraphState",
    "ExecutionContext",
    "ErrorCategory",
    "StepError",
]
