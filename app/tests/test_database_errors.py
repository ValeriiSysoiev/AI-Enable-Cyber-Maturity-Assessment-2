"""Tests for database error handling module"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from azure.cosmos.exceptions import (
    CosmosResourceNotFoundError,
    CosmosHttpResponseError
)
from fastapi import HTTPException

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database_errors import (
    DatabaseErrorCategory,
    categorize_database_error,
    is_retryable_error,
    calculate_retry_delay,
    translate_database_error,
    retry_database_operation,
    handle_database_errors
)


class TestErrorCategorization:
    """Test error categorization logic"""
    
    def test_categorize_not_found_error(self):
        """Test categorization of not found errors"""
        error = CosmosResourceNotFoundError(status_code=404, message="Not found")
        assert categorize_database_error(error) == DatabaseErrorCategory.NOT_FOUND
    
    def test_categorize_rate_limit_error(self):
        """Test categorization of rate limit errors"""
        error = CosmosHttpResponseError(status_code=429, message="Too many requests")
        assert categorize_database_error(error) == DatabaseErrorCategory.RATE_LIMITED
    
    def test_categorize_timeout_error(self):
        """Test categorization of timeout errors"""
        error = Exception("Connection timeout occurred")
        assert categorize_database_error(error) == DatabaseErrorCategory.TIMEOUT
    
    def test_categorize_permission_error(self):
        """Test categorization of permission errors"""
        error = CosmosHttpResponseError(status_code=403, message="Forbidden")
        assert categorize_database_error(error) == DatabaseErrorCategory.PERMISSION
    
    def test_categorize_unknown_error(self):
        """Test categorization of unknown errors"""
        error = Exception("Some unknown error")
        assert categorize_database_error(error) == DatabaseErrorCategory.UNKNOWN


class TestRetryLogic:
    """Test retry logic and backoff calculations"""
    
    def test_is_retryable_error(self):
        """Test identification of retryable errors"""
        # Retryable errors
        rate_limit = CosmosHttpResponseError(status_code=429, message="Rate limited")
        assert is_retryable_error(rate_limit) is True
        
        timeout = Exception("Connection timeout")
        assert is_retryable_error(timeout) is True
        
        # Non-retryable errors
        not_found = CosmosResourceNotFoundError(status_code=404, message="Not found")
        assert is_retryable_error(not_found) is False
        
        validation = CosmosHttpResponseError(status_code=400, message="Bad request")
        assert is_retryable_error(validation) is False
    
    def test_calculate_retry_delay(self):
        """Test exponential backoff calculation"""
        # First attempt - base delay
        delay0 = calculate_retry_delay(0, base_delay=1.0, max_delay=10.0)
        assert 0.9 <= delay0 <= 1.1  # With jitter
        
        # Second attempt - doubled
        delay1 = calculate_retry_delay(1, base_delay=1.0, max_delay=10.0)
        assert 1.8 <= delay1 <= 2.2  # With jitter
        
        # Max delay cap
        delay_max = calculate_retry_delay(10, base_delay=1.0, max_delay=10.0)
        assert delay_max <= 11.0  # Max + jitter


class TestErrorTranslation:
    """Test database error to HTTP exception translation"""
    
    def test_translate_not_found(self):
        """Test translation of not found errors"""
        error = CosmosResourceNotFoundError(status_code=404, message="Not found")
        http_error = translate_database_error(error, "test operation")
        
        assert isinstance(http_error, HTTPException)
        assert http_error.status_code == 404
        assert http_error.detail == "Resource not found"
    
    def test_translate_rate_limit(self):
        """Test translation of rate limit errors"""
        error = CosmosHttpResponseError(status_code=429, message="Rate limited")
        http_error = translate_database_error(error, "test operation")
        
        assert http_error.status_code == 429
        assert "Too many requests" in http_error.detail
    
    def test_translate_permission_error(self):
        """Test translation of permission errors"""
        error = CosmosHttpResponseError(status_code=403, message="Forbidden")
        http_error = translate_database_error(error, "test operation")
        
        assert http_error.status_code == 403
        assert "Access denied" in http_error.detail
    
    def test_translate_unknown_error(self):
        """Test translation of unknown errors"""
        error = Exception("Some internal error with secrets")
        http_error = translate_database_error(error, "test operation")
        
        assert http_error.status_code == 500
        # Should not expose internal details
        assert "secrets" not in http_error.detail
        assert "unexpected error" in http_error.detail.lower()


@pytest.mark.asyncio
class TestRetryOperation:
    """Test retry_database_operation function"""
    
    async def test_successful_operation(self):
        """Test successful operation without retry"""
        operation = AsyncMock(return_value="success")
        
        result = await retry_database_operation(
            operation,
            context="test operation"
        )
        
        assert result == "success"
        operation.assert_called_once()
    
    async def test_retry_on_transient_error(self):
        """Test retry on transient errors"""
        operation = AsyncMock()
        # Fail twice, then succeed
        operation.side_effect = [
            CosmosHttpResponseError(status_code=503, message="Service unavailable"),
            CosmosHttpResponseError(status_code=503, message="Service unavailable"),
            "success"
        ]
        
        result = await retry_database_operation(
            operation,
            max_retries=2,
            context="test operation"
        )
        
        assert result == "success"
        assert operation.call_count == 3
    
    async def test_fail_after_max_retries(self):
        """Test failure after max retries"""
        operation = AsyncMock()
        operation.side_effect = CosmosHttpResponseError(
            status_code=503, 
            message="Service unavailable"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await retry_database_operation(
                operation,
                max_retries=2,
                context="test operation"
            )
        
        assert exc_info.value.status_code == 503
        assert operation.call_count == 3  # Initial + 2 retries
    
    async def test_no_retry_on_non_retryable(self):
        """Test no retry on non-retryable errors"""
        operation = AsyncMock()
        operation.side_effect = CosmosHttpResponseError(
            status_code=400,
            message="Bad request"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await retry_database_operation(
                operation,
                max_retries=3,
                context="test operation"
            )
        
        assert exc_info.value.status_code == 400
        operation.assert_called_once()  # No retries


@pytest.mark.asyncio
class TestErrorHandlerDecorator:
    """Test handle_database_errors decorator"""
    
    async def test_decorator_passes_through_success(self):
        """Test decorator passes through successful operations"""
        @handle_database_errors("test operation")
        async def successful_operation():
            return "success"
        
        result = await successful_operation()
        assert result == "success"
    
    async def test_decorator_translates_errors(self):
        """Test decorator translates database errors"""
        @handle_database_errors("test operation")
        async def failing_operation():
            raise CosmosResourceNotFoundError(status_code=404, message="Not found")
        
        with pytest.raises(HTTPException) as exc_info:
            await failing_operation()
        
        assert exc_info.value.status_code == 404
    
    async def test_decorator_preserves_http_exceptions(self):
        """Test decorator preserves existing HTTP exceptions"""
        @handle_database_errors("test operation")
        async def http_error_operation():
            raise HTTPException(status_code=418, detail="I'm a teapot")
        
        with pytest.raises(HTTPException) as exc_info:
            await http_error_operation()
        
        assert exc_info.value.status_code == 418
        assert exc_info.value.detail == "I'm a teapot"