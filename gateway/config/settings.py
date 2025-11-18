"""Configuration management for the API Gateway."""
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # Application
    app_name: str = "API Gateway"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    allowed_origins: List[str] = ["*"]

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_url: Optional[str] = None

    @property
    def redis_connection_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_url:
            return self.redis_url
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Circuit Breaker
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60

    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300

    # Monitoring
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    log_level: str = "INFO"

    # Proxy Settings
    proxy_timeout_seconds: int = 30
    proxy_max_retries: int = 3
    proxy_retry_delay_seconds: float = 1.0

    # Health Check
    health_check_enabled: bool = True
    health_check_interval_seconds: int = 30

    # Database (PostgreSQL)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "api_gateway"
    db_user: str = "gateway_user"
    db_password: str = "gateway_password"
    db_pool_size: int = 20
    db_max_overflow: int = 40
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600

    # Vault (Secrets Management)
    vault_enabled: bool = False
    vault_url: str = "http://localhost:8200"
    vault_token: Optional[str] = None
    vault_mount_point: str = "secret"

    # Consul (Service Discovery)
    consul_enabled: bool = False
    consul_host: str = "localhost"
    consul_port: int = 8500
    consul_datacenter: str = "dc1"


# Global settings instance
settings = Settings()
