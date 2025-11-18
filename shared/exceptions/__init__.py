"""Custom exceptions for the API Gateway."""


class GatewayException(Exception):
    """Base exception for all gateway errors."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(GatewayException):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AuthorizationError(GatewayException):
    """Raised when authorization fails."""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)


class RateLimitExceeded(GatewayException):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)


class ServiceUnavailable(GatewayException):
    """Raised when upstream service is unavailable."""
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, status_code=503)


class CircuitBreakerOpen(GatewayException):
    """Raised when circuit breaker is open."""
    def __init__(self, message: str = "Circuit breaker is open"):
        super().__init__(message, status_code=503)


class RouteNotFound(GatewayException):
    """Raised when route is not found."""
    def __init__(self, message: str = "Route not found"):
        super().__init__(message, status_code=404)


class InvalidRequest(GatewayException):
    """Raised when request is invalid."""
    def __init__(self, message: str = "Invalid request"):
        super().__init__(message, status_code=400)


class UpstreamError(GatewayException):
    """Raised when upstream service returns an error."""
    def __init__(self, message: str = "Upstream service error", status_code: int = 502):
        super().__init__(message, status_code=status_code)


class TimeoutError(GatewayException):
    """Raised when request times out."""
    def __init__(self, message: str = "Request timeout"):
        super().__init__(message, status_code=504)


class ConfigurationError(GatewayException):
    """Raised when there's a configuration error."""
    def __init__(self, message: str = "Configuration error"):
        super().__init__(message, status_code=500)
