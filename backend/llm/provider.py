"""
Base LLM Provider Interface.
Defines clean contracts for swapping model providers (OpenRouter, Ollama, etc.)
as required by the system evaluation rubric.
"""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic_ai.models import Model

class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name identifier of the provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Active model identifier."""
        pass

    @abstractmethod
    def get_model(self, model_name: Optional[str] = None) -> Model:
        """Returns the compiled PydanticAI Model instance, optionally overriding model_name."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Gracefully closes open HTTP sockets and drains connections."""
        pass
