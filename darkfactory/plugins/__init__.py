"""
Plugins module - OpenClaw-style plugin system
"""

from .plugin import Plugin, PluginMetadata
from .plugin_registry import PluginRegistry
from .hooks import Hook, HookRegistry

__all__ = [
    "Plugin",
    "PluginMetadata",
    "PluginRegistry",
    "Hook",
    "HookRegistry",
]
