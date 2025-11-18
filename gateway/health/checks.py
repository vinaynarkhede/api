"""Health check implementations for the API Gateway."""
import asyncio
from datetime import datetime
from typing import Dict, Optional
import httpx

from gateway.database.connection import db_manager
from gateway.cache.redis_cache import redis_cache
from gateway.config.settings import settings
from gateway.resilience.circuit_breaker import circuit_breaker_registry


class HealthChecker:
    """Performs health checks on gateway and dependencies."""

    def __init__(self):
        """Initialize health checker."""
        self.http_client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(timeout=2.0)
        return self.http_client

    async def check_liveness(self) -> Dict:
        """
        Liveness probe - checks if the application is running.

        Returns 200 if app is alive, 503 if dead.
        This should be a simple check that doesn't depend on external services.
        """
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.app_version,
        }

    async def check_readiness(self) -> Dict:
        """
        Readiness probe - checks if the application is ready to serve traffic.

        Returns 200 if ready, 503 if not ready.
        This checks all critical dependencies.
        """
        checks = {}
        overall_status = "ready"

        # Check database
        db_healthy = await self._check_database()
        checks["database"] = db_healthy
        if not db_healthy["healthy"]:
            overall_status = "not_ready"

        # Check Redis
        redis_healthy = await self._check_redis()
        checks["redis"] = redis_healthy
        if not redis_healthy["healthy"]:
            overall_status = "degraded"  # Can operate without Redis

        # Check upstream services
        services_health = await self._check_upstream_services()
        checks["upstream_services"] = services_health

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
        }

    async def check_dependencies(self) -> Dict:
        """
        Detailed health check of all dependencies.

        Returns comprehensive health status including latency and circuit breakers.
        """
        checks = {}

        # Database check
        db_start = datetime.utcnow()
        db_healthy = await self._check_database()
        db_latency = (datetime.utcnow() - db_start).total_seconds() * 1000
        checks["database"] = {
            **db_healthy,
            "latency_ms": round(db_latency, 2),
        }

        # Redis check
        redis_start = datetime.utcnow()
        redis_healthy = await self._check_redis()
        redis_latency = (datetime.utcnow() - redis_start).total_seconds() * 1000
        checks["redis"] = {
            **redis_healthy,
            "latency_ms": round(redis_latency, 2),
        }

        # Upstream services check
        services = await self._check_upstream_services()
        checks["upstream_services"] = services

        # Circuit breakers status
        circuit_breakers = circuit_breaker_registry.get_all_states()
        checks["circuit_breakers"] = circuit_breakers

        # Connection pool status
        pool_status = db_manager.get_pool_status()
        checks["connection_pool"] = pool_status

        # Overall status
        critical_failures = []
        if not checks["database"]["healthy"]:
            critical_failures.append("database")

        if critical_failures:
            overall_status = "unhealthy"
        elif not checks["redis"]["healthy"]:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
            "critical_failures": critical_failures,
        }

    async def _check_database(self) -> Dict:
        """Check database health."""
        try:
            healthy = await db_manager.check_health()
            return {
                "healthy": healthy,
                "message": "Database is healthy" if healthy else "Database connection failed",
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Database error: {str(e)}",
            }

    async def _check_redis(self) -> Dict:
        """Check Redis health."""
        try:
            redis_client = await redis_cache.get_redis()
            await redis_client.ping()
            return {
                "healthy": True,
                "message": "Redis is healthy",
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Redis error: {str(e)}",
            }

    async def _check_upstream_services(self) -> Dict:
        """Check health of upstream services."""
        from gateway.core.router import router

        services = {}
        client = await self.get_client()

        for service_name, service_config in router.get_all_services().items():
            try:
                health_url = f"{service_config.url}{service_config.health_check}"
                response = await client.get(health_url, timeout=2.0)

                if response.status_code == 200:
                    services[service_name] = {
                        "status": "healthy",
                        "latency_ms": response.elapsed.total_seconds() * 1000,
                    }
                else:
                    services[service_name] = {
                        "status": "unhealthy",
                        "status_code": response.status_code,
                    }

            except httpx.TimeoutException:
                services[service_name] = {
                    "status": "timeout",
                    "message": "Health check timed out",
                }
            except httpx.ConnectError:
                services[service_name] = {
                    "status": "unreachable",
                    "message": "Cannot connect to service",
                }
            except Exception as e:
                services[service_name] = {
                    "status": "error",
                    "message": str(e),
                }

        return services

    async def close(self):
        """Close HTTP client."""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()


# Global health checker instance
health_checker = HealthChecker()
