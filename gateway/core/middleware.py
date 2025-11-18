"""Middleware stack for the API Gateway."""
import time
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from gateway.monitoring.logger import logger
from gateway.monitoring.metrics import metrics
from gateway.monitoring.tracer import tracer
from gateway.security.cors import cors_config
from gateway.security.validator import request_validator
from shared.exceptions import GatewayException, RateLimitExceeded
from shared.utils import get_client_ip


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds unique request ID to each request and binds it to logging context."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add request ID to request state and logging context.

        This middleware:
        1. Extracts or generates a unique request ID
        2. Stores it in request.state for access by other components
        3. Binds it to structlog context for automatic inclusion in all logs
        4. Propagates it to response headers for client correlation
        """
        import uuid

        # Extract request ID from header or generate new one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Bind request ID to logging context for this request
        # This ensures all logs during this request will include the request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Clear context after request completes
            structlog.contextvars.clear_contextvars()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs all requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response."""
        start_time = time.time()

        # Extract request info
        method = request.method
        path = str(request.url.path)
        client_ip = get_client_ip(dict(request.headers))

        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception as e:
            status_code = 500
            logger.log_error(
                error_type=type(e).__name__,
                error_message=str(e),
                method=method,
                path=path,
                client_ip=client_ip,
            )
            raise

        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log the request
            logger.log_request(
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                client_ip=client_ip,
                request_id=getattr(request.state, "request_id", None),
            )

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collects metrics for requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect request metrics."""
        method = request.method
        path = str(request.url.path)

        # Track in-progress requests
        metrics.requests_in_progress.labels(method=method).inc()

        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code

            return response

        except Exception as e:
            status_code = 500
            raise

        finally:
            # Record metrics
            duration_seconds = time.time() - start_time

            metrics.record_request(
                method=method,
                path=path,
                status_code=status_code,
                duration_seconds=duration_seconds,
            )

            metrics.requests_in_progress.labels(method=method).dec()


class TracingMiddleware(BaseHTTPMiddleware):
    """Adds distributed tracing to requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add tracing to request."""
        # Extract or create trace ID
        trace_id = tracer.extract_trace_context(dict(request.headers))

        if trace_id:
            request.state.trace_id = trace_id

        # Start span
        span = tracer.start_trace(f"{request.method} {request.url.path}")

        if span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.client_ip", get_client_ip(dict(request.headers)))

            request.state.span = span

        try:
            response = await call_next(request)

            if span:
                span.set_attribute("http.status_code", response.status_code)
                span.end()

            return response

        except Exception as e:
            if span:
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.end()
            raise


class SecurityMiddleware(BaseHTTPMiddleware):
    """Validates and secures requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request security."""
        try:
            # Validate request
            await request_validator.validate_request(request)

            response = await call_next(request)

            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

            return response

        except GatewayException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": type(e).__name__,
                    "message": e.message,
                },
            )


class CORSMiddleware(BaseHTTPMiddleware):
    """Handles CORS for cross-origin requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle CORS."""
        origin = request.headers.get("origin")
        method = request.method

        # Handle preflight
        if method == "OPTIONS":
            response = Response()
            headers = cors_config.get_cors_headers(origin, method)

            for key, value in headers.items():
                response.headers[key] = value

            return response

        # Handle actual request
        response = await call_next(request)

        # Add CORS headers
        headers = cors_config.get_cors_headers(origin, method)
        for key, value in headers.items():
            response.headers[key] = value

        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Handles errors and exceptions."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle errors."""
        try:
            return await call_next(request)

        except RateLimitExceeded as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": "RateLimitExceeded",
                    "message": e.message,
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": "100",
                },
            )

        except GatewayException as e:
            logger.log_error(
                error_type=type(e).__name__,
                error_message=e.message,
                path=str(request.url.path),
            )

            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": type(e).__name__,
                    "message": e.message,
                },
            )

        except Exception as e:
            logger.log_error(
                error_type=type(e).__name__,
                error_message=str(e),
                path=str(request.url.path),
            )

            return JSONResponse(
                status_code=500,
                content={
                    "error": "InternalServerError",
                    "message": "An unexpected error occurred",
                },
            )
