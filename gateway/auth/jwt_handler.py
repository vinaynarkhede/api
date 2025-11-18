"""JWT token handling for authentication."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from gateway.config.settings import settings
from shared.models import TokenData, Token
from shared.exceptions import AuthenticationError


class JWTHandler:
    """Handles JWT token creation and validation."""

    def __init__(self):
        """Initialize JWT handler."""
        self.secret_key = settings.secret_key
        self.algorithm = settings.jwt_algorithm
        self.expiration_minutes = settings.jwt_expiration_minutes
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> Token:
        """
        Create a new JWT access token.

        Args:
            data: Data to encode in the token
            expires_delta: Optional custom expiration time

        Returns:
            Token object with access_token and metadata
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.expiration_minutes)

        to_encode.update({"exp": expire, "iat": datetime.utcnow()})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return Token(
            access_token=encoded_jwt,
            token_type="bearer",
            expires_in=int(expires_delta.total_seconds() if expires_delta else self.expiration_minutes * 60)
        )

    def verify_token(self, token: str) -> TokenData:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenData with decoded information

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            username: Optional[str] = payload.get("sub")
            user_id: Optional[int] = payload.get("user_id")
            scopes: list = payload.get("scopes", [])

            if username is None:
                raise AuthenticationError("Invalid token payload")

            return TokenData(
                username=username,
                user_id=user_id,
                scopes=scopes
            )

        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)


# Global JWT handler instance
jwt_handler = JWTHandler()
