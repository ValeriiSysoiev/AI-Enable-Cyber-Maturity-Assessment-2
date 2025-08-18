"""
Tests for SecretProvider interface and implementations.
"""
import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from security.secret_provider import (
    LocalEnvProvider, 
    SecretProviderFactory,
    get_secret_provider,
    get_secret,
    health_check_secrets
)


class TestLocalEnvProvider:
    """Test LocalEnvProvider implementation"""
    
    @pytest.mark.asyncio
    async def test_get_secret_found(self):
        """Test getting secret that exists in environment"""
        provider = LocalEnvProvider("test-correlation")
        
        with patch.dict(os.environ, {"TEST_SECRET": "test-value"}):
            result = await provider.get_secret("test-secret")
            assert result == "test-value"
    
    @pytest.mark.asyncio
    async def test_get_secret_not_found(self):
        """Test getting secret that doesn't exist"""
        provider = LocalEnvProvider("test-correlation")
        
        with patch.dict(os.environ, {}, clear=True):
            result = await provider.get_secret("nonexistent-secret")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_secret_kebab_to_snake_case(self):
        """Test secret name conversion from kebab-case to UPPER_SNAKE_CASE"""
        provider = LocalEnvProvider("test-correlation")
        
        with patch.dict(os.environ, {"AZURE_OPENAI_API_KEY": "test-api-key"}):
            result = await provider.get_secret("azure-openai-api-key")
            assert result == "test-api-key"
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check returns proper status"""
        provider = LocalEnvProvider("test-correlation")
        
        with patch.dict(os.environ, {
            "COSMOS_ENDPOINT": "test-cosmos",
            "AZURE_OPENAI_API_KEY": "test-key",
            "OTHER_VAR": "not-relevant"
        }):
            health = await provider.health_check()
            
            assert health["provider"] == "LocalEnvProvider"
            assert health["status"] == "healthy"
            assert health["mode"] == "local_development"
            assert "timestamp" in health
            assert "available_secrets" in health
            assert len(health["available_secrets"]) >= 2  # Should find COSMOS and AZURE vars


class TestSecretProviderFactory:
    """Test SecretProviderFactory"""
    
    def test_create_provider_local_env(self):
        """Test factory creates LocalEnvProvider when no Key Vault configured"""
        with patch.dict(os.environ, {}, clear=True):
            provider = SecretProviderFactory.create_provider("test-correlation")
            assert isinstance(provider, LocalEnvProvider)
            assert provider.correlation_id == "test-correlation"
    
    @patch('security.secret_provider.AZURE_AVAILABLE', True)
    def test_create_provider_keyvault_configured(self):
        """Test factory creates KeyVaultProvider when configured"""
        with patch.dict(os.environ, {
            "AZURE_KEYVAULT_URL": "https://test.vault.azure.net/",
            "USE_KEYVAULT": "true"
        }):
            # Mock KeyVaultProvider to avoid actual Azure SDK calls
            with patch('security.secret_provider.KeyVaultProvider') as mock_kv_provider:
                mock_instance = Mock()
                mock_kv_provider.return_value = mock_instance
                
                provider = SecretProviderFactory.create_provider("test-correlation")
                
                mock_kv_provider.assert_called_once_with(
                    "https://test.vault.azure.net/", 
                    "test-correlation"
                )
                assert provider == mock_instance
    
    @patch('security.secret_provider.AZURE_AVAILABLE', True)
    def test_create_provider_keyvault_fallback_on_error(self):
        """Test factory falls back to LocalEnvProvider if KeyVault fails"""
        with patch.dict(os.environ, {
            "AZURE_KEYVAULT_URL": "https://test.vault.azure.net/",
            "USE_KEYVAULT": "true"
        }):
            # Mock KeyVaultProvider to raise exception
            with patch('security.secret_provider.KeyVaultProvider', side_effect=Exception("KeyVault error")):
                provider = SecretProviderFactory.create_provider("test-correlation")
                
                assert isinstance(provider, LocalEnvProvider)
                assert provider.correlation_id == "test-correlation"


class TestGlobalSecretFunctions:
    """Test global secret provider functions"""
    
    @pytest.mark.asyncio
    async def test_get_secret_provider_singleton(self):
        """Test get_secret_provider returns singleton instance"""
        # Clear global state
        import security.secret_provider
        security.secret_provider._secret_provider = None
        
        provider1 = await get_secret_provider("test-correlation")
        provider2 = await get_secret_provider("test-correlation")
        
        assert provider1 is provider2
        assert isinstance(provider1, LocalEnvProvider)
    
    @pytest.mark.asyncio
    async def test_get_secret_convenience_function(self):
        """Test get_secret convenience function"""
        # Clear global state
        import security.secret_provider
        security.secret_provider._secret_provider = None
        
        with patch.dict(os.environ, {"TEST_SECRET": "test-value"}):
            result = await get_secret("test-secret", "test-correlation")
            assert result == "test-value"
    
    @pytest.mark.asyncio
    async def test_health_check_secrets(self):
        """Test health_check_secrets function"""
        # Clear global state
        import security.secret_provider
        security.secret_provider._secret_provider = None
        
        health = await health_check_secrets("test-correlation")
        
        assert isinstance(health, dict)
        assert health["provider"] == "LocalEnvProvider"
        assert health["status"] == "healthy"


class TestKeyVaultProviderMocked:
    """Test KeyVaultProvider with mocked Azure SDK"""
    
    @pytest.mark.asyncio
    @patch('security.secret_provider.AZURE_AVAILABLE', True)
    async def test_keyvault_provider_get_secret_success(self):
        """Test KeyVaultProvider get_secret with successful response"""
        from security.secret_provider import KeyVaultProvider
        
        # Mock Azure SDK components
        mock_secret_client = Mock()
        mock_secret = Mock()
        mock_secret.value = "secret-value"
        
        with patch('security.secret_provider.SecretClient') as mock_secret_client_class, \
             patch('security.secret_provider.DefaultAzureCredential') as mock_credential, \
             patch('asyncio.to_thread', return_value=mock_secret):
            
            mock_secret_client_class.return_value = mock_secret_client
            
            provider = KeyVaultProvider(
                vault_url="https://test.vault.azure.net/",
                correlation_id="test-correlation"
            )
            
            result = await provider.get_secret("test-secret")
            
            assert result == "secret-value"
    
    @pytest.mark.asyncio
    @patch('security.secret_provider.AZURE_AVAILABLE', True)
    async def test_keyvault_provider_get_secret_not_found(self):
        """Test KeyVaultProvider get_secret when secret not found"""
        from security.secret_provider import KeyVaultProvider
        from azure.core.exceptions import ResourceNotFoundError
        
        # Mock Azure SDK components
        mock_secret_client = Mock()
        
        with patch('security.secret_provider.SecretClient') as mock_secret_client_class, \
             patch('security.secret_provider.DefaultAzureCredential') as mock_credential, \
             patch('asyncio.to_thread', side_effect=ResourceNotFoundError("Secret not found")):
            
            mock_secret_client_class.return_value = mock_secret_client
            
            provider = KeyVaultProvider(
                vault_url="https://test.vault.azure.net/",
                correlation_id="test-correlation"
            )
            
            result = await provider.get_secret("nonexistent-secret")
            
            assert result is None
    
    @pytest.mark.asyncio
    @patch('security.secret_provider.AZURE_AVAILABLE', True)
    async def test_keyvault_provider_health_check(self):
        """Test KeyVaultProvider health check"""
        from security.secret_provider import KeyVaultProvider
        
        # Mock Azure SDK components
        mock_secret_client = Mock()
        mock_secret_props = [Mock(), Mock(), Mock()]  # 3 secrets
        
        with patch('security.secret_provider.SecretClient') as mock_secret_client_class, \
             patch('security.secret_provider.DefaultAzureCredential') as mock_credential, \
             patch('asyncio.to_thread', return_value=mock_secret_props):
            
            mock_secret_client_class.return_value = mock_secret_client
            
            provider = KeyVaultProvider(
                vault_url="https://test.vault.azure.net/",
                correlation_id="test-correlation"
            )
            
            health = await provider.health_check()
            
            assert health["provider"] == "KeyVaultProvider"
            assert health["status"] == "healthy"
            assert health["mode"] == "azure_keyvault"
            assert health["vault_url"] == "https://test.vault.azure.net/"
            assert health["secret_count"] == 3
            assert "timestamp" in health