"""Database connection management with connection pooling."""
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional

from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker

from gateway.config.settings import settings
from gateway.database.models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self):
        """Initialize database manager."""
        self.engine: Optional[create_engine] = None
        self.async_engine: Optional[create_async_engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self.AsyncSessionLocal: Optional[async_sessionmaker] = None
        self._database_url = self._build_database_url()
        self._async_database_url = self._build_async_database_url()

    def _build_database_url(self) -> str:
        """Build synchronous database URL."""
        return (
            f"postgresql://{settings.db_user}:{settings.db_password}"
            f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        )

    def _build_async_database_url(self) -> str:
        """Build asynchronous database URL."""
        return (
            f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}"
            f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        )

    def initialize(self):
        """Initialize database engines and session factories."""
        if self.engine is not None:
            return  # Already initialized

        # Synchronous engine
        self.engine = create_engine(
            self._database_url,
            poolclass=pool.QueuePool,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=settings.debug,
        )

        # Async engine
        self.async_engine = create_async_engine(
            self._async_database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.debug,
        )

        # Session factories
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        self.AsyncSessionLocal = async_sessionmaker(
            self.async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # Set up event listeners
        self._setup_event_listeners()

        logger.info(
            "Database initialized",
            host=settings.db_host,
            database=settings.db_name,
            pool_size=settings.db_pool_size,
        )

    def _setup_event_listeners(self):
        """Set up SQLAlchemy event listeners for logging."""

        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Log when a new connection is created."""
            logger.debug("Database connection established")

        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Log when a connection is checked out from the pool."""
            logger.debug("Database connection checked out from pool")

    def create_tables(self):
        """Create all database tables."""
        if self.engine is None:
            self.initialize()

        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")

    def drop_tables(self):
        """Drop all database tables (USE WITH CAUTION!)."""
        if self.engine is None:
            self.initialize()

        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a synchronous database session.

        Usage:
            with db_manager.get_session() as session:
                users = session.query(User).all()
        """
        if self.SessionLocal is None:
            self.initialize()

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an asynchronous database session.

        Usage:
            async with db_manager.get_async_session() as session:
                result = await session.execute(select(User))
                users = result.scalars().all()
        """
        if self.AsyncSessionLocal is None:
            self.initialize()

        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def check_health(self) -> bool:
        """
        Check database health.

        Returns:
            True if database is healthy, False otherwise
        """
        try:
            async with self.get_async_session() as session:
                # Simple query to check connection
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def get_pool_status(self) -> dict:
        """
        Get connection pool status.

        Returns:
            Dictionary with pool statistics
        """
        if self.engine is None:
            return {}

        pool = self.engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow(),
        }

    def dispose(self):
        """Dispose of all database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Synchronous database engine disposed")

        if self.async_engine:
            # For async engine, we need to use asyncio
            import asyncio

            asyncio.create_task(self.async_engine.dispose())
            logger.info("Asynchronous database engine disposed")


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting database session.

    Usage in FastAPI:
        @app.get("/users")
        async def list_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with db_manager.get_async_session() as session:
        yield session
