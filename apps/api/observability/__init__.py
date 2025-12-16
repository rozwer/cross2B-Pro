"""Observability module for workflow monitoring.

This module provides:
- Event: Structured event schema
- EventEmitter: DB-persistent event emission
- Structured logging with context
"""

from .events import Event, EventEmitter, EventType
from .logger import StructuredLogger, get_logger

__all__ = [
    "Event",
    "EventType",
    "EventEmitter",
    "StructuredLogger",
    "get_logger",
]
