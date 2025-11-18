"""Main API Gateway application."""
import time
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Request, Depends, Header
from fastapi.responses import JSONResponse, Response, PlainTextResponse

from gateway.config.settings import settings
from gateway.core.router import router
from gateway.core.proxy import http_proxy
from gateway.core.middleware import (
    RequestIDMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    TracingMiddleware,
    SecurityMiddleware,
    CORSMiddleware,
    ErrorHandlerMiddleware,
)
from gateway.auth.jwt_handler import jwt_handler
from gateway.auth.api_key import api_key_handler
from gateway.security.rate_limiter import rate_limiter
from gateway.cache.redis_cache import redis_cache
from gateway.resilience.circuit_breaker import circuit_breaker_registry
from gateway.monitoring.logger import logger
from gateway.monitoring.metrics import metrics
from gateway.database.connection import db_manager
from gateway.health.checks import HealthChecker
from gateway.admin.api import router as admin_router
from shared.models import HealthCheck, Token, TokenData
from shared.exceptions import RouteNotFound, AuthenticationError, RateLimitExceeded
from shared.utils import get_client_ip


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("gateway_starting", version=settings.app_version)

    # Initialize database
    try:
        db_manager.initialize()
        logger.info("database_initialized", pool_size=settings.db_pool_size)
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        # Continue without database for now (could be made fatal)

    # Startup logic here
    yield

    # Shutdown logic
    logger.info("gateway_shutting_down")
    await http_proxy.close()
    await redis_cache.close()
    await rate_limiter.close()
    await api_key_handler.close()

    # Close database connections
    try:
        await db_manager.close()
        logger.info("database_closed")
    except Exception as e:
        logger.error("database_close_failed", error=str(e))


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A modern API Gateway built with Python and FastAPI",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# Add middleware (order matters - bottom to top execution)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(CORSMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(TracingMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

# Include Admin API router
app.include_router(admin_router, tags=["admin"])

# Initialize health checker
health_checker = HealthChecker()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
) -> Optional[TokenData]:
    """
    Get current authenticated user from JWT or API key.

    Args:
        authorization: Authorization header
        x_api_key: API key header

    Returns:
        TokenData if authenticated

    Raises:
        AuthenticationError: If authentication fails
    """
    # Try JWT authentication
    if authorization:
        if not authorization.startswith("Bearer "):
            raise AuthenticationError("Invalid authorization header")

        token = authorization.split("Bearer ")[1]
        return jwt_handler.verify_token(token)

    # Try API key authentication
    if x_api_key:
        api_key = await api_key_handler.validate_api_key(x_api_key)
        return TokenData(
            username=f"api_key_{api_key.user_id}",
            user_id=api_key.user_id,
            scopes=api_key.scopes,
        )

    return None


@app.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    Returns 200 if the application is running.
    """
    result = await health_checker.check_liveness()
    return JSONResponse(content=result, status_code=200)


@app.get("/health/ready")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.
    Returns 200 if the application is ready to serve traffic.
    """
    result = await health_checker.check_readiness()
    status_code = 200 if result["status"] == "ready" else 503
    return JSONResponse(content=result, status_code=status_code)


@app.get("/api/health")
async def health_check():
    """
    Comprehensive health check endpoint with dependency status.
    """
    result = await health_checker.check_dependencies()
    status_code = 200 if result["status"] == "healthy" else 503
    return JSONResponse(content=result, status_code=status_code)


@app.get("/api/metrics")
async def get_metrics() -> Response:
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        content=metrics.get_metrics().decode("utf-8"),
        media_type="text/plain",
    )


@app.get("/api/routes")
async def list_routes():
    """List all configured routes."""
    routes = []

    for route in router.get_all_routes():
        routes.append({
            "path": route.path,
            "methods": route.methods,
            "service": route.service,
            "upstream": route.upstream,
            "auth_required": route.auth_required,
        })

    return {"routes": routes}


