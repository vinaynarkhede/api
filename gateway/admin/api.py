"""Admin API endpoints for gateway management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from gateway.database.connection import get_db
from gateway.database.repositories import RouteConfigRepository, APIKeyRepository, TenantRepository
from gateway.database.models import RouteConfig, APIKey, Tenant
from gateway.cache.redis_cache import redis_cache
from gateway.resilience.circuit_breaker import circuit_breaker_registry
from pydantic import BaseModel


router = APIRouter(prefix="/admin", tags=["admin"])


# Request/Response Models
class RouteConfigCreate(BaseModel):
    path: str
    methods: List[str]
    service: str
    upstream: str
    config_json: dict = {}
    tenant_id: str = None


class RouteConfigUpdate(BaseModel):
    path: str = None
    methods: List[str] = None
    upstream: str = None
    config_json: dict = None
    is_active: bool = None


@router.get("/config")
async def get_configuration():
    """Get current gateway configuration."""
    from gateway.config.settings import settings
    from gateway.core.router import router as gateway_router

    return {
        "version": settings.app_version,
        "environment": settings.environment,
        "routes_count": len(gateway_router.get_all_routes()),
        "services_count": len(gateway_router.get_all_services()),
    }


@router.post("/config/reload")
async def reload_configuration():
    """Reload configuration from database."""
    from gateway.core.router import router as gateway_router

    try:
        gateway_router.reload_configuration()
        return {"message": "Configuration reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routes")
async def list_routes(db: AsyncSession = Depends(get_db)):
    """List all routes."""
    routes = await RouteConfigRepository.list_active(db)
    return {"routes": [{"id": r.id, "path": r.path, "methods": r.methods, "service": r.service} for r in routes]}


@router.post("/routes")
async def create_route(route_data: RouteConfigCreate, db: AsyncSession = Depends(get_db)):
    """Create a new route."""
    route = await RouteConfigRepository.create(
        db,
        path=route_data.path,
        methods=route_data.methods,
        service=route_data.service,
        upstream=route_data.upstream,
        config_json=route_data.config_json,
        tenant_id=route_data.tenant_id,
    )
    await db.commit()
    return {"message": "Route created", "route_id": route.id}


@router.put("/routes/{route_id}")
async def update_route(route_id: int, route_data: RouteConfigUpdate, db: AsyncSession = Depends(get_db)):
    """Update a route."""
    route = await RouteConfigRepository.get_by_id(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    if route_data.path:
        route.path = route_data.path
    if route_data.methods:
        route.methods = route_data.methods
    if route_data.upstream:
        route.upstream = route_data.upstream
    if route_data.config_json is not None:
        route.config_json = route_data.config_json
    if route_data.is_active is not None:
        route.is_active = route_data.is_active

    await RouteConfigRepository.update(db, route)
    await db.commit()

    return {"message": "Route updated"}


@router.delete("/routes/{route_id}")
async def delete_route(route_id: int, db: AsyncSession = Depends(get_db)):
    """Delete (deactivate) a route."""
    route = await RouteConfigRepository.get_by_id(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    await RouteConfigRepository.deactivate(db, route)
    await db.commit()

    return {"message": "Route deactivated"}


@router.get("/circuit-breakers")
async def get_circuit_breakers():
    """Get all circuit breaker states."""
    return circuit_breaker_registry.get_all_states()


@router.post("/circuit-breakers/{service}/reset")
async def reset_circuit_breaker(service: str):
    """Reset a circuit breaker."""
    breaker = circuit_breaker_registry.get(service)
    if not breaker:
        raise HTTPException(status_code=404, detail="Circuit breaker not found")

    breaker.reset()
    return {"message": f"Circuit breaker for {service} reset"}


@router.post("/cache/clear")
async def clear_cache(pattern: str = "*"):
    """Clear cache by pattern."""
    count = await redis_cache.clear_pattern(pattern)
    return {"message": f"Cleared {count} cache entries"}


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    stats = await redis_cache.get_stats()
    return stats


@router.get("/instances")
async def list_instances():
    """List all gateway instances."""
    # Would integrate with service discovery in production
    return {"instances": [{"id": "gateway-1", "status": "healthy"}]}
