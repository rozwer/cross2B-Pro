"""Observability module for workflow monitoring.

This module provides:
- Event: Structured event schema
- EventEmitter: DB-persistent event emission
- Structured logging with context
- ErrorCollector: Run-scoped error log collection
- DiagnosticsService: LLM-based failure analysis
"""

from .diagnostics import DiagnosticsService, diagnose_run_failure
from .error_collector import ErrorCollector, LogSource
from .events import Event, EventEmitter, EventType
from .logger import StructuredLogger, get_logger

__all__ = [
    "Event",
    "EventType",
    "EventEmitter",
    "StructuredLogger",
    "get_logger",
    "ErrorCollector",
    "LogSource",
    "DiagnosticsService",
    "diagnose_run_failure",
]
