"""
Built-in plugins
"""

from .linter_plugin import LinterPlugin
from .test_runner_plugin import TestRunnerPlugin
from .browser_plugin import BrowserPlugin

__all__ = [
    "LinterPlugin",
    "TestRunnerPlugin",
    "BrowserPlugin",
]
