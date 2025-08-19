from __future__ import annotations
import os
import logging
import time
import asyncio
from typing import List, Dict, Any, Optional

from security.secret_provider import get_secret

USE_MOCK = None  # Will be determined asynchronously

# Set up logger
logger = logging.getLogger(__name__)

# Global client instance - will be initialized asynchronously
_client: Optional['AzureOpenAI'] = None
_model: Optional[str] = None
_client_initialized = False

async def _initialize_client(correlation_id: Optional[str] = None) -> bool:
    """Initialize OpenAI client with secret provider"""
    global _client, _model, USE_MOCK, _client_initialized
    
    if _client_initialized:
        return not USE_MOCK
    
    try:
        # Get secrets using secret provider
        endpoint = await get_secret("azure-openai-endpoint", correlation_id)
        api_key = await get_secret("azure-openai-api-key", correlation_id)
        deployment = await get_secret("azure-openai-deployment", correlation_id)
        
        # Fallback to environment variables for local development
        if not endpoint:
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not api_key:
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not deployment:
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        USE_MOCK = not (endpoint and api_key and deployment)
        
        if not USE_MOCK:
            from openai import AzureOpenAI, APIError, APIConnectionError, RateLimitError
            _client = AzureOpenAI(
                api_key=api_key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                azure_endpoint=endpoint,
            )
            _model = deployment
            
            logger.info(
                "Initialized OpenAI client with secret provider",
                extra={"correlation_id": correlation_id, "endpoint": endpoint}
            )
        else:
            logger.info(
                "Using mock LLM client - secrets not available",
                extra={"correlation_id": correlation_id}
            )
        
        _client_initialized = True
        return not USE_MOCK
        
    except (ImportError, ModuleNotFoundError) as e:
        logger.error(f"Failed to import OpenAI client: {e}", exc_info=True)
        USE_MOCK = True
        _client_initialized = True
        return False
    except RuntimeError as e:
        logger.error(f"Runtime error initializing OpenAI client: {e}", exc_info=True)
        USE_MOCK = True
        _client_initialized = True
        return False
    except Exception as e:
        logger.exception(f"Unexpected error initializing OpenAI client: {e}")
        USE_MOCK = True
        _client_initialized = True
        return False

class LLMError(Exception):
    """Custom exception for LLM-related errors"""
    pass

class LLMClient:
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id
    
    async def generate(self, system: str, user: str) -> str:
        # Ensure client is initialized
        await _initialize_client(self.correlation_id)
        if USE_MOCK or not _client:
            # Simple deterministic stub for demos
            return (
                "Findings:\n"
                "- [high] Identity: MFA not enforced for admins.\n"
                "- [medium] Data: No DLP policies for M365.\n"
                "- [low] SecOps: Runbooks missing for P1 incidents.\n"
                "\nRecommendations:\n"
                "1) Enforce Conditional Access + MFA for privileged roles (P1, M effort, 4 weeks)\n"
                "2) Deploy baseline DLP policies for M365 (P2, M effort, 6 weeks)\n"
                "3) Author incident runbooks and test (P3, S effort, 3 weeks)\n"
            )
        else:
            # Implement retry logic with exponential backoff
            max_retries = 3
            base_delay = 1.0  # seconds
            
            for attempt in range(max_retries):
                try:
                    resp = _client.chat.completions.create(
                        model=_model,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        temperature=0.2,
                    )
                    
                    # Validate response structure
                    if not resp:
                        logger.error("OpenAI API returned empty response")
                        raise LLMError("Empty response from OpenAI API")
                    
                    if not hasattr(resp, 'choices') or not resp.choices:
                        logger.error(f"OpenAI API response missing choices: {resp}")
                        raise LLMError("Invalid response structure: missing choices")
                    
                    if len(resp.choices) == 0:
                        logger.error(f"OpenAI API returned empty choices list: {resp}")
                        raise LLMError("Invalid response structure: empty choices list")
                    
                    first_choice = resp.choices[0]
                    if not hasattr(first_choice, 'message') or not first_choice.message:
                        logger.error(f"OpenAI API choice missing message: {first_choice}")
                        raise LLMError("Invalid response structure: missing message")
                    
                    if not hasattr(first_choice.message, 'content') or first_choice.message.content is None:
                        logger.error(f"OpenAI API message missing content: {first_choice.message}")
                        raise LLMError("Invalid response structure: missing message content")
                    
                    content = first_choice.message.content
                    if not content or not content.strip():
                        logger.warning("OpenAI API returned empty content")
                        return "No content generated by the model."
                    
                    return content
                    
                except RateLimitError as e:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # exponential backoff
                        logger.warning(f"Rate limit hit, retrying in {delay}s. Attempt {attempt + 1}/{max_retries}: {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"Rate limit error after {max_retries} attempts: {e}")
                        raise LLMError(f"Rate limit exceeded after {max_retries} retries") from e
                        
                except APIConnectionError as e:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Connection error, retrying in {delay}s. Attempt {attempt + 1}/{max_retries}: {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"Connection error after {max_retries} attempts: {e}")
                        raise LLMError(f"Connection failed after {max_retries} retries") from e
                        
                except APIError as e:
                    logger.error(f"OpenAI API error: {e}")
                    raise LLMError(f"OpenAI API error: {str(e)}") from e
                    
                except Exception as e:
                    logger.exception(f"Unexpected error calling OpenAI API: {e}")
                    raise LLMError(f"Unexpected error: {str(e)}") from e
