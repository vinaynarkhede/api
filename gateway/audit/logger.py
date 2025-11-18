"""Audit logging for compliance and security tracking."""
import time
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.database.connection import db_manager
from gateway.database.repositories import AuditLogRepository
from gateway.monitoring.logger import logger
from shared.utils import get_client_ip


class AuditLogger:
    """
    Audit logger for tracking security-sensitive operations.

    Logs events for compliance with SOC 2, GDPR, HIPAA, etc.
    """

    # Event types for categorization
    EVENT_TYPES = {
        "AUTH_SUCCESS": "Authentication successful",
        "AUTH_FAILED": "Authentication failed",
        "AUTH_LOGOUT": "User logout",
        "API_KEY_CREATED": "API key created",
        "API_KEY_REVOKED": "API key revoked",
        "PERMISSION_DENIED": "Permission denied",
        "RATE_LIMIT_EXCEEDED": "Rate limit exceeded",
        "CONFIG_CHANGED": "Configuration changed",
        "ROUTE_CREATED": "Route created",
        "ROUTE_UPDATED": "Route updated",
        "ROUTE_DELETED": "Route deleted",
        "SESSION_CREATED": "Session created",
        "SESSION_REVOKED": "Session revoked",
        "DATA_ACCESSED": "Sensitive data accessed",
        "DATA_MODIFIED": "Data modified",
        "DATA_DELETED": "Data deleted",
        "SECURITY_VIOLATION": "Security policy violation",
        "CIRCUIT_BREAKER_OPENED": "Circuit breaker opened",
        "CIRCUIT_BREAKER_CLOSED": "Circuit breaker closed",
    }

    def __init__(self):
        """Initialize audit logger."""
        self.repository = AuditLogRepository()

    async def log_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log an audit event to the database.

        Args:
            event_type: Type of event (from EVENT_TYPES)
            user_id: ID of the user performing the action
            username: Username of the user
            resource: Resource being accessed/modified
            action: Action being performed
            result: Result of the action (success, failure, denied)
            ip_address: IP address of the client
            user_agent: User agent string
            request_id: Request ID for correlation
            metadata: Additional metadata as JSON

        Returns:
            True if logged successfully, False otherwise
        """
        try:
            async with db_manager.get_session() as session:
                await self.repository.create(
                    session,
                    event_type=event_type,
                    user_id=user_id,
                    username=username,
                    resource=resource,
                    action=action,
                    result=result,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_id=request_id,
                    metadata=metadata or {},
                )
                await session.commit()

            # Also log to structured logger for immediate visibility
            logger.info(
                "audit_event",
                event_type=event_type,
                user_id=user_id,
                username=username,
                resource=resource,
                action=action,
                result=result,
                ip_address=ip_address,
                request_id=request_id,
            )

            return True

        except Exception as e:
            logger.error(
                "audit_log_failed",
                event_type=event_type,
                error=str(e),
            )
            return False

    async def log_authentication(
        self,
        username: str,
        success: bool,
        ip_address: str,
        user_agent: str,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log authentication attempts."""
        await self.log_event(
            event_type="AUTH_SUCCESS" if success else "AUTH_FAILED",
            username=username,
            resource="authentication",
            action="login",
            result="success" if success else "failure",
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            metadata=metadata,
        )

    async def log_api_key_action(
        self,
        action: str,
        user_id: int,
        username: str,
        api_key_id: int,
        ip_address: str,
        request_id: Optional[str] = None,
    ):
        """Log API key creation/revocation."""
        event_type = f"API_KEY_{action.upper()}"
        await self.log_event(
            event_type=event_type,
            user_id=user_id,
            username=username,
            resource=f"api_key:{api_key_id}",
            action=action,
            result="success",
            ip_address=ip_address,
            request_id=request_id,
        )

    async def log_permission_denied(
        self,
        username: str,
        resource: str,
        action: str,
        ip_address: str,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log permission denied events."""
        await self.log_event(
            event_type="PERMISSION_DENIED",
            username=username,
            resource=resource,
            action=action,
            result="denied",
            ip_address=ip_address,
            request_id=request_id,
            metadata=metadata,
        )

    async def log_rate_limit(
        self,
        username: Optional[str],
        ip_address: str,
        resource: str,
        request_id: Optional[str] = None,
    ):
        """Log rate limit exceeded events."""
        await self.log_event(
            event_type="RATE_LIMIT_EXCEEDED",
            username=username,
            resource=resource,
            action="access",
            result="denied",
            ip_address=ip_address,
            request_id=request_id,
        )

    async def log_config_change(
        self,
        user_id: int,
        username: str,
        resource: str,
        action: str,
        ip_address: str,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log configuration changes."""
        await self.log_event(
            event_type="CONFIG_CHANGED",
            user_id=user_id,
            username=username,
            resource=resource,
            action=action,
            result="success",
            ip_address=ip_address,
            request_id=request_id,
            metadata=metadata,
        )

    async def log_data_access(
        self,
        user_id: int,
        username: str,
        resource: str,
        action: str,
        ip_address: str,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log sensitive data access."""
        event_type = {
            "read": "DATA_ACCESSED",
            "update": "DATA_MODIFIED",
            "delete": "DATA_DELETED",
        }.get(action, "DATA_ACCESSED")

        await self.log_event(
            event_type=event_type,
            user_id=user_id,
            username=username,
            resource=resource,
            action=action,
            result="success",
            ip_address=ip_address,
            request_id=request_id,
            metadata=metadata,
        )

    async def log_security_violation(
        self,
        username: Optional[str],
        violation_type: str,
        resource: str,
        ip_address: str,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log security policy violations."""
        await self.log_event(
            event_type="SECURITY_VIOLATION",
            username=username,
            resource=resource,
            action=violation_type,
            result="blocked",
            ip_address=ip_address,
            request_id=request_id,
            metadata=metadata,
        )

    async def log_from_request(
        self,
        request: Request,
        event_type: str,
        action: str,
        result: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Log an event from a FastAPI request context.

        Automatically extracts IP, user agent, request ID, and user info from request.
        """
        ip_address = get_client_ip(dict(request.headers))
        user_agent = request.headers.get("user-agent")
        request_id = getattr(request.state, "request_id", None)

        # Extract user info if available
        user_data = getattr(request.state, "user", None)
        user_id = user_data.user_id if user_data else None
        username = user_data.username if user_data else None

        await self.log_event(
            event_type=event_type,
            user_id=user_id,
            username=username,
            resource=str(request.url.path),
            action=action,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            metadata=metadata,
        )


# Global audit logger instance
audit_logger = AuditLogger()
