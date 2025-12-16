"""Audit logging with integrity guarantees.

Security requirements:
- All security-sensitive operations must be logged
- Logs must be tamper-evident (hash chain)
- Logs must be append-only (no deletion/modification)
- Critical events must be logged to separate audit log
"""

import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_REFRESH = "auth.token.refresh"
    AUTH_TOKEN_INVALID = "auth.token.invalid"

    # Authorization events
    AUTHZ_ACCESS_GRANTED = "authz.access.granted"
    AUTHZ_ACCESS_DENIED = "authz.access.denied"
    AUTHZ_TENANT_MISMATCH = "authz.tenant.mismatch"

    # Data access events
    DATA_READ = "data.read"
    DATA_CREATE = "data.create"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"

    # Run events
    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_APPROVED = "run.approved"
    RUN_REJECTED = "run.rejected"

    # Security events
    SECURITY_SSRF_BLOCKED = "security.ssrf.blocked"
    SECURITY_INJECTION_DETECTED = "security.injection.detected"
    SECURITY_PATH_TRAVERSAL = "security.path_traversal.blocked"

    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_CONFIG_CHANGE = "system.config.change"


class AuditEvent(BaseModel):
    """Immutable audit event record."""

    # Event identification
    event_id: str = Field(..., description="Unique event ID")
    event_type: AuditEventType = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Actor information
    tenant_id: str | None = Field(default=None, description="Tenant ID")
    user_id: str | None = Field(default=None, description="User ID")
    ip_address: str | None = Field(default=None, description="Client IP address")

    # Context
    resource_type: str | None = Field(default=None, description="Type of resource")
    resource_id: str | None = Field(default=None, description="Resource ID")
    action: str | None = Field(default=None, description="Action performed")

    # Details (must not contain sensitive data)
    details: dict[str, Any] = Field(default_factory=dict)

    # Integrity
    previous_hash: str | None = Field(default=None, description="Hash of previous event")
    event_hash: str | None = Field(default=None, description="Hash of this event")


class AuditLogger:
    """Secure audit logger with integrity guarantees.

    Features:
    - Hash chain for tamper detection
    - Append-only operations
    - Structured logging format
    - Separation of regular and audit logs
    """

    def __init__(
        self,
        log_file: str | None = None,
        enable_hash_chain: bool = True,
    ):
        """Initialize audit logger.

        Args:
            log_file: Path to audit log file (default: from env or stdout)
            enable_hash_chain: Enable hash chain for integrity
        """
        self.log_file = log_file or os.getenv("AUDIT_LOG_FILE")
        self.enable_hash_chain = enable_hash_chain
        self._last_hash: str | None = None
        self._event_count = 0

        # Setup dedicated audit logger
        self._audit_logger = logging.getLogger("audit")
        self._audit_logger.setLevel(logging.INFO)

        # Add file handler if configured
        if self.log_file:
            handler = logging.FileHandler(self.log_file, mode="a")
            handler.setFormatter(
                logging.Formatter("%(message)s")
            )
            self._audit_logger.addHandler(handler)

    def _compute_event_hash(self, event: AuditEvent) -> str:
        """Compute hash for an event including the previous hash."""
        # Create canonical representation (excluding event_hash)
        data = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "tenant_id": event.tenant_id,
            "user_id": event.user_id,
            "ip_address": event.ip_address,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "action": event.action,
            "details": event.details,
            "previous_hash": event.previous_hash,
        }
        canonical = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        import uuid

        self._event_count += 1
        return f"audit-{uuid.uuid4().hex[:12]}-{self._event_count}"

    def log(
        self,
        event_type: AuditEventType,
        tenant_id: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Log an audit event.

        Args:
            event_type: Type of event
            tenant_id: Tenant ID
            user_id: User ID
            ip_address: Client IP
            resource_type: Type of resource
            resource_id: Resource ID
            action: Action performed
            details: Additional details (must not contain sensitive data)

        Returns:
            The created AuditEvent
        """
        # Create event
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            tenant_id=tenant_id,
            user_id=user_id,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            previous_hash=self._last_hash if self.enable_hash_chain else None,
        )

        # Compute hash
        if self.enable_hash_chain:
            event.event_hash = self._compute_event_hash(event)
            self._last_hash = event.event_hash

        # Log to audit log
        log_data = event.model_dump(mode="json")
        self._audit_logger.info(json.dumps(log_data))

        # Also log to regular logger for visibility
        logger.info(
            f"AUDIT: {event_type.value}",
            extra={
                "audit_event_id": event.event_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "resource": f"{resource_type}/{resource_id}" if resource_type else None,
            },
        )

        return event

    def log_auth_success(
        self,
        tenant_id: str,
        user_id: str,
        ip_address: str | None = None,
    ) -> AuditEvent:
        """Log successful authentication."""
        return self.log(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            tenant_id=tenant_id,
            user_id=user_id,
            ip_address=ip_address,
        )

    def log_auth_failure(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        reason: str | None = None,
    ) -> AuditEvent:
        """Log failed authentication attempt."""
        return self.log(
            event_type=AuditEventType.AUTH_LOGIN_FAILURE,
            tenant_id=tenant_id,
            user_id=user_id,
            ip_address=ip_address,
            details={"reason": reason} if reason else {},
        )

    def log_access_denied(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        reason: str | None = None,
    ) -> AuditEvent:
        """Log access denied event."""
        return self.log(
            event_type=AuditEventType.AUTHZ_ACCESS_DENIED,
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details={"reason": reason} if reason else {},
        )

    def log_security_event(
        self,
        event_type: AuditEventType,
        tenant_id: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Log a security-related event."""
        return self.log(
            event_type=event_type,
            tenant_id=tenant_id,
            user_id=user_id,
            ip_address=ip_address,
            details=details or {},
        )

    def verify_chain(self, events: list[AuditEvent]) -> tuple[bool, str | None]:
        """Verify the integrity of an audit log chain.

        Args:
            events: List of events to verify (must be in order)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not events:
            return True, None

        prev_hash = None
        for i, event in enumerate(events):
            # Check previous hash link
            if event.previous_hash != prev_hash:
                return False, f"Chain broken at event {i}: previous_hash mismatch"

            # Verify event hash
            computed_hash = self._compute_event_hash(event)
            if event.event_hash != computed_hash:
                return False, f"Hash mismatch at event {i}: tampering detected"

            prev_hash = event.event_hash

        return True, None


# Global audit logger instance
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
