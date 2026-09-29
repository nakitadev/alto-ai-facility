"""
OpenRouter LLM Provider implementation.
"""

import asyncio
from typing import Optional, Dict, List, Any
from pydantic_ai.models import Model
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from backend.config import OPENROUTER_MODEL, OPENROUTER_API_KEY, FREE_OPENROUTER_MODELS
from backend.llm.provider import BaseLLMProvider

class OpenRouterLLMProvider(BaseLLMProvider):
    """
    OpenRouter API provider managing persistent HTTP pooling and dynamic model resolution.
    Caches OpenRouterModel instances to reuse persistent connection pools across model switches.
    """
    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        self._default_model = model_name or OPENROUTER_MODEL
        self._api_key = api_key or OPENROUTER_API_KEY
        self._provider = OpenRouterProvider(api_key=self._api_key)
        self._models: Dict[str, OpenRouterModel] = {}
        # Pre-cache default model
        self._models[self._default_model] = OpenRouterModel(self._default_model, provider=self._provider)

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def model_name(self) -> str:
        return self._default_model

    def get_model(self, model_name: Optional[str] = None) -> Model:
        """
        Retrieves or instantiates an OpenRouterModel reusing the shared provider HTTP pool.
        """
        target = model_name or self._default_model
        if target not in self._models:
            self._models[target] = OpenRouterModel(target, provider=self._provider)
        return self._models[target]

    def list_available_models(self) -> List[Dict[str, Any]]:
        """Returns the list of verified free OpenRouter models."""
        return FREE_OPENROUTER_MODELS

    async def close(self) -> None:
        if self._provider and hasattr(self._provider, "_client") and self._provider._client:
            client = self._provider._client
            if hasattr(client, "close"):
                res = client.close()
                if asyncio.iscoroutine(res):
                    await res
            elif hasattr(client, "aclose"):
                await client.aclose()
        self._models.clear()
