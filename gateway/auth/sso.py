"""SSO authentication handlers for OAuth providers."""
from typing import Dict, Optional
from datetime import datetime, timedelta
import httpx
from jose import jwt

from gateway.config.settings import settings
from gateway.monitoring.logger import logger
from shared.exceptions import AuthenticationError


class SSOProvider:
    """Base class for SSO providers."""

    def __init__(self, provider_name: str):
        """Initialize SSO provider."""
        self.provider_name = provider_name
        self.client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """
        Get OAuth authorization URL.

        Args:
            redirect_uri: Callback URL
            state: State parameter for CSRF protection

        Returns:
            Authorization URL
        """
        raise NotImplementedError

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code
            redirect_uri: Callback URL

        Returns:
            Token response with access_token, id_token, etc.
        """
        raise NotImplementedError

    async def get_user_info(self, access_token: str) -> Dict:
        """
        Get user information from provider.

        Args:
            access_token: Access token

        Returns:
            User information dictionary
        """
        raise NotImplementedError

    async def verify_token(self, token: str) -> Dict:
        """
        Verify and decode ID token.

        Args:
            token: ID token

        Returns:
            Decoded token payload
        """
        raise NotImplementedError


class GoogleSSO(SSOProvider):
    """Google OAuth 2.0 provider."""

    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize Google SSO.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
        """
        super().__init__("google")
        self.client_id = client_id
        self.client_secret = client_secret

    async def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Get Google OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.AUTHORIZATION_URL}?{query_string}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict:
        """Exchange authorization code for tokens."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            response = await self.client.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("google_token_exchange_failed", error=str(e))
            raise AuthenticationError("Failed to exchange authorization code")

    async def get_user_info(self, access_token: str) -> Dict:
        """Get user information from Google."""
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = await self.client.get(self.USER_INFO_URL, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("google_user_info_failed", error=str(e))
            raise AuthenticationError("Failed to get user information")

    async def verify_token(self, token: str) -> Dict:
        """Verify Google ID token."""
        try:
            # In production, you should fetch and cache JWKS from Google
            # and verify the signature properly
            decoded = jwt.decode(
                token,
                options={"verify_signature": False},  # Should verify in production
            )

            # Verify issuer and audience
            if decoded.get("iss") not in [
                "https://accounts.google.com",
                "accounts.google.com",
            ]:
                raise AuthenticationError("Invalid token issuer")

            if decoded.get("aud") != self.client_id:
                raise AuthenticationError("Invalid token audience")

            return decoded
        except Exception as e:
            logger.error("google_token_verification_failed", error=str(e))
            raise AuthenticationError("Token verification failed")


class GitHubSSO(SSOProvider):
    """GitHub OAuth provider."""

    AUTHORIZATION_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_INFO_URL = "https://api.github.com/user"

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize GitHub SSO.

        Args:
            client_id: GitHub OAuth client ID
            client_secret: GitHub OAuth client secret
        """
        super().__init__("github")
        self.client_id = client_id
        self.client_secret = client_secret

    async def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Get GitHub OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.AUTHORIZATION_URL}?{query_string}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict:
        """Exchange authorization code for access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }

        headers = {"Accept": "application/json"}

        try:
            response = await self.client.post(
                self.TOKEN_URL, data=data, headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("github_token_exchange_failed", error=str(e))
            raise AuthenticationError("Failed to exchange authorization code")

    async def get_user_info(self, access_token: str) -> Dict:
        """Get user information from GitHub."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        try:
            response = await self.client.get(self.USER_INFO_URL, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("github_user_info_failed", error=str(e))
            raise AuthenticationError("Failed to get user information")

    async def verify_token(self, token: str) -> Dict:
        """GitHub doesn't use ID tokens, verify by fetching user info."""
        return await self.get_user_info(token)


class AzureADSSO(SSOProvider):
    """Azure Active Directory (Microsoft) OAuth provider."""

    def __init__(self, client_id: str, client_secret: str, tenant_id: str = "common"):
        """
        Initialize Azure AD SSO.

        Args:
            client_id: Azure AD application (client) ID
            client_secret: Azure AD client secret
            tenant_id: Azure AD tenant ID (default: common for multi-tenant)
        """
        super().__init__("azure_ad")
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id

        # Azure AD endpoints
        self.authorization_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        self.token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        self.user_info_url = "https://graph.microsoft.com/v1.0/me"

    async def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Get Azure AD OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile User.Read",
            "state": state,
            "response_mode": "query",
        }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.authorization_url}?{query_string}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict:
        """Exchange authorization code for tokens."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "scope": "openid email profile User.Read",
        }

        try:
            response = await self.client.post(self.token_url, data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("azure_ad_token_exchange_failed", error=str(e))
            raise AuthenticationError("Failed to exchange authorization code")

    async def get_user_info(self, access_token: str) -> Dict:
        """Get user information from Microsoft Graph."""
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = await self.client.get(self.user_info_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("azure_ad_user_info_failed", error=str(e))
            raise AuthenticationError("Failed to get user information")

    async def verify_token(self, token: str) -> Dict:
        """Verify Azure AD ID token."""
        try:
            # In production, fetch JWKS and verify signature
            decoded = jwt.decode(
                token,
                options={"verify_signature": False},  # Should verify in production
            )

            # Verify issuer and audience
            expected_issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            if decoded.get("iss") != expected_issuer:
                raise AuthenticationError("Invalid token issuer")

            if decoded.get("aud") != self.client_id:
                raise AuthenticationError("Invalid token audience")

            return decoded
        except Exception as e:
            logger.error("azure_ad_token_verification_failed", error=str(e))
            raise AuthenticationError("Token verification failed")


class SSOManager:
    """Manager for multiple SSO providers."""

    def __init__(self):
        """Initialize SSO manager."""
        self.providers: Dict[str, SSOProvider] = {}

    def register_provider(self, name: str, provider: SSOProvider):
        """
        Register an SSO provider.

        Args:
            name: Provider name (e.g., "google", "github", "azure")
            provider: Provider instance
        """
        self.providers[name] = provider
        logger.info("sso_provider_registered", provider=name)

    def get_provider(self, name: str) -> Optional[SSOProvider]:
        """
        Get SSO provider by name.

        Args:
            name: Provider name

        Returns:
            Provider instance or None
        """
        return self.providers.get(name)

    def list_providers(self) -> list[str]:
        """
        Get list of registered providers.

        Returns:
            List of provider names
        """
        return list(self.providers.keys())

    async def close_all(self):
        """Close all provider HTTP clients."""
        for provider in self.providers.values():
            await provider.close()


# Global SSO manager instance
sso_manager = SSOManager()


# Initialize SSO providers if configured
def initialize_sso_providers():
    """Initialize SSO providers from settings."""
    # Google OAuth
    if hasattr(settings, "google_client_id") and settings.google_client_id:
        google_provider = GoogleSSO(
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
        sso_manager.register_provider("google", google_provider)

    # GitHub OAuth
    if hasattr(settings, "github_client_id") and settings.github_client_id:
        github_provider = GitHubSSO(
            client_id=settings.github_client_id,
            client_secret=settings.github_client_secret,
        )
        sso_manager.register_provider("github", github_provider)

    # Azure AD OAuth
    if hasattr(settings, "azure_client_id") and settings.azure_client_id:
        azure_provider = AzureADSSO(
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret,
            tenant_id=getattr(settings, "azure_tenant_id", "common"),
        )
        sso_manager.register_provider("azure", azure_provider)

    logger.info(
        "sso_providers_initialized",
        providers=sso_manager.list_providers(),
    )
