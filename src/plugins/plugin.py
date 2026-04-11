"""
Plugin Base - OpenClaw-style plugin architecture
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import importlib.util
import sys
from pathlib import Path


class PluginType(Enum):
    """Plugin type classification"""
    BUILTIN = "builtin"
    LINTER = "linter"
    TEST_RUNNER = "test_runner"
    BROWSER = "browser"
    VALIDATOR = "validator"
    MEMORY = "memory"
    SKILL = "skill"
    CUSTOM = "custom"


@dataclass
class PluginMetadata:
    """Plugin metadata"""
    name: str
    version: str
    description: str
    author: str = ""
    plugin_type: PluginType = PluginType.CUSTOM
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    hooks_provided: List[str] = field(default_factory=list)


class Plugin(ABC):
    """
    Plugin Base Class

    All plugins inherit from this class.
    OpenClaw-style architecture with lifecycle hooks.

    Usage:
        class MyPlugin(Plugin):
            name = "my-plugin"
            version = "1.0.0"

            def on_load(self) -> None:
                ...

            def execute(self, context: dict) -> Any:
                ...
    """

    # Plugin metadata (override in subclass)
    name: str = "base-plugin"
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    plugin_type: PluginType = PluginType.CUSTOM
    dependencies: List[str] = []
    config_schema: Dict[str, Any] = {}
    hooks_provided: List[str] = []

    def __init__(self):
        self._enabled: bool = False
        self._config: Dict[str, Any] = {}
        self._context: Dict[str, Any] = {}

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled"""
        return self._enabled

    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata"""
        return PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            plugin_type=self.plugin_type,
            dependencies=self.dependencies,
            config_schema=self.config_schema,
            hooks_provided=self.hooks_provided,
        )

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure plugin

        Args:
            config: Configuration dictionary
        """
        self._config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration against schema"""
        for key in self.config_schema:
            if key not in self._config:
                if self.config_schema[key].get("required", False):
                    raise ValueError(f"Required config key '{key}' missing for plugin {self.name}")

    # === Lifecycle Hooks ===

    def on_load(self) -> None:
        """
        Called when plugin is loaded

        Override to perform initialization.
        """
        pass

    def on_enable(self) -> None:
        """
        Called when plugin is enabled

        Override to perform enable logic.
        """
        self._enabled = True

    def on_disable(self) -> None:
        """
        Called when plugin is disabled

        Override to perform cleanup.
        """
        self._enabled = False

    def on_unload(self) -> None:
        """
        Called when plugin is unloaded

        Override to perform final cleanup.
        """
        pass

    def on_hook(self, hook_name: str, *args, **kwargs) -> Any:
        """
        Hook handler

        Called when a specific hook is triggered.

        Args:
            hook_name: Name of the hook
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Hook result
        """
        hook_method = getattr(self, f"hook_{hook_name}", None)
        if hook_method and callable(hook_method):
            return hook_method(*args, **kwargs)
        return None

    # === Execution ===

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        Execute plugin main functionality

        Must be implemented by subclass.
        """
        pass

    def set_context(self, key: str, value: Any) -> None:
        """Set execution context value"""
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get execution context value"""
        return self._context.get(key, default)


class BuiltinPlugin(Plugin):
    """Base class for built-in plugins"""
    plugin_type: PluginType = PluginType.BUILTIN


class LinterPlugin(Plugin):
    """Base class for linter plugins"""
    plugin_type: PluginType = PluginType.LINTER


class TestRunnerPlugin(Plugin):
    """Base class for test runner plugins"""
    plugin_type: PluginType = PluginType.TEST_RUNNER


class BrowserPlugin(Plugin):
    """Base class for browser/Playwright plugins"""
    plugin_type: PluginType = PluginType.BROWSER


class ValidatorPlugin(Plugin):
    """Base class for validator plugins"""
    plugin_type: PluginType = PluginType.VALIDATOR


def load_plugin_from_path(plugin_path: str, plugin_name: str) -> Plugin:
    """
    Load plugin from file path

    Args:
        plugin_path: Path to plugin file
        plugin_name: Plugin class name

    Returns:
        Loaded plugin instance
    """
    spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load plugin from {plugin_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[plugin_name] = module
    spec.loader.exec_module(module)

    plugin_class = getattr(module, plugin_name, None)
    if plugin_class is None:
        raise AttributeError(f"Plugin class {plugin_name} not found in {plugin_path}")

    return plugin_class()
