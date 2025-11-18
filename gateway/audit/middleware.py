"""Audit logging middleware for automatic event tracking."""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from gateway.audit.logger import audit_logger
from gateway.monitoring.logger import logger
from shared.utils import get_client_ip


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log audit events for sensitive operations.

    This middleware tracks:
    - Authentication attempts
    - Authorization failures
    - Configuration changes (admin endpoints)
    - Sensitive data access
    - Security violations
    """

    # Paths that should trigger audit logging
    AUDIT_PATHS = {
        "/api/auth/": "authentication",
        "/api/admin/": "configuration",
        "/admin/": "configuration",
        "/api/users/": "user_management",
        "/api/keys/": "api_key_management",
    }

    # HTTP methods that modify data
    MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log audit events as appropriate.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from downstream handler
        """
        start_time = time.time()
        path = str(request.url.path)
        method = request.method

        # Check if this path should be audited
        should_audit = any(path.startswith(audit_path) for audit_path in self.AUDIT_PATHS)

        # Always audit mutating operations on sensitive endpoints
        if method in self.MUTATING_METHODS and should_audit:
            should_audit = True

        try:
            # Call the next handler
            response = await call_next(request)

            # Log audit event after successful response
            if should_audit:
                await self._log_audit_event(
                    request=request,
                    response=response,
                    duration_ms=(time.time() - start_time) * 1000,
                )

            return response

        except Exception as e:
            # Log failed operations
            if should_audit:
                await self._log_failed_audit_event(
                    request=request,
                    error=e,
                    duration_ms=(time.time() - start_time) * 1000,
                )
            raise

    async def _log_audit_event(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
    ):
        """
        Log successful audit event.

        Args:
            request: FastAPI request
            response: Response object
            duration_ms: Request duration in milliseconds
        """
        path = str(request.url.path)
        method = request.method
        status_code = response.status_code

        # Extract request context
        ip_address = get_client_ip(dict(request.headers))
        user_agent = request.headers.get("user-agent")
        request_id = getattr(request.state, "request_id", None)

        # Extract user info if authenticated
        user_data = getattr(request.state, "user", None)
        user_id = user_data.user_id if user_data else None
        username = user_data.username if user_data else "anonymous"

        # Determine event type and action
        event_type, action = self._categorize_request(path, method, status_code)

        # Determine result
        if 200 <= status_code < 300:
            result = "success"
        elif status_code == 401:
            result = "unauthorized"
        elif status_code == 403:
            result = "forbidden"
        elif status_code == 429:
            result = "rate_limited"
        else:
            result = "failure"

        # Log to audit trail
        try:
            await audit_logger.log_event(
                event_type=event_type,
                user_id=user_id,
                username=username,
                resource=path,
                action=action,
                result=result,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                metadata={
                    "method": method,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )
        except Exception as e:
            # Don't fail the request if audit logging fails
            logger.error("audit_middleware_error", error=str(e), path=path)

    async def _log_failed_audit_event(
        self,
        request: Request,
        error: Exception,
        duration_ms: float,
    ):
        """
        Log failed operation to audit trail.

        Args:
            request: FastAPI request
            error: Exception that was raised
            duration_ms: Request duration in milliseconds
        """
        path = str(request.url.path)
        method = request.method

        # Extract request context
        ip_address = get_client_ip(dict(request.headers))
        user_agent = request.headers.get("user-agent")
        request_id = getattr(request.state, "request_id", None)

        # Extract user info if available
        user_data = getattr(request.state, "user", None)
        user_id = user_data.user_id if user_data else None
        username = user_data.username if user_data else "anonymous"

        # Determine event type
        event_type = "SECURITY_VIOLATION" if "security" in str(error).lower() else "DATA_MODIFIED"

        try:
            await audit_logger.log_event(
                event_type=event_type,
                user_id=user_id,
                username=username,
                resource=path,
                action=method.lower(),
                result="failure",
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                metadata={
                    "method": method,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "duration_ms": round(duration_ms, 2),
                },
            )
        except Exception as e:
            # Don't fail the request if audit logging fails
            logger.error("audit_middleware_error", error=str(e), path=path)

    def _categorize_request(self, path: str, method: str, status_code: int) -> tuple[str, str]:
        """
        Categorize request into event type and action.

        Args:
            path: Request path
            method: HTTP method
            status_code: Response status code

        Returns:
            Tuple of (event_type, action)
        """
        # Authentication endpoints
        if "/auth/login" in path or "/token" in path:
            if status_code == 200:
                return ("AUTH_SUCCESS", "login")
            else:
                return ("AUTH_FAILED", "login")

        if "/auth/logout" in path:
            return ("AUTH_LOGOUT", "logout")

        # API key management
        if "/keys" in path:
            if method == "POST":
                return ("API_KEY_CREATED", "create")
            elif method == "DELETE":
                return ("API_KEY_REVOKED", "revoke")

        # Configuration changes
        if "/admin/config" in path or "/admin/routes" in path:
            if method == "POST":
                return ("CONFIG_CHANGED", "create")
            elif method == "PUT" or method == "PATCH":
                return ("CONFIG_CHANGED", "update")
            elif method == "DELETE":
                return ("CONFIG_CHANGED", "delete")
            else:
                return ("CONFIG_CHANGED", "read")

        # Session management
        if "/sessions" in path:
            if method == "POST":
                return ("SESSION_CREATED", "create")
            elif method == "DELETE":
                return ("SESSION_REVOKED", "revoke")

        # Data access/modification
        if method == "GET":
            return ("DATA_ACCESSED", "read")
        elif method in ["POST", "PUT", "PATCH"]:
            return ("DATA_MODIFIED", "update")
        elif method == "DELETE":
            return ("DATA_DELETED", "delete")

        # Default
        return ("DATA_ACCESSED", method.lower())
