"""Database models for the API Gateway."""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    password_hash = Column(String(255), nullable=False)
    disabled = Column(Boolean, default=False, nullable=False)
    tenant_id = Column(String(100), index=True)  # For multi-tenancy
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        Index("idx_user_tenant_username", "tenant_id", "username"),
        Index("idx_user_tenant_email", "tenant_id", "email"),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class APIKey(Base):
    """API Key model."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(String(100), index=True)
    scopes = Column(JSON, default=list)  # List of permission scopes
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    __table_args__ = (Index("idx_apikey_user_active", "user_id", "is_active"),)

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}')>"


class Session(Base):
    """Session model for tracking active user sessions."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    ip_address = Column(String(45))  # IPv6 max length
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("idx_session_user_active", "user_id", "is_active"),
        Index("idx_session_expires", "expires_at"),
    )

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id})>"


class RouteConfig(Base):
    """Route configuration model."""

    __tablename__ = "route_configs"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String(500), nullable=False, index=True)
    methods = Column(JSON, nullable=False)  # List of HTTP methods
    service = Column(String(100), nullable=False)
    upstream = Column(String(500), nullable=False)
    config_json = Column(JSON, default=dict)  # Full route configuration
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    tenant_id = Column(String(100), index=True)  # Optional tenant-specific routes
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))

    __table_args__ = (
        Index("idx_route_path_active", "path", "is_active"),
        Index("idx_route_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self):
        return f"<RouteConfig(id={self.id}, path='{self.path}')>"


class AuditLog(Base):
    """Audit log for tracking all important actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tenant_id = Column(String(100), index=True)
    event_type = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # create, read, update, delete
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255))
    metadata = Column(JSON, default=dict)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    result = Column(String(50), nullable=False)  # success, failure, denied
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        Index("idx_audit_tenant_timestamp", "tenant_id", "timestamp"),
        Index("idx_audit_event_timestamp", "event_type", "timestamp"),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type='{self.event_type}')>"


class Tenant(Base):
    """Tenant model for multi-tenancy support."""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    subdomain = Column(String(100), unique=True)
    config = Column(JSON, default=dict)  # Tenant-specific configuration
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Subscription info
    plan = Column(String(50), default="free")  # free, pro, team, enterprise
    max_requests_per_month = Column(Integer)
    current_requests_this_month = Column(Integer, default=0)

    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}')>"


class ServiceRegistry(Base):
    """Service registry for tracking discovered services."""

    __tablename__ = "service_registry"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    service_id = Column(String(255), unique=True, nullable=False)
    address = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    health_check_url = Column(String(500))
    metadata = Column(JSON, default=dict)
    is_healthy = Column(Boolean, default=True, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_health_check_at = Column(DateTime)
    deregistered_at = Column(DateTime)

    __table_args__ = (Index("idx_service_name_healthy", "service_name", "is_healthy"),)

    def __repr__(self):
        return f"<ServiceRegistry(id={self.id}, service_name='{self.service_name}')>"
