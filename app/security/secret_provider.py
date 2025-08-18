"""
Secret Provider Interface and Implementations
Handles secret management with Key Vault integration for production and local env fallback
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime, timedelta

try:
    from azure.keyvault.secrets import SecretClient
    from azure.identity import DefaultAzureCredential
    from azure.core.exceptions import ServiceRequestError, ResourceNotFoundError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

logger = logging.getLogger(__name__)


class SecretProvider(ABC):
    """Abstract base class for secret providers"""
    
    @abstractmethod
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret value by name"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health and connectivity"""
        pass


class LocalEnvProvider(SecretProvider):
    """Local environment-based secret provider for development"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or "unknown"
        self.name = "LocalEnvProvider"
        logger.info(
            "Initialized LocalEnvProvider for development",
            extra={"correlation_id": self.correlation_id}
        )
    
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from environment variables"""
        try:
            # Convert secret name to env var format (kebab-case to UPPER_SNAKE_CASE)
            env_var_name = secret_name.replace("-", "_").upper()
            
            value = os.getenv(env_var_name)
            
            if value:
                logger.debug(
                    f"Retrieved secret from environment: {secret_name}",
                    extra={
                        "correlation_id": self.correlation_id,
                        "secret_name": secret_name,
                        "env_var": env_var_name
                    }
                )
            else:
                logger.warning(
                    f"Secret not found in environment: {secret_name}",
                    extra={
                        "correlation_id": self.correlation_id,
                        "secret_name": secret_name,
                        "env_var": env_var_name
                    }
                )
            
            return value
            
        except Exception as e:
            logger.error(
                f"Failed to get secret from environment: {secret_name}",
                extra={
                    "correlation_id": self.correlation_id,
                    "secret_name": secret_name,
                    "error": str(e)
                }
            )
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check local environment provider health"""
        return {
            "provider": self.name,
            "status": "healthy",
            "mode": "local_development",
            "timestamp": datetime.utcnow().isoformat(),
            "available_secrets": [
                key for key in os.environ.keys() 
                if any(prefix in key.upper() for prefix in [
                    'COSMOS', 'AZURE', 'OPENAI', 'SEARCH', 'STORAGE'
                ])
            ]
        }


class KeyVaultProvider(SecretProvider):
    """Azure Key Vault-based secret provider for production"""
    
    def __init__(self, vault_url: str, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or "unknown"
        self.vault_url = vault_url
        self.name = "KeyVaultProvider"
        self.client = None
        self._cache = {}
        self._cache_ttl = timedelta(minutes=15)  # Cache secrets for 15 minutes
        
        if not AZURE_AVAILABLE:
            raise ImportError("Azure SDK not available. Install azure-keyvault-secrets and azure-identity")
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Key Vault client with managed identity"""
        try:
            credential = DefaultAzureCredential()
            self.client = SecretClient(
                vault_url=self.vault_url,
                credential=credential
            )
            
            logger.info(
                "Initialized Key Vault client",
                extra={
                    "correlation_id": self.correlation_id,
                    "vault_url": self.vault_url
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize Key Vault client",
                extra={
                    "correlation_id": self.correlation_id,
                    "vault_url": self.vault_url,
                    "error": str(e)
                }
            )
            raise
    
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from Azure Key Vault with caching"""
        try:
            # Check cache first
            cache_key = f"{secret_name}:{self.vault_url}"
            cached_entry = self._cache.get(cache_key)
            
            if cached_entry and datetime.utcnow() < cached_entry["expires_at"]:
                logger.debug(
                    f"Retrieved secret from cache: {secret_name}",
                    extra={
                        "correlation_id": self.correlation_id,
                        "secret_name": secret_name
                    }
                )
                return cached_entry["value"]
            
            # Fetch from Key Vault
            secret = await asyncio.to_thread(
                self.client.get_secret, secret_name
            )
            
            if secret and secret.value:
                # Cache the secret
                self._cache[cache_key] = {
                    "value": secret.value,
                    "expires_at": datetime.utcnow() + self._cache_ttl
                }
                
                logger.debug(
                    f"Retrieved secret from Key Vault: {secret_name}",
                    extra={
                        "correlation_id": self.correlation_id,
                        "secret_name": secret_name,
                        "vault_url": self.vault_url
                    }
                )
                
                return secret.value
            else:
                logger.warning(
                    f"Secret not found in Key Vault: {secret_name}",
                    extra={
                        "correlation_id": self.correlation_id,
                        "secret_name": secret_name,
                        "vault_url": self.vault_url
                    }
                )
                return None
                
        except ResourceNotFoundError:
            logger.warning(
                f"Secret not found in Key Vault: {secret_name}",
                extra={
                    "correlation_id": self.correlation_id,
                    "secret_name": secret_name,
                    "vault_url": self.vault_url
                }
            )
            return None
            
        except Exception as e:
            logger.error(
                f"Failed to get secret from Key Vault: {secret_name}",
                extra={
                    "correlation_id": self.correlation_id,
                    "secret_name": secret_name,
                    "vault_url": self.vault_url,
                    "error": str(e)
                }
            )
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Key Vault connectivity and health"""
        try:
            # Try to list secrets (without values) as a connectivity test
            secret_props = await asyncio.to_thread(
                lambda: list(self.client.list_properties_of_secrets())
            )
            
            return {
                "provider": self.name,
                "status": "healthy",
                "mode": "azure_keyvault",
                "vault_url": self.vault_url,
                "timestamp": datetime.utcnow().isoformat(),
                "secret_count": len(list(secret_props)),
                "cache_size": len(self._cache)
            }
            
        except Exception as e:
            logger.error(
                "Key Vault health check failed",
                extra={
                    "correlation_id": self.correlation_id,
                    "vault_url": self.vault_url,
                    "error": str(e)
                }
            )
            
            return {
                "provider": self.name,
                "status": "unhealthy",
                "mode": "azure_keyvault",
                "vault_url": self.vault_url,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }


class SecretProviderFactory:
    """Factory for creating appropriate secret provider based on environment"""
    
    @staticmethod
    def create_provider(correlation_id: Optional[str] = None) -> SecretProvider:
        """Create secret provider based on environment configuration"""
        
        # Check if Key Vault is configured
        vault_url = os.getenv("AZURE_KEYVAULT_URL")
        use_keyvault = os.getenv("USE_KEYVAULT", "false").lower() == "true"
        
        if vault_url and use_keyvault and AZURE_AVAILABLE:
            try:
                logger.info(
                    "Creating Key Vault provider",
                    extra={
                        "correlation_id": correlation_id,
                        "vault_url": vault_url
                    }
                )
                return KeyVaultProvider(vault_url, correlation_id)
                
            except Exception as e:
                logger.warning(
                    f"Failed to create Key Vault provider, falling back to local env: {str(e)}",
                    extra={
                        "correlation_id": correlation_id,
                        "vault_url": vault_url,
                        "error": str(e)
                    }
                )
                
        # Fall back to local environment provider
        logger.info(
            "Creating local environment provider",
            extra={"correlation_id": correlation_id}
        )
        return LocalEnvProvider(correlation_id)


# Global provider instance
_secret_provider: Optional[SecretProvider] = None


async def get_secret_provider(correlation_id: Optional[str] = None) -> SecretProvider:
    """Get global secret provider instance"""
    global _secret_provider
    
    if _secret_provider is None:
        _secret_provider = SecretProviderFactory.create_provider(correlation_id)
    
    return _secret_provider


async def get_secret(secret_name: str, correlation_id: Optional[str] = None) -> Optional[str]:
    """Convenience function to get a secret"""
    provider = await get_secret_provider(correlation_id)
    return await provider.get_secret(secret_name)


async def health_check_secrets(correlation_id: Optional[str] = None) -> Dict[str, Any]:
    """Health check for secret provider"""
    provider = await get_secret_provider(correlation_id)
    return await provider.health_check()