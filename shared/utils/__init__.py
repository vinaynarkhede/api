"""Utility functions for the API Gateway."""
import hashlib
import secrets
import re
from typing import Any, Dict, Optional
from datetime import datetime, timedelta


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return hash_api_key(api_key) == hashed_key


def match_route(path: str, pattern: str) -> Optional[Dict[str, str]]:
    """
    Match a URL path against a route pattern.
    Returns dict of path parameters if matched, None otherwise.

    Example:
        match_route("/api/users/123", "/api/users/{user_id}")
        Returns: {"user_id": "123"}
    """
    # Convert route pattern to regex
    regex_pattern = re.sub(r'\{([^}]+)\}', r'(?P<\1>[^/]+)', pattern)
    regex_pattern = f"^{regex_pattern}$"

    match = re.match(regex_pattern, path)
    if match:
        return match.groupdict()
    return None


def get_client_ip(headers: Dict[str, str]) -> str:
    """Extract client IP from headers."""
    # Check common headers for client IP
    ip_headers = [
        "X-Forwarded-For",
        "X-Real-IP",
        "CF-Connecting-IP",  # Cloudflare
        "True-Client-IP",    # Akamai
    ]

    for header in ip_headers:
        if header in headers:
            # X-Forwarded-For can contain multiple IPs
            ip = headers[header].split(',')[0].strip()
            if ip:
                return ip

    return "unknown"


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Remove sensitive headers before proxying."""
    sensitive_headers = [
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
    ]

    return {
        k: v for k, v in headers.items()
        if k.lower() not in sensitive_headers
    }


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def calculate_cache_key(method: str, path: str, query_params: Dict[str, Any]) -> str:
    """Generate a cache key from request details."""
    # Sort query params for consistent keys
    sorted_params = sorted(query_params.items())
    params_str = "&".join(f"{k}={v}" for k, v in sorted_params)
    key_str = f"{method}:{path}:{params_str}"
    return hashlib.md5(key_str.encode()).hexdigest()


def parse_duration(duration_str: str) -> timedelta:
    """
    Parse duration string to timedelta.

    Formats supported:
        - "30s" -> 30 seconds
        - "5m" -> 5 minutes
        - "2h" -> 2 hours
        - "1d" -> 1 day
    """
    pattern = r'^(\d+)([smhd])$'
    match = re.match(pattern, duration_str.lower())

    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")

    value, unit = match.groups()
    value = int(value)

    units = {
        's': 'seconds',
        'm': 'minutes',
        'h': 'hours',
        'd': 'days',
    }

    return timedelta(**{units[unit]: value})


def format_bytes(bytes_count: int) -> str:
    """Format bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


def get_utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.utcnow()
