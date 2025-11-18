"""OAuth 2.0 authentication handler."""
from typing import Optional
from datetime import datetime, timedelta

from gateway.auth.jwt_handler import jwt_handler
from shared.models import Token
from shared.exceptions import AuthenticationError


class OAuthHandler:
    """
    Handles OAuth 2.0 authentication flows.

    This is a simplified implementation. In production, you would integrate
    with providers like Google, GitHub, Auth0, etc.
    """

    def __init__(self):
        """Initialize OAuth handler."""
        self.jwt = jwt_handler

    async def authenticate_with_password(
        self,
        username: str,
        password: str,
    ) -> Token:
        """
        Authenticate user with username and password (OAuth 2.0 Password Grant).

        Args:
            username: Username
            password: Password

        Returns:
            Token object

        Raises:
            AuthenticationError: If credentials are invalid
        """
        # In production, verify against database
        # This is a mock implementation
        if not username or not password:
            raise AuthenticationError("Invalid credentials")

        # Create token with user information
        token_data = {
            "sub": username,
            "user_id": 1,  # Would come from database
            "scopes": ["read", "write"],
        }

        return self.jwt.create_access_token(token_data)

    async def authenticate_with_client_credentials(
        self,
        client_id: str,
        client_secret: str,
    ) -> Token:
        """
        Authenticate using client credentials (OAuth 2.0 Client Credentials Grant).

        Args:
            client_id: Client ID
            client_secret: Client secret

        Returns:
            Token object

        Raises:
            AuthenticationError: If credentials are invalid
        """
        # In production, verify against database
        if not client_id or not client_secret:
            raise AuthenticationError("Invalid client credentials")

        token_data = {
            "sub": client_id,
            "client_id": client_id,
            "scopes": ["api.read", "api.write"],
        }

        return self.jwt.create_access_token(
            token_data,
            expires_delta=timedelta(hours=1)
        )

    async def refresh_token(self, refresh_token: str) -> Token:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            New Token object

        Raises:
            AuthenticationError: If refresh token is invalid
        """
        # Verify refresh token
        try:
            token_data = self.jwt.verify_token(refresh_token)
        except AuthenticationError:
            raise AuthenticationError("Invalid refresh token")

        # Create new access token
        new_token_data = {
            "sub": token_data.username,
            "user_id": token_data.user_id,
            "scopes": token_data.scopes,
        }

        return self.jwt.create_access_token(new_token_data)


# Global OAuth handler instance
oauth_handler = OAuthHandler()
