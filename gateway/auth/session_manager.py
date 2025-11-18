"""Session management for tracking user sessions."""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from gateway.database.repositories import SessionRepository
from gateway.database.models import Session as SessionModel
from gateway.auth.jwt_handler import jwt_handler
from shared.utils import hash_api_key


class SessionManager:
    """Manages user sessions with database storage."""

    async def create_session(
        self,
        db: AsyncSession,
        user_id: int,
        token: str,
        ip_address: str,
        user_agent: str,
        expires_in_minutes: int = 30,
    ) -> SessionModel:
        """
        Create a new session.

        Args:
            db: Database session
            user_id: User ID
            token: JWT token
            ip_address: Client IP address
            user_agent: Client user agent
            expires_in_minutes: Session expiration in minutes

        Returns:
            Created session model
        """
        token_hash = hash_api_key(token)
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)

        session = await SessionRepository.create(
            db,
            user_id=user_id,
            token_hash=token_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )

        return session

    async def validate_session(
        self, db: AsyncSession, token: str
    ) -> Optional[SessionModel]:
        """
        Validate a session token.

        Args:
            db: Database session
            token: JWT token

        Returns:
            Session model if valid, None otherwise
        """
        token_hash = hash_api_key(token)
        session = await SessionRepository.get_by_token_hash(db, token_hash)

        if session:
            # Update last activity
            await SessionRepository.update_activity(db, session)

        return session

    async def revoke_session(self, db: AsyncSession, session_id: int):
        """
        Revoke a specific session.

        Args:
            db: Database session
            session_id: Session ID to revoke
        """
        from gateway.database.models import Session as SessionModel

        result = await db.execute(
            SessionModel.__table__.select().where(SessionModel.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session:
            await SessionRepository.revoke(db, session)

    async def revoke_all_user_sessions(self, db: AsyncSession, user_id: int):
        """
        Revoke all sessions for a user.

        Args:
            db: Database session
            user_id: User ID
        """
        await SessionRepository.revoke_all_for_user(db, user_id)

    async def get_user_sessions(
        self, db: AsyncSession, user_id: int
    ) -> List[SessionModel]:
        """
        Get all active sessions for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of active sessions
        """
        return await SessionRepository.list_by_user(db, user_id)

    async def cleanup_expired_sessions(self, db: AsyncSession) -> int:
        """
        Clean up expired sessions.

        Args:
            db: Database session

        Returns:
            Number of sessions cleaned up
        """
        return await SessionRepository.cleanup_expired(db)


# Global session manager instance
session_manager = SessionManager()
