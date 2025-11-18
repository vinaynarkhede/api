"""Shared data models for the API Gateway."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RouteConfig(BaseModel):
    """Route configuration model."""
    path: str
    methods: List[str]
    service: str
    upstream: str
    auth_required: bool = True
    rate_limit: Optional[Dict[str, int]] = None
    cache: Optional[Dict[str, Any]] = None
    strip_path: bool = False
    timeout: Optional[int] = None


class ServiceConfig(BaseModel):
    """Service configuration model."""
    url: str
    health_check: str = "/health"
    timeout: int = 30
    instances: List[str] = Field(default_factory=list)


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""
    requests: int = 100
    window: int = 60  # seconds


class CacheConfig(BaseModel):
    """Cache configuration."""
    enabled: bool = True
    ttl: int = 300  # seconds


class User(BaseModel):
    """User model."""
    id: Optional[int] = None
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: bool = False
    created_at: Optional[datetime] = None


class Token(BaseModel):
    """JWT Token model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token data extracted from JWT."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    scopes: List[str] = Field(default_factory=list)


class APIKey(BaseModel):
    """API Key model."""
    key: str
    name: str
    user_id: int
    scopes: List[str] = Field(default_factory=list)
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True


class HealthCheck(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: Optional[str] = None
