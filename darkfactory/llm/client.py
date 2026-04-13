"""
LLM Client - Abstract base and factory for LLM providers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
import httpx

from ..config import LLMConfig, ProviderType


class MessageRole(Enum):
    """Message roles"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """Chat message"""
    role: MessageRole
    content: str


@dataclass
class LLMResponse:
    """LLM response"""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    raw: Optional[Dict[str, Any]] = None


class LLMClient(ABC):
    """Abstract LLM client"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    @abstractmethod
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        """Send chat request"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the client"""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


def create_llm_client(config: LLMConfig) -> LLMClient:
    """
    Factory function to create LLM client based on config

    Supports:
    - Anthropic-style: Claude, MiniMax, etc.
    - OpenAI-style: GPT-4, Qwen, DeepSeek, etc.
    """
    # Import here to avoid circular imports
    if config.provider_type == ProviderType.ANTHROPIC:
        from .anthropic_client import AnthropicClient
        return AnthropicClient(config)
    else:
        from .openai_client import OpenAIClient
        return OpenAIClient(config)
