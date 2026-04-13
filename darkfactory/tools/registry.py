"""
Tool Registry - Register and manage available tools
"""

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Tool category classification"""
    FILE = "file"
    EXECUTION = "execution"
    SEARCH = "search"
    MEMORY = "memory"
    SKILL = "skill"
    VALIDATION = "validation"
    WEB = "web"
    CUSTOM = "custom"


@dataclass
class ToolMetadata:
    """Tool metadata"""
    name: str
    description: str
    category: ToolCategory = ToolCategory.CUSTOM
    parameters: Dict[str, Any] = field(default_factory=dict)
    returns: Dict[str, Any] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)


@dataclass
class Tool:
    """
    Tool Definition

    A tool that can be executed by the agent.
    """
    metadata: ToolMetadata
    handler: Callable[..., Any]

    def execute(self, *args, **kwargs) -> Any:
        """Execute the tool"""
        return self.handler(*args, **kwargs)


class ToolRegistry:
    """
    Tool Registry

    Central registry for all available tools.
    Tools are registered by name and can be looked up and executed.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {}

    def register(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        category: ToolCategory = ToolCategory.CUSTOM,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a tool

        Args:
            name: Tool name
            handler: Handler function
            description: Tool description
            category: Tool category
            parameters: Parameter schema
        """
        metadata = ToolMetadata(
            name=name,
            description=description,
            category=category,
            parameters=parameters or {},
        )

        tool = Tool(metadata=metadata, handler=handler)
        self._tools[name] = tool

        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)

        logger.info(f"Registered tool: {name} ({category.value})")

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool

        Args:
            name: Tool name

        Returns:
            True if unregistered
        """
        if name not in self._tools:
            return False

        tool = self._tools[name]
        category = tool.metadata.category

        del self._tools[name]

        if category in self._categories:
            self._categories[category].remove(name)

        logger.info(f"Unregistered tool: {name}")
        return True

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self._tools.get(name)

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolMetadata]:
        """
        List all tools

        Args:
            category: Optional category filter

        Returns:
            List of tool metadata
        """
        if category:
            tool_names = self._categories.get(category, [])
            return [self._tools[name].metadata for name in tool_names if name in self._tools]

        return [tool.metadata for tool in self._tools.values()]

    def execute(self, name: str, *args, **kwargs) -> Any:
        """
        Execute a tool

        Args:
            name: Tool name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tool execution result
        """
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Tool not found: {name}")

        try:
            return tool.execute(*args, **kwargs)
        except Exception as e:
            logger.error(f"Tool execution error ({name}): {e}")
            raise

    def has_tool(self, name: str) -> bool:
        """Check if tool exists"""
        return name in self._tools


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get global tool registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
