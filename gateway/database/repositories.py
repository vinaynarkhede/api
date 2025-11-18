"""Repository pattern for database operations."""
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from gateway.database.models import (
    User,
    APIKey,
    Session as SessionModel,
    RouteConfig,
    AuditLog,
    Tenant,
    ServiceRegistry,
)
from shared.utils import hash_api_key


class UserRepository:
    """Repository for User operations."""

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> User:
        """Create a new user."""
        user = User(**kwargs)
        session.add(user)
        await session.flush()
        return user

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(session: AsyncSession, username: str) -> Optional[User]:
        """Get user by username."""
        result = await session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(session: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_tenant(
        session: AsyncSession, tenant_id: str, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """List users by tenant."""
        result = await session.execute(
            select(User)
            .where(User.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update(session: AsyncSession, user: User) -> User:
        """Update user."""
        user.updated_at = datetime.utcnow()
        await session.flush()
        return user

    @staticmethod
    async def delete(session: AsyncSession, user: User):
        """Delete user."""
        await session.delete(user)
        await session.flush()


class APIKeyRepository:
    """Repository for APIKey operations."""

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> APIKey:
        """Create a new API key."""
        api_key = APIKey(**kwargs)
        session.add(api_key)
        await session.flush()
        return api_key

    @staticmethod
    async def get_by_hash(session: AsyncSession, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash."""
        result = await session.execute(
            select(APIKey).where(
                and_(APIKey.key_hash == key_hash, APIKey.is_active == True)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user(
        session: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[APIKey]:
        """List API keys for a user."""
        result = await session.execute(
            select(APIKey)
            .where(APIKey.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def revoke(session: AsyncSession, api_key: APIKey):
        """Revoke an API key."""
        api_key.is_active = False
        await session.flush()

    @staticmethod
    async def update_last_used(session: AsyncSession, api_key: APIKey):
        """Update last used timestamp."""
        api_key.last_used_at = datetime.utcnow()
        await session.flush()


class SessionRepository:
    """Repository for Session operations."""

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> SessionModel:
        """Create a new session."""
        session_model = SessionModel(**kwargs)
        session.add(session_model)
        await session.flush()
        return session_model

    @staticmethod
    async def get_by_token_hash(
        db_session: AsyncSession, token_hash: str
    ) -> Optional[SessionModel]:
        """Get session by token hash."""
        result = await db_session.execute(
            select(SessionModel).where(
                and_(
                    SessionModel.token_hash == token_hash,
                    SessionModel.is_active == True,
                    SessionModel.expires_at > datetime.utcnow(),
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user(
        db_session: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[SessionModel]:
        """List sessions for a user."""
        result = await db_session.execute(
            select(SessionModel)
            .where(
                and_(SessionModel.user_id == user_id, SessionModel.is_active == True)
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def revoke(db_session: AsyncSession, session_model: SessionModel):
        """Revoke a session."""
        session_model.is_active = False
        await db_session.flush()

    @staticmethod
    async def revoke_all_for_user(db_session: AsyncSession, user_id: int):
        """Revoke all sessions for a user."""
        result = await db_session.execute(
            select(SessionModel).where(
                and_(SessionModel.user_id == user_id, SessionModel.is_active == True)
            )
        )
        sessions = result.scalars().all()
        for session in sessions:
            session.is_active = False
        await db_session.flush()

    @staticmethod
    async def cleanup_expired(db_session: AsyncSession):
        """Clean up expired sessions."""
        result = await db_session.execute(
            select(SessionModel).where(
                and_(
                    SessionModel.is_active == True,
                    SessionModel.expires_at < datetime.utcnow(),
                )
            )
        )
        sessions = result.scalars().all()
        for session in sessions:
            session.is_active = False
        await db_session.flush()
        return len(sessions)

    @staticmethod
    async def update_activity(db_session: AsyncSession, session_model: SessionModel):
        """Update last activity timestamp."""
        session_model.last_activity_at = datetime.utcnow()
        await db_session.flush()


class RouteConfigRepository:
    """Repository for RouteConfig operations."""

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> RouteConfig:
        """Create a new route configuration."""
        route = RouteConfig(**kwargs)
        session.add(route)
        await session.flush()
        return route

    @staticmethod
    async def get_by_id(session: AsyncSession, route_id: int) -> Optional[RouteConfig]:
        """Get route by ID."""
        result = await session.execute(
            select(RouteConfig).where(RouteConfig.id == route_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_active(
        session: AsyncSession, tenant_id: Optional[str] = None
    ) -> List[RouteConfig]:
        """List active routes, optionally filtered by tenant."""
        query = select(RouteConfig).where(RouteConfig.is_active == True)

        if tenant_id:
            query = query.where(
                (RouteConfig.tenant_id == tenant_id)
                | (RouteConfig.tenant_id == None)
            )

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update(session: AsyncSession, route: RouteConfig) -> RouteConfig:
        """Update route configuration."""
        route.updated_at = datetime.utcnow()
        route.version += 1
        await session.flush()
        return route

    @staticmethod
    async def deactivate(session: AsyncSession, route: RouteConfig):
        """Deactivate a route."""
        route.is_active = False
        route.updated_at = datetime.utcnow()
        await session.flush()


class AuditLogRepository:
    """Repository for AuditLog operations."""

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> AuditLog:
        """Create a new audit log entry."""
        audit_log = AuditLog(**kwargs)
        session.add(audit_log)
        await session.flush()
        return audit_log

    @staticmethod
    async def list_by_user(
        session: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AuditLog]:
        """List audit logs for a user."""
        query = select(AuditLog).where(AuditLog.user_id == user_id)

        if start_date:
            query = query.where(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLog.timestamp <= end_date)

        query = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def list_by_tenant(
        session: AsyncSession,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        event_type: Optional[str] = None,
    ) -> List[AuditLog]:
        """List audit logs for a tenant."""
        query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

        if event_type:
            query = query.where(AuditLog.event_type == event_type)

        query = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())


class TenantRepository:
    """Repository for Tenant operations."""

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> Tenant:
        """Create a new tenant."""
        tenant = Tenant(**kwargs)
        session.add(tenant)
        await session.flush()
        return tenant

    @staticmethod
    async def get_by_id(session: AsyncSession, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_subdomain(
        session: AsyncSession, subdomain: str
    ) -> Optional[Tenant]:
        """Get tenant by subdomain."""
        result = await session.execute(
            select(Tenant).where(Tenant.subdomain == subdomain)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(
        session: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Tenant]:
        """List all tenants."""
        result = await session.execute(select(Tenant).offset(skip).limit(limit))
        return list(result.scalars().all())

    @staticmethod
    async def update(session: AsyncSession, tenant: Tenant) -> Tenant:
        """Update tenant."""
        tenant.updated_at = datetime.utcnow()
        await session.flush()
        return tenant

    @staticmethod
    async def increment_usage(session: AsyncSession, tenant: Tenant, count: int = 1):
        """Increment request count for tenant."""
        tenant.current_requests_this_month += count
        await session.flush()


class ServiceRegistryRepository:
    """Repository for ServiceRegistry operations."""

    @staticmethod
    async def register(session: AsyncSession, **kwargs) -> ServiceRegistry:
        """Register a new service."""
        service = ServiceRegistry(**kwargs)
        session.add(service)
        await session.flush()
        return service

    @staticmethod
    async def get_by_service_id(
        session: AsyncSession, service_id: str
    ) -> Optional[ServiceRegistry]:
        """Get service by service ID."""
        result = await session.execute(
            select(ServiceRegistry).where(ServiceRegistry.service_id == service_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_healthy_by_name(
        session: AsyncSession, service_name: str
    ) -> List[ServiceRegistry]:
        """List healthy instances of a service."""
        result = await session.execute(
            select(ServiceRegistry).where(
                and_(
                    ServiceRegistry.service_name == service_name,
                    ServiceRegistry.is_healthy == True,
                    ServiceRegistry.deregistered_at == None,
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_health(
        session: AsyncSession, service: ServiceRegistry, is_healthy: bool
    ):
        """Update service health status."""
        service.is_healthy = is_healthy
        service.last_health_check_at = datetime.utcnow()
        await session.flush()

    @staticmethod
    async def deregister(session: AsyncSession, service: ServiceRegistry):
        """Deregister a service."""
        service.deregistered_at = datetime.utcnow()
        await session.flush()
