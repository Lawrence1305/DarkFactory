"""
Configuration Module - AI API and Framework Configuration

Supports multiple LLM providers:
- Anthropic-style (Claude, MiniMax, etc.)
- OpenAI-style (GPT-4, Qwen, etc.)
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    CUSTOM = "custom"


class ProviderType(Enum):
    """API style type"""
    ANTHROPIC = "anthropic"  # Uses anthropic messages API
    OPENAI = "openai"         # Uses OpenAI chat completions API


# Known provider patterns for auto-detection
KNOWN_PROVIDERS = {
    # Anthropic-compatible
    "api.anthropic.com": ProviderType.ANTHROPIC,
    "api.minimax.chat": ProviderType.ANTHROPIC,
    # OpenAI-compatible
    "api.openai.com": ProviderType.OPENAI,
    "api.deepseek.com": ProviderType.OPENAI,
    "dashscope.aliyuncs.com": ProviderType.OPENAI,  # Qwen
    "openai.azure.com": ProviderType.OPENAI,
}


def detect_provider_type(base_url: str) -> ProviderType:
    """Auto-detect provider type from base URL"""
    if not base_url:
        return ProviderType.ANTHROPIC  # Default to Anthropic

    base_url_lower = base_url.lower()

    for known_host, provider_type in KNOWN_PROVIDERS.items():
        if known_host in base_url_lower:
            return provider_type

    # Check for common patterns
    if "anthropic" in base_url_lower:
        return ProviderType.ANTHROPIC
    if "openai" in base_url_lower or "chat/completions" in base_url_lower:
        return ProviderType.OPENAI

    # Default to OpenAI (more common for third-party)
    return ProviderType.OPENAI


@dataclass
class LLMConfig:
    """LLM Provider Configuration"""
    provider: LLMProvider = LLMProvider.ANTHROPIC
    provider_type: ProviderType = ProviderType.ANTHROPIC

    # API Settings
    api_key: str = ""
    base_url: str = ""  # Custom endpoint for third-party providers

    # Model Settings
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60

    # Provider-specific settings
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryConfig:
    """Memory System Configuration"""
    memory_path: str = "./memory"
    palace_path: str = "./memory/palace"
    kg_path: str = "./memory/kg.db"
    max_memory_tokens: int = 100000


@dataclass
class AgentConfig:
    """Agent Configuration"""
    max_agents: int = 4
    max_retries: int = 3
    agent_timeout: int = 300


@dataclass
class ValidationConfig:
    """Validation Configuration"""
    validation_level: str = "strict"  # relaxed, standard, strict
    auto_validate: bool = True
    require_tests: bool = True


@dataclass
class SkillConfig:
    """Skill Generation Configuration"""
    auto_generate: bool = True
    min_tool_calls: int = 5
    error_recovery_weight: float = 1.5
    user_correction_weight: float = 2.0


@dataclass
class Config:
    """Main Configuration"""
    # LLM Settings
    llm: LLMConfig = field(default_factory=LLMConfig)

    # Memory Settings
    memory: MemoryConfig = field(default_factory=MemoryConfig)

    # Agent Settings
    agent: AgentConfig = field(default_factory=AgentConfig)

    # Validation Settings
    validation: ValidationConfig = field(default_factory=ValidationConfig)

    # Skill Settings
    skill: SkillConfig = field(default_factory=SkillConfig)

    # Workspace
    workspace: str = "."

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables"""
        config = cls()

        # Base URL first (for auto-detection)
        config.llm.base_url = os.getenv("DARKFACTORY_BASE_URL", "")

        # LLM Provider - auto-detect from base_url or use env var
        explicit_type = os.getenv("DARKFACTORY_PROVIDER_TYPE", "").lower()
        if explicit_type:
            config.llm.provider_type = ProviderType.ANTHROPIC if explicit_type == "anthropic" else ProviderType.OPENAI
        else:
            config.llm.provider_type = detect_provider_type(config.llm.base_url)

        config.llm.provider = LLMProvider.CUSTOM if config.llm.base_url else config.llm.provider

        # API Key
        config.llm.api_key = os.getenv("DARKFACTORY_API_KEY", "")
        if not config.llm.api_key:
            config.llm.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not config.llm.api_key:
            config.llm.api_key = os.getenv("OPENAI_API_KEY", "")

        # Model
        config.llm.model = os.getenv("DARKFACTORY_MODEL", config.llm.model)

        # Memory
        config.memory.memory_path = os.getenv("DARKFACTORY_MEMORY_PATH", "./memory")
        config.memory.palace_path = os.getenv("DARKFACTORY_PALACE_PATH", "./memory/palace")
        config.memory.kg_path = os.getenv("DARKFACTORY_KG_PATH", "./memory/kg.db")

        # Agent
        config.agent.max_agents = int(os.getenv("DARKFACTORY_MAX_AGENTS", "4"))

        return config

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Load config from JSON file"""
        config_path = Path(path)
        if not config_path.exists():
            return cls.from_env()

        with open(config_path) as f:
            data = json.load(f)

        config = cls()

        # LLM
        if "llm" in data:
            llm_data = data["llm"]
            config.llm.api_key = llm_data.get("api_key", "")
            config.llm.base_url = llm_data.get("base_url", "")
            config.llm.model = llm_data.get("model", config.llm.model)
            config.llm.max_tokens = llm_data.get("max_tokens", config.llm.max_tokens)
            config.llm.temperature = llm_data.get("temperature", config.llm.temperature)
            config.llm.extra = llm_data.get("extra", {})

            # Auto-detect provider type from base_url if not specified
            explicit_type = llm_data.get("provider_type", "")
            if explicit_type:
                config.llm.provider_type = ProviderType(explicit_type)
            else:
                config.llm.provider_type = detect_provider_type(config.llm.base_url)

            # Provider
            provider_name = llm_data.get("provider", "")
            if provider_name:
                config.llm.provider = LLMProvider(provider_name)

        # Memory
        if "memory" in data:
            config.memory.memory_path = data["memory"].get("memory_path", config.memory.memory_path)
            config.memory.palace_path = data["memory"].get("palace_path", config.memory.palace_path)
            config.memory.kg_path = data["memory"].get("kg_path", config.memory.kg_path)

        # Agent
        if "agent" in data:
            config.agent.max_agents = data["agent"].get("max_agents", config.agent.max_agents)

        # Validation
        if "validation" in data:
            config.validation.validation_level = data["validation"].get("level", config.validation.validation_level)

        # Skill
        if "skill" in data:
            config.skill.auto_generate = data["skill"].get("auto_generate", config.skill.auto_generate)

        # Workspace
        config.workspace = data.get("workspace", ".")

        return config

    def save(self, path: str) -> None:
        """Save config to JSON file"""
        data = {
            "llm": {
                "provider": self.llm.provider.value,
                "provider_type": self.llm.provider_type.value,
                "api_key": self.llm.api_key,
                "base_url": self.llm.base_url,
                "model": self.llm.model,
                "max_tokens": self.llm.max_tokens,
                "temperature": self.llm.temperature,
                "extra": self.llm.extra,
            },
            "memory": {
                "memory_path": self.memory.memory_path,
                "palace_path": self.memory.palace_path,
                "kg_path": self.memory.kg_path,
            },
            "agent": {
                "max_agents": self.agent.max_agents,
            },
            "validation": {
                "level": self.validation.validation_level,
            },
            "skill": {
                "auto_generate": self.skill.auto_generate,
            },
            "workspace": self.workspace,
        }

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def validate(self) -> None:
        """Validate configuration"""
        if not self.llm.api_key:
            raise ValueError(
                "API key not configured. "
                "Set DARKFACTORY_API_KEY or ANTHROPIC_API_KEY or OPENAI_API_KEY"
            )


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance"""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file or environment"""
    global _config
    if config_path:
        _config = Config.from_file(config_path)
    else:
        _config = Config.from_env()
    _config.validate()
    return _config


def reset_config() -> None:
    """Reset global config (for testing)"""
    global _config
    _config = None
