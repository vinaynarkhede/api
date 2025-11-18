"""Multi-tenancy middleware for tenant isolation and management."""
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from gateway.database.connection import db_manager
from gateway.database.repositories import TenantRepository
from gateway.monitoring.logger import logger
from shared.exceptions import TenantNotFound, TenantSuspended


class TenancyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for multi-tenancy support.

    Features:
    - Tenant identification from headers or subdomain
    - Tenant validation and status checking
    - Quota enforcement (request limits, rate limits)
    - Tenant context injection into request state
    """

    # Header name for tenant identification
    TENANT_HEADER = "X-Tenant-ID"

    # Paths that don't require tenant identification
    EXEMPT_PATHS = [
        "/health/",
        "/api/health",
        "/api/metrics",
        "/api/docs",
        "/api/redoc",
        "/openapi.json",
    ]

    def __init__(self, app, require_tenant: bool = True):
        """
        Initialize tenancy middleware.

        Args:
            app: FastAPI application
            require_tenant: Whether to require tenant ID for all requests
        """
        super().__init__(app)
        self.require_tenant = require_tenant
        self.repository = TenantRepository()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with tenant context.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from downstream handler
        """
        path = str(request.url.path)

        # Skip tenant check for exempt paths
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return await call_next(request)

        # Extract tenant ID
        tenant_id = await self._extract_tenant_id(request)

        # If tenant is required but not provided
        if self.require_tenant and not tenant_id:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "TenantRequired",
                    "message": f"Tenant ID must be provided in {self.TENANT_HEADER} header",
                },
            )

        # If tenant ID is provided, validate it
        if tenant_id:
            try:
                tenant = await self._validate_tenant(tenant_id)

                # Add tenant to request state
                request.state.tenant_id = tenant.tenant_id
                request.state.tenant = tenant

                # Check if tenant has exceeded quotas
                if not await self._check_quotas(tenant, request):
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "QuotaExceeded",
                            "message": "Tenant has exceeded usage quotas",
                        },
                    )

            except TenantNotFound as e:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": "TenantNotFound",
                        "message": str(e),
                    },
                )

            except TenantSuspended as e:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "TenantSuspended",
                        "message": str(e),
                    },
                )

        # Process request
        response = await call_next(request)

        # Add tenant ID to response headers for tracking
        if tenant_id:
            response.headers["X-Tenant-ID"] = tenant_id

        return response

    async def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """
        Extract tenant ID from request.

        Checks (in order):
        1. X-Tenant-ID header
        2. Subdomain (e.g., tenant1.api.example.com)
        3. Query parameter (tenant_id)

        Args:
            request: FastAPI request

        Returns:
            Tenant ID if found, None otherwise
        """
        # Check header
        tenant_id = request.headers.get(self.TENANT_HEADER)
        if tenant_id:
            return tenant_id

        # Check subdomain
        host = request.headers.get("host", "")
        if host:
            parts = host.split(".")
            if len(parts) >= 3:  # subdomain.domain.tld
                tenant_id = parts[0]
                # Validate it's not a common subdomain
                if tenant_id not in ["www", "api", "app", "admin"]:
                    return tenant_id

        # Check query parameter
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id

        return None

    async def _validate_tenant(self, tenant_id: str):
        """
        Validate tenant exists and is active.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Tenant object

        Raises:
            TenantNotFound: If tenant doesn't exist
            TenantSuspended: If tenant is suspended
        """
        async with db_manager.get_session() as session:
            tenant = await self.repository.get_by_tenant_id(session, tenant_id)

            if not tenant:
                raise TenantNotFound(f"Tenant '{tenant_id}' not found")

            if not tenant.is_active:
                raise TenantSuspended(f"Tenant '{tenant_id}' is suspended")

            return tenant

    async def _check_quotas(self, tenant, request: Request) -> bool:
        """
        Check if tenant has exceeded usage quotas.

        Args:
            tenant: Tenant object
            request: FastAPI request

        Returns:
            True if within quotas, False if exceeded
        """
        # Check monthly request quota
        if tenant.max_requests_per_month:
            # Get current month's request count
            current_requests = tenant.current_month_requests or 0

            if current_requests >= tenant.max_requests_per_month:
                logger.warning(
                    "tenant_quota_exceeded",
                    tenant_id=tenant.tenant_id,
                    current_requests=current_requests,
                    max_requests=tenant.max_requests_per_month,
                )
                return False

            # Increment request count (this would typically be done in a background task)
            # For now, we'll just log it
            logger.debug(
                "tenant_request_tracked",
                tenant_id=tenant.tenant_id,
                current_requests=current_requests + 1,
            )

        return True


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware to inject tenant context into logs.

    This should be added after TenancyMiddleware to ensure
    tenant information is available in all logs.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add tenant context to logging.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from downstream handler
        """
        import structlog

        tenant_id = getattr(request.state, "tenant_id", None)

        if tenant_id:
            # Bind tenant_id to logging context
            structlog.contextvars.bind_contextvars(tenant_id=tenant_id)

        try:
            response = await call_next(request)
            return response
        finally:
            # Clear tenant context if it was set
            if tenant_id:
                structlog.contextvars.unbind_contextvars("tenant_id")
