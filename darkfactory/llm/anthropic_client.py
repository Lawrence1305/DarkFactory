"""
Anthropic-style LLM Client

Supports:
- Claude (Anthropic)
- MiniMax (via OpenAI-compatible API with anthropic endpoint)
- Other anthropic-compatible APIs
"""

import httpx
from typing import List, Dict, Any, Optional

from .client import LLMClient, LLMResponse, Message, MessageRole
from ..config import LLMConfig


class AnthropicClient(LLMClient):
    """
    Anthropic-style API client

    Works with:
    - Anthropic Claude API
    - MiniMax (anthropic endpoint)
    - Any anthropic-compatible API
    """

    ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_url = self.config.base_url or self.ANTHROPIC_API_URL

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers"""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true",
        }
        return headers

    def _build_body(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """Build request body"""
        # Convert messages to anthropic format
        anthropic_messages = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # System messages handled separately
                continue
            anthropic_messages.append({
                "role": msg.role.value,
                "content": msg.content,
            })

        body = {
            "model": self.config.model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        # Add system message if present
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                body["system"] = msg.content
                break

        return body

    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        """Send chat request to anthropic-compatible API"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)

        headers = self._build_headers()
        body = self._build_body(messages, **kwargs)

        try:
            response = await self._client.post(
                self.api_url,
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()

            return LLMResponse(
                content=data["content"][0]["text"],
                model=data.get("model", self.config.model),
                usage={
                    "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                },
                raw=data,
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid API key")
            elif e.response.status_code == 429:
                raise ValueError("Rate limit exceeded")
            else:
                raise RuntimeError(f"Anthropic API error: {e.response.status_code} - {e.response.text}")

        except Exception as e:
            raise RuntimeError(f"Failed to call Anthropic API: {e}")

    async def close(self) -> None:
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# MiniMax-specific configuration example
MINIMAX_CONFIG = {
    "provider_type": "anthropic",
    "base_url": "https://api.minimax.chat/v1/text/chatcompletion_v2",
    "model": "MiniMax-Text-01",
    # Extra headers might be needed
    "extra": {
        "group_id": "your_group_id",
    }
}
