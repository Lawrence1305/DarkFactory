"""
Plugin Registry - Manages plugin lifecycle and discovery
"""

from typing import Dict, List, Optional, Type, Callable, Any
from pathlib import Path
import logging

from .plugin import Plugin, PluginMetadata, PluginType
from .hooks import HookRegistry

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Plugin Registry

    Manages plugin discovery, loading, enabling, and execution.

    Features:
    - Automatic discovery from plugins/ directory
    - Dependency resolution
    - Lifecycle management
    - Hook integration
    """

    def __init__(self, hooks: Optional[HookRegistry] = None):
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_classes: Dict[str, Type[Plugin]] = {}
        self._hooks = hooks or HookRegistry()
        self._search_paths: List[Path] = []

    @property
    def plugins(self) -> Dict[str, Plugin]:
        """Get all registered plugins"""
        return self._plugins.copy()

    @property
    def enabled_plugins(self) -> List[Plugin]:
        """Get all enabled plugins"""
        return [p for p in self._plugins.values() if p.enabled]

    def add_search_path(self, path: str) -> None:
        """Add directory to search for plugins"""
        p = Path(path)
        if p.exists() and p.is_dir():
            self._search_paths.append(p)

    def discover_plugins(self) -> List[str]:
        """
        Discover plugins from search paths

        Returns:
            List of discovered plugin names
        """
        discovered = []
        for search_path in self._search_paths:
            for plugin_file in search_path.glob("*.py"):
                if plugin_file.stem.startswith("_"):
                    continue
                try:
                    name = self._discover_plugin_file(plugin_file)
                    if name:
                        discovered.append(name)
                except Exception as e:
                    logger.warning(f"Failed to discover plugin {plugin_file}: {e}")
        return discovered

    def _discover_plugin_file(self, plugin_file: Path) -> Optional[str]:
        """Discover plugin class from file"""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            f"darkfactory.plugins.{plugin_file.stem}",
            plugin_file
        )
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        sys_modules_before = set(__import__('sys').modules.keys())
        spec.loader.exec_module(module)
        sys_modules_after = set(__import__('sys').modules.keys())

        new_modules = sys_modules_after - sys_modules_before
        for mod_name in new_modules:
            if mod_name.startswith("darkfactory.plugins"):
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, Plugin) and
                        attr is not Plugin):
                        self._plugin_classes[attr.name] = attr
                        return attr.name
        return None

    def register_plugin_class(self, plugin_class: Type[Plugin]) -> None:
        """
        Register a plugin class

        Args:
            plugin_class: Plugin class to register
        """
        if not issubclass(plugin_class, Plugin):
            raise TypeError("Must be subclass of Plugin")
        self._plugin_classes[plugin_class.name] = plugin_class

    def load_plugin(self, name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Load a plugin by name

        Args:
            name: Plugin name
            config: Optional configuration

        Returns:
            True if loaded successfully
        """
        if name in self._plugins:
            logger.warning(f"Plugin {name} already loaded")
            return True

        plugin_class = self._plugin_classes.get(name)
        if plugin_class is None:
            logger.error(f"Plugin class {name} not found")
            return False

        try:
            plugin = plugin_class()
            if config:
                plugin.configure(config)
            plugin.on_load()
            self._plugins[name] = plugin
            logger.info(f"Loaded plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
            return False

    def enable_plugin(self, name: str) -> bool:
        """
        Enable a loaded plugin

        Args:
            name: Plugin name

        Returns:
            True if enabled successfully
        """
        if name not in self._plugins:
            logger.error(f"Plugin {name} not loaded")
            return False

        plugin = self._plugins[name]
        if plugin.enabled:
            return True

        try:
            # Check dependencies
            for dep in plugin.dependencies:
                if dep not in self._plugins or not self._plugins[dep].enabled:
                    logger.error(f"Plugin {name} depends on {dep} which is not enabled")
                    return False

            plugin.on_enable()

            # Register plugin hooks
            for hook_name in plugin.hooks_provided:
                self._hooks.register(hook_name, name, lambda *args, plugin=plugin, h=hook_name: plugin.on_hook(h, *args))

            logger.info(f"Enabled plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable plugin {name}: {e}")
            return False

    def disable_plugin(self, name: str) -> bool:
        """
        Disable a plugin

        Args:
            name: Plugin name

        Returns:
            True if disabled successfully
        """
        if name not in self._plugins:
            return False

        plugin = self._plugins[name]
        if not plugin.enabled:
            return True

        try:
            plugin.on_disable()

            # Unregister hooks
            for hook_name in plugin.hooks_provided:
                self._hooks.unregister(hook_name, name)

            logger.info(f"Disabled plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to disable plugin {name}: {e}")
            return False

    def unload_plugin(self, name: str) -> bool:
        """
        Unload a plugin

        Args:
            name: Plugin name

        Returns:
            True if unloaded successfully
        """
        if name not in self._plugins:
            return False

        plugin = self._plugins[name]

        try:
            if plugin.enabled:
                self.disable_plugin(name)
            plugin.on_unload()
            del self._plugins[name]
            logger.info(f"Unloaded plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload plugin {name}: {e}")
            return False

    def execute_plugin(self, name: str, *args, **kwargs) -> Any:
        """
        Execute a plugin

        Args:
            name: Plugin name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Plugin execution result
        """
        if name not in self._plugins:
            raise ValueError(f"Plugin {name} not loaded")

        plugin = self._plugins[name]
        if not plugin.enabled:
            raise ValueError(f"Plugin {name} not enabled")

        return plugin.execute(*args, **kwargs)

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get plugin by name"""
        return self._plugins.get(name)

    def list_plugins(self, plugin_type: Optional[PluginType] = None) -> List[PluginMetadata]:
        """
        List all plugins

        Args:
            plugin_type: Optional filter by type

        Returns:
            List of plugin metadata
        """
        result = []
        for plugin in self._plugins.values():
            if plugin_type is None or plugin.metadata.plugin_type == plugin_type:
                result.append(plugin.metadata)
        return result

    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """
        Trigger a hook across all enabled plugins

        Args:
            hook_name: Hook name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            List of hook results
        """
        return self._hooks.trigger(hook_name, *args, **kwargs)
