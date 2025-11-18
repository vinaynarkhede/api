"""Request validation and security checks."""
import re
from typing import Optional, Dict, Any
from fastapi import Request

from shared.exceptions import InvalidRequest


class RequestValidator:
    """Validates and sanitizes incoming requests."""

    # Common SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bSELECT\b.*\bFROM\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(--|\#|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.",
        r"%2e%2e",
        r"\.\.\\",
    ]

    def __init__(self):
        """Initialize request validator."""
        self.sql_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self.path_patterns = [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]

    async def validate_request(self, request: Request) -> None:
        """
        Validate incoming request for security issues.

        Args:
            request: FastAPI Request object

        Raises:
            InvalidRequest: If request contains malicious content
        """
        # Validate path
        self.validate_path(str(request.url.path))

        # Validate query parameters
        if request.query_params:
            self.validate_query_params(dict(request.query_params))

        # Validate headers
        self.validate_headers(dict(request.headers))

    def validate_path(self, path: str) -> None:
        """
        Validate URL path.

        Args:
            path: URL path

        Raises:
            InvalidRequest: If path contains malicious patterns
        """
        # Check for path traversal
        for pattern in self.path_patterns:
            if pattern.search(path):
                raise InvalidRequest("Path traversal detected")

        # Check for null bytes
        if '\x00' in path:
            raise InvalidRequest("Null byte in path")

    def validate_query_params(self, params: Dict[str, Any]) -> None:
        """
        Validate query parameters.

        Args:
            params: Query parameters dict

        Raises:
            InvalidRequest: If params contain malicious content
        """
        for key, value in params.items():
            value_str = str(value)

            # Check for SQL injection
            for pattern in self.sql_patterns:
                if pattern.search(value_str):
                    raise InvalidRequest(f"Potential SQL injection in parameter: {key}")

            # Check for XSS
            for pattern in self.xss_patterns:
                if pattern.search(value_str):
                    raise InvalidRequest(f"Potential XSS in parameter: {key}")

    def validate_headers(self, headers: Dict[str, str]) -> None:
        """
        Validate request headers.

        Args:
            headers: Request headers dict

        Raises:
            InvalidRequest: If headers contain malicious content
        """
        # Check for header injection
        for key, value in headers.items():
            # Check for CRLF injection
            if '\r' in value or '\n' in value:
                raise InvalidRequest(f"CRLF injection detected in header: {key}")

            # Check for null bytes
            if '\x00' in value:
                raise InvalidRequest(f"Null byte in header: {key}")

    def sanitize_input(self, value: str) -> str:
        """
        Sanitize user input.

        Args:
            value: Input string

        Returns:
            Sanitized string
        """
        # Remove null bytes
        value = value.replace('\x00', '')

        # Remove CRLF
        value = value.replace('\r', '').replace('\n', '')

        # Encode HTML special characters
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&#x27;",
            ">": "&gt;",
            "<": "&lt;",
        }

        for char, escape in html_escape_table.items():
            value = value.replace(char, escape)

        return value

    def validate_content_type(
        self,
        content_type: Optional[str],
        allowed_types: list
    ) -> None:
        """
        Validate content type.

        Args:
            content_type: Content-Type header value
            allowed_types: List of allowed content types

        Raises:
            InvalidRequest: If content type is not allowed
        """
        if not content_type:
            raise InvalidRequest("Content-Type header missing")

        # Extract base content type (ignore charset, etc.)
        base_type = content_type.split(';')[0].strip().lower()

        if base_type not in allowed_types:
            raise InvalidRequest(f"Content-Type not allowed: {base_type}")

    def validate_content_length(
        self,
        content_length: Optional[int],
        max_length: int
    ) -> None:
        """
        Validate content length.

        Args:
            content_length: Content length in bytes
            max_length: Maximum allowed length

        Raises:
            InvalidRequest: If content is too large
        """
        if content_length and content_length > max_length:
            raise InvalidRequest(
                f"Request body too large: {content_length} bytes (max: {max_length})"
            )


# Global validator instance
request_validator = RequestValidator()
