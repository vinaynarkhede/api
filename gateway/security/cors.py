"""CORS (Cross-Origin Resource Sharing) handler."""
from typing import List, Optional
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware

from gateway.config.settings import settings


class CORSConfig:
    """CORS configuration and utilities."""

    def __init__(
        self,
        allowed_origins: Optional[List[str]] = None,
        allowed_methods: Optional[List[str]] = None,
        allowed_headers: Optional[List[str]] = None,
        expose_headers: Optional[List[str]] = None,
        allow_credentials: bool = True,
        max_age: int = 600,
    ):
        """
        Initialize CORS configuration.

        Args:
            allowed_origins: List of allowed origins (["*"] for all)
            allowed_methods: List of allowed HTTP methods
            allowed_headers: List of allowed headers
            expose_headers: List of headers to expose to browser
            allow_credentials: Whether to allow credentials
            max_age: Max age for preflight cache in seconds
        """
        self.allowed_origins = allowed_origins or settings.allowed_origins
        self.allowed_methods = allowed_methods or ["*"]
        self.allowed_headers = allowed_headers or ["*"]
        self.expose_headers = expose_headers or [
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ]
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    def is_origin_allowed(self, origin: str) -> bool:
        """
        Check if origin is allowed.

        Args:
            origin: Origin to check

        Returns:
            True if allowed, False otherwise
        """
        if "*" in self.allowed_origins:
            return True

        return origin in self.allowed_origins

    def get_cors_headers(
        self,
        request_origin: Optional[str],
        request_method: str
    ) -> dict:
        """
        Get CORS headers for response.

        Args:
            request_origin: Origin from request
            request_method: HTTP method

        Returns:
            Dict of CORS headers
        """
        headers = {}

        if not request_origin:
            return headers

        # Check if origin is allowed
        if self.is_origin_allowed(request_origin):
            headers["Access-Control-Allow-Origin"] = request_origin
        elif "*" in self.allowed_origins:
            headers["Access-Control-Allow-Origin"] = "*"

        # Allow credentials
        if self.allow_credentials and request_origin != "*":
            headers["Access-Control-Allow-Credentials"] = "true"

        # Expose headers
        if self.expose_headers:
            headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)

        # For preflight requests
        if request_method == "OPTIONS":
            if self.allowed_methods:
                methods = ", ".join(self.allowed_methods)
                headers["Access-Control-Allow-Methods"] = methods

            if self.allowed_headers:
                allow_headers = ", ".join(self.allowed_headers)
                headers["Access-Control-Allow-Headers"] = allow_headers

            headers["Access-Control-Max-Age"] = str(self.max_age)

        return headers


# Global CORS config instance
cors_config = CORSConfig()
