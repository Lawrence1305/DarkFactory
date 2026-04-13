"""
OpenAI-style LLM Client

Supports:
- OpenAI GPT-4, GPT-3.5
- Qwen (阿里通义)
- DeepSeek
- Any OpenAI-compatible API
"""

import httpx
from typing import List, Dict, Any, Optional

from .client import LLMClient, LLMResponse, Message, MessageRole
from ..config import LLMConfig


class OpenAIClient(LLMClient):
    """
    OpenAI-style API client

    Works with:
    - OpenAI GPT-4, GPT-3.5
    - Qwen (阿里通义千问)
    - DeepSeek
    - Any OpenAI-compatible API
    """

    OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_url = self.config.base_url or self.OPENAI_API_URL

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        return headers

    def _build_body(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """Build request body"""
        # Convert messages to openai format
        openai_messages = []
        for msg in messages:
            openai_messages.append({
                "role": msg.role.value,
                "content": msg.content,
            })

        body = {
            "model": self.config.model,
            "messages": openai_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        # Add optional parameters
        if kwargs.get("stream"):
            body["stream"] = True

        return body

    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        """Send chat request to OpenAI-compatible API"""
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
                content=data["choices"][0]["message"]["content"],
                model=data.get("model", self.config.model),
                usage={
                    "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": data.get("usage", {}).get("total_tokens", 0),
                },
                raw=data,
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid API key")
            elif e.response.status_code == 429:
                raise ValueError("Rate limit exceeded")
            else:
                raise RuntimeError(f"OpenAI API error: {e.response.status_code} - {e.response.text}")

        except Exception as e:
            raise RuntimeError(f"Failed to call OpenAI API: {e}")

    async def close(self) -> None:
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Qwen-specific configuration example
QWEN_CONFIG = {
    "provider_type": "openai",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "qwen-plus",
    "api_key": "your_qwen_api_key",
}

# DeepSeek-specific configuration example
DEEPSEEK_CONFIG = {
    "provider_type": "openai",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "api_key": "your_deepseek_api_key",
}