@app.get("/api/circuit-breakers")
async def get_circuit_breakers():
    """Get circuit breaker states."""
    return circuit_breaker_registry.get_all_states()


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def gateway_proxy(
    request: Request,
    path: str,
):
    """
    Main gateway proxy endpoint.

    Routes requests to upstream services based on configuration.
    """
    method = request.method
    full_path = f"/{path}" if not path.startswith("/") else path

    # Find matching route
    route_match = router.find_route(full_path, method)

    if not route_match:
        raise RouteNotFound(f"No route found for {method} {full_path}")

    route_config, path_params = route_match

    # Check authentication if required
    if route_config.auth_required:
        user = await get_current_user(
            authorization=request.headers.get("authorization"),
            x_api_key=request.headers.get("x-api-key"),
        )

        if not user:
            raise AuthenticationError("Authentication required")

    # Apply rate limiting
    if route_config.rate_limit and settings.rate_limit_enabled:
        client_ip = get_client_ip(dict(request.headers))
        rate_limit_key = f"{client_ip}:{full_path}"

        max_requests = route_config.rate_limit.get("requests", settings.rate_limit_requests)
        window = route_config.rate_limit.get("window", settings.rate_limit_window_seconds)

        try:
            is_allowed, remaining, retry_after = await rate_limiter.check_rate_limit(
                key=rate_limit_key,
                max_requests=max_requests,
                window_seconds=window,
            )
        except RateLimitExceeded as e:
            metrics.record_rate_limit_hit("ip")
            raise e

    # Check cache (only for GET requests)
    if method == "GET" and route_config.cache and route_config.cache.get("enabled"):
        cache_key = f"{method}:{full_path}:{str(dict(request.query_params))}"
        cached_response = await redis_cache.get(cache_key)

        if cached_response:
            metrics.record_cache_hit("get")
            logger.log_cache_event("hit", cache_key, hit=True)

            return JSONResponse(
                content=cached_response.get("content"),
                status_code=cached_response.get("status_code", 200),
                headers=cached_response.get("headers", {}),
            )

        metrics.record_cache_miss()
        logger.log_cache_event("miss", cache_key, hit=False)

    # Build upstream URL
    upstream_url = router.get_upstream_url(route_config, full_path, path_params)

    # Handle internal routes
    if upstream_url == "internal":
        return JSONResponse({"message": "Internal route"})

    # Get request body
    body = await request.body()

    # Get circuit breaker for this service
    breaker = circuit_breaker_registry.get_or_create(
        name=route_config.service,
        failure_threshold=settings.circuit_breaker_failure_threshold,
        timeout_seconds=settings.circuit_breaker_timeout_seconds,
    )

    # Proxy request with circuit breaker
    start_time = time.time()

    try:
        # Get request ID for propagation to downstream services
        request_id = getattr(request.state, "request_id", None)

        async def proxy_request():
            return await http_proxy.forward_request(
                upstream_url=upstream_url,
                method=method,
                headers=dict(request.headers),
                body=body if body else None,
                query_params=dict(request.query_params),
                request_id=request_id,
            )

        response = await breaker.call(proxy_request)

        # Log proxy request
        duration_ms = (time.time() - start_time) * 1000
        logger.log_proxy_request(
            method=method,
            upstream_url=upstream_url,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        # Record metrics
        metrics.record_proxy_request(
            service=route_config.service,
            method=method,
            status_code=response.status_code,
            duration_seconds=time.time() - start_time,
        )

        # Cache successful GET responses
        if (
            method == "GET"
            and route_config.cache
            and route_config.cache.get("enabled")
            and 200 <= response.status_code < 300
        ):
            cache_data = {
                "content": response.body.decode("utf-8") if response.body else None,
                "status_code": response.status_code,
                "headers": dict(response.headers),
            }

            ttl = route_config.cache.get("ttl", settings.cache_ttl_seconds)
            await redis_cache.set(cache_key, cache_data, ttl=ttl)
            logger.log_cache_event("set", cache_key)

        return response

    except Exception as e:
        metrics.record_proxy_error(route_config.service, type(e).__name__)
        logger.log_error(
            error_type=type(e).__name__,
            error_message=str(e),
            service=route_config.service,
            upstream_url=upstream_url,
        )
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "gateway.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1,
        log_level=settings.log_level.lower(),
    )
