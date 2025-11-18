"""Prometheus metrics for the API Gateway."""
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    REGISTRY,
)
from typing import Optional

from gateway.config.settings import settings


class Metrics:
    """Prometheus metrics collector."""

    def __init__(self):
        """Initialize metrics."""

        # Request metrics
        self.requests_total = Counter(
            "gateway_requests_total",
            "Total number of requests",
            ["method", "path", "status_code"],
        )

        self.request_duration = Histogram(
            "gateway_request_duration_seconds",
            "Request duration in seconds",
            ["method", "path"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        self.requests_in_progress = Gauge(
            "gateway_requests_in_progress",
            "Number of requests currently being processed",
            ["method"],
        )

        # Proxy metrics
        self.proxy_requests_total = Counter(
            "gateway_proxy_requests_total",
            "Total number of proxied requests",
            ["service", "method", "status_code"],
        )

        self.proxy_duration = Histogram(
            "gateway_proxy_duration_seconds",
            "Proxy request duration in seconds",
            ["service", "method"],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        self.proxy_errors_total = Counter(
            "gateway_proxy_errors_total",
            "Total number of proxy errors",
            ["service", "error_type"],
        )

        # Authentication metrics
        self.auth_requests_total = Counter(
            "gateway_auth_requests_total",
            "Total authentication requests",
            ["auth_type", "result"],
        )

        self.auth_failures_total = Counter(
            "gateway_auth_failures_total",
            "Total authentication failures",
            ["auth_type", "reason"],
        )

        # Rate limiting metrics
        self.rate_limit_hits_total = Counter(
            "gateway_rate_limit_hits_total",
            "Total rate limit hits",
            ["key_type"],
        )

        self.rate_limit_remaining = Gauge(
            "gateway_rate_limit_remaining",
            "Remaining rate limit quota",
            ["key"],
        )

        # Cache metrics
        self.cache_hits_total = Counter(
            "gateway_cache_hits_total",
            "Total cache hits",
            ["operation"],
        )

        self.cache_misses_total = Counter(
            "gateway_cache_misses_total",
            "Total cache misses",
        )

        self.cache_size = Gauge(
            "gateway_cache_size_bytes",
            "Current cache size in bytes",
        )

        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge(
            "gateway_circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=half-open, 2=open)",
            ["service"],
        )

        self.circuit_breaker_failures = Counter(
            "gateway_circuit_breaker_failures_total",
            "Total circuit breaker failures",
            ["service"],
        )

        # System metrics
        self.info = Info(
            "gateway_info",
            "Gateway information",
        )

        # Set gateway info
        self.info.info({
            "version": settings.app_version,
            "environment": settings.environment,
        })

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ):
        """
        Record an HTTP request.

        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration_seconds: Request duration in seconds
        """
        if settings.metrics_enabled:
            self.requests_total.labels(
                method=method,
                path=path,
                status_code=status_code,
            ).inc()

            self.request_duration.labels(
                method=method,
                path=path,
            ).observe(duration_seconds)

    def record_proxy_request(
        self,
        service: str,
        method: str,
        status_code: int,
        duration_seconds: float,
    ):
        """
        Record a proxied request.

        Args:
            service: Service name
            method: HTTP method
            status_code: Response status code
            duration_seconds: Request duration in seconds
        """
        if settings.metrics_enabled:
            self.proxy_requests_total.labels(
                service=service,
                method=method,
                status_code=status_code,
            ).inc()

            self.proxy_duration.labels(
                service=service,
                method=method,
            ).observe(duration_seconds)

    def record_proxy_error(self, service: str, error_type: str):
        """Record a proxy error."""
        if settings.metrics_enabled:
            self.proxy_errors_total.labels(
                service=service,
                error_type=error_type,
            ).inc()

    def record_auth_request(self, auth_type: str, result: str):
        """Record an authentication request."""
        if settings.metrics_enabled:
            self.auth_requests_total.labels(
                auth_type=auth_type,
                result=result,
            ).inc()

    def record_auth_failure(self, auth_type: str, reason: str):
        """Record an authentication failure."""
        if settings.metrics_enabled:
            self.auth_failures_total.labels(
                auth_type=auth_type,
                reason=reason,
            ).inc()

    def record_rate_limit_hit(self, key_type: str):
        """Record a rate limit hit."""
        if settings.metrics_enabled:
            self.rate_limit_hits_total.labels(key_type=key_type).inc()

    def update_rate_limit_remaining(self, key: str, remaining: int):
        """Update rate limit remaining quota."""
        if settings.metrics_enabled:
            self.rate_limit_remaining.labels(key=key).set(remaining)

    def record_cache_hit(self, operation: str = "get"):
        """Record a cache hit."""
        if settings.metrics_enabled:
            self.cache_hits_total.labels(operation=operation).inc()

    def record_cache_miss(self):
        """Record a cache miss."""
        if settings.metrics_enabled:
            self.cache_misses_total.inc()

    def update_circuit_breaker_state(self, service: str, state: int):
        """
        Update circuit breaker state.

        Args:
            service: Service name
            state: State value (0=closed, 1=half-open, 2=open)
        """
        if settings.metrics_enabled:
            self.circuit_breaker_state.labels(service=service).set(state)

    def record_circuit_breaker_failure(self, service: str):
        """Record a circuit breaker failure."""
        if settings.metrics_enabled:
            self.circuit_breaker_failures.labels(service=service).inc()

    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format."""
        return generate_latest(REGISTRY)


# Global metrics instance
metrics = Metrics()
