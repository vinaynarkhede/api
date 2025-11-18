"""Secrets management integration with HashiCorp Vault."""
import os
from typing import Dict, Optional
import hvac
from gateway.config.settings import settings


class SecretsManager:
    """Manages secrets from Vault or environment variables."""

    def __init__(self):
        """Initialize secrets manager."""
        self.vault_client: Optional[hvac.Client] = None
        self._secrets_cache: Dict[str, str] = {}

        if settings.vault_enabled:
            self._init_vault()

    def _init_vault(self):
        """Initialize Vault client."""
        try:
            self.vault_client = hvac.Client(
                url=settings.vault_url,
                token=settings.vault_token,
            )

            if not self.vault_client.is_authenticated():
                raise Exception("Vault authentication failed")

        except Exception as e:
            print(f"Warning: Could not connect to Vault: {e}")
            print("Falling back to environment variables")
            self.vault_client = None

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get secret from Vault or environment.

        Args:
            key: Secret key
            default: Default value if not found

        Returns:
            Secret value or default
        """
        # Check cache first
        if key in self._secrets_cache:
            return self._secrets_cache[key]

        # Try Vault if enabled
        if self.vault_client:
            try:
                secret_path = f"{settings.vault_mount_point}/data/gateway"
                response = self.vault_client.secrets.kv.v2.read_secret_version(
                    path=secret_path
                )
                value = response["data"]["data"].get(key)
                if value:
                    self._secrets_cache[key] = value
                    return value
            except Exception:
                pass  # Fall through to environment variable

        # Fall back to environment variable
        value = os.getenv(key.upper(), default)
        if value:
            self._secrets_cache[key] = value

        return value

    def get_database_url(self) -> str:
        """Get database URL with credentials from secrets."""
        user = self.get_secret("db_user", settings.db_user)
        password = self.get_secret("db_password", settings.db_password)
        host = self.get_secret("db_host", settings.db_host)
        port = self.get_secret("db_port", str(settings.db_port))
        name = self.get_secret("db_name", settings.db_name)

        return f"postgresql://{user}:{password}@{host}:{port}/{name}"

    def get_jwt_secret(self) -> str:
        """Get JWT secret key."""
        secret = self.get_secret("jwt_secret_key", settings.secret_key)

        # Validate secret strength
        if secret == "your-secret-key-change-in-production":
            raise ValueError(
                "CRITICAL: JWT secret key must be changed in production! "
                "Set JWT_SECRET_KEY environment variable or configure in Vault."
            )

        if len(secret) < 32:
            raise ValueError(
                "CRITICAL: JWT secret key must be at least 32 characters long!"
            )

        return secret

    def get_redis_password(self) -> Optional[str]:
        """Get Redis password."""
        return self.get_secret("redis_password", settings.redis_password)

    def rotate_secret(self, key: str, new_value: str) -> bool:
        """
        Rotate a secret in Vault.

        Args:
            key: Secret key
            new_value: New secret value

        Returns:
            True if successful
        """
        if not self.vault_client:
            return False

        try:
            secret_path = f"{settings.vault_mount_point}/data/gateway"
            # Read existing secrets
            response = self.vault_client.secrets.kv.v2.read_secret_version(
                path=secret_path
            )
            secrets = response["data"]["data"]

            # Update with new value
            secrets[key] = new_value

            # Write back
            self.vault_client.secrets.kv.v2.create_or_update_secret(
                path=secret_path,
                secret=secrets,
            )

            # Update cache
            self._secrets_cache[key] = new_value

            return True

        except Exception as e:
            print(f"Failed to rotate secret: {e}")
            return False


# Global secrets manager
secrets_manager = SecretsManager()
