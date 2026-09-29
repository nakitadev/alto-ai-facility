"""
LLM Provider package with factory function for OpenRouter.
"""

from typing import Optional
from backend.llm.provider import BaseLLMProvider
from backend.llm.openrouter import OpenRouterLLMProvider
from backend.config import FREE_OPENROUTER_MODELS

def get_llm_provider(
    provider_type: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> OpenRouterLLMProvider:
    """
    Factory creating the persistent OpenRouter LLM provider instance.
    """
    return OpenRouterLLMProvider(model_name=model_name, api_key=api_key)

__all__ = [
    "BaseLLMProvider",
    "OpenRouterLLMProvider",
    "FREE_OPENROUTER_MODELS",
    "get_llm_provider"
]
