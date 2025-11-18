"""Structured logging configuration."""
import logging
import sys
from typing import Any, Dict
import structlog
from datetime import datetime

from gateway.config.settings import settings


def configure_logging():
    """Configure structured logging with structlog."""

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.environment == "production"
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class Logger:
    """Structured logger wrapper."""

    def __init__(self, name: str = "api-gateway"):
        """
        Initialize logger.

        Args:
            name: Logger name
        """
        self.logger = structlog.get_logger(name)

    def info(self, event: str, **kwargs):
        """Log info level message."""
        self.logger.info(event, **kwargs)

    def error(self, event: str, **kwargs):
        """Log error level message."""
        self.logger.error(event, **kwargs)

    def warning(self, event: str, **kwargs):
        """Log warning level message."""
        self.logger.warning(event, **kwargs)

    def debug(self, event: str, **kwargs):
        """Log debug level message."""
        self.logger.debug(event, **kwargs)

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        **extra
    ):
        """
        Log HTTP request.

        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            **extra: Additional context
        """
        self.info(
            "http_request",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            **extra
        )

    def log_proxy_request(
        self,
        method: str,
        upstream_url: str,
        status_code: int,
        duration_ms: float,
        **extra
    ):
        """
        Log proxied request to upstream.

        Args:
            method: HTTP method
            upstream_url: Upstream URL
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            **extra: Additional context
        """
        self.info(
            "proxy_request",
            method=method,
            upstream_url=upstream_url,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            **extra
        )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        **extra
    ):
        """
        Log error with context.

        Args:
            error_type: Type of error
            error_message: Error message
            **extra: Additional context
        """
        self.error(
            "error_occurred",
            error_type=error_type,
            error_message=error_message,
            **extra
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        **extra
    ):
        """
        Log security event.

        Args:
            event_type: Type of security event
            severity: Event severity (low, medium, high, critical)
            **extra: Additional context
        """
        self.warning(
            "security_event",
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow().isoformat(),
            **extra
        )

    def log_rate_limit(
        self,
        key: str,
        limit: int,
        remaining: int,
        **extra
    ):
        """
        Log rate limit event.

        Args:
            key: Rate limit key
            limit: Rate limit
            remaining: Remaining requests
            **extra: Additional context
        """
        self.info(
            "rate_limit_check",
            key=key,
            limit=limit,
            remaining=remaining,
            **extra
        )

    def log_cache_event(
        self,
        event: str,
        key: str,
        hit: bool = None,
        **extra
    ):
        """
        Log cache event.

        Args:
            event: Event type (get, set, delete, etc.)
            key: Cache key
            hit: Whether it was a cache hit
            **extra: Additional context
        """
        self.debug(
            "cache_event",
            event=event,
            key=key,
            hit=hit,
            **extra
        )


# Configure logging on module import
configure_logging()

# Global logger instance
logger = Logger()
