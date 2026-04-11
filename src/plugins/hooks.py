"""
Hooks - Event hook system for plugin communication
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class Hook:
    """
    Hook definition

    A hook is a named event that plugins can register to.
    """
    name: str
    handler: Callable[..., Any]
    plugin_name: str
    priority: int = 100  # Lower = higher priority
    is_async: bool = False


class HookRegistry:
    """
    Hook Registry

    Manages event hooks for plugin communication.

    Usage:
        # Register a hook
        registry.register("task_completed", "my-plugin", my_handler)

        # Trigger hooks
        results = registry.trigger("task_completed", task_id="123")

        # Unregister
        registry.unregister("task_completed", "my-plugin")
    """

    def __init__(self):
        self._hooks: Dict[str, List[Hook]] = defaultdict(list)
        self._global_hooks: List[Hook] = []

    def register(
        self,
        name: str,
        plugin_name: str,
        handler: Callable[..., Any],
        priority: int = 100,
        is_async: bool = False,
    ) -> None:
        """
        Register a hook handler

        Args:
            name: Hook name
            plugin_name: Plugin registering the hook
            handler: Handler function
            priority: Handler priority (lower = higher priority)
            is_async: Whether handler is async
        """
        hook = Hook(
            name=name,
            handler=handler,
            plugin_name=plugin_name,
            priority=priority,
            is_async=is_async,
        )

        if name == "*":
            self._global_hooks.append(hook)
        else:
            self._hooks[name].append(hook)
            self._hooks[name].sort(key=lambda h: h.priority)

    def unregister(self, name: str, plugin_name: str) -> bool:
        """
        Unregister a hook

        Args:
            name: Hook name
            plugin_name: Plugin name

        Returns:
            True if unregistered
        """
        if name == "*":
            before = len(self._global_hooks)
            self._global_hooks = [
                h for h in self._global_hooks if h.plugin_name != plugin_name
            ]
            return len(self._global_hooks) < before

        if name not in self._hooks:
            return False

        before = len(self._hooks[name])
        self._hooks[name] = [
            h for h in self._hooks[name] if h.plugin_name != plugin_name
        ]
        return len(self._hooks[name]) < before

    def trigger(self, name: str, *args, **kwargs) -> List[Any]:
        """
        Trigger a hook

        Args:
            name: Hook name
            *args: Positional arguments passed to handlers
            **kwargs: Keyword arguments passed to handlers

        Returns:
            List of handler results
        """
        results = []

        # Trigger global hooks
        for hook in self._global_hooks:
            try:
                if hook.is_async:
                    logger.warning(f"Global hook {hook.name} is async but trigger is sync")
                result = hook.handler(*args, **kwargs)
                if result is not None:
                    results.append(result)
            except Exception as e:
                logger.error(f"Hook handler error ({hook.plugin_name}): {e}")

        # Trigger named hooks
        if name in self._hooks:
            for hook in self._hooks[name]:
                try:
                    if hook.is_async:
                        logger.warning(f"Hook {name} is async but trigger is sync")
                    result = hook.handler(*args, **kwargs)
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Hook handler error ({hook.plugin_name}): {e}")

        return results

    async def trigger_async(self, name: str, *args, **kwargs) -> List[Any]:
        """
        Async trigger a hook

        Args:
            name: Hook name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            List of handler results
        """
        results = []

        # Collect all hooks
        all_hooks = list(self._global_hooks) + list(self._hooks.get(name, []))

        # Execute async hooks
        for hook in all_hooks:
            if hook.is_async:
                try:
                    result = await hook.handler(*args, **kwargs)
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Async hook handler error ({hook.plugin_name}): {e}")

        # Execute sync hooks (in executor)
        for hook in all_hooks:
            if not hook.is_async:
                try:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, lambda: hook.handler(*args, **kwargs)
                    )
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Hook handler error ({hook.plugin_name}): {e}")

        return results

    def list_hooks(self, name: Optional[str] = None) -> List[Hook]:
        """
        List registered hooks

        Args:
            name: Optional hook name filter

        Returns:
            List of hooks
        """
        if name:
            return list(self._hooks.get(name, []))
        return list(self._hooks.values())

    def has_hook(self, name: str) -> bool:
        """Check if hook exists"""
        return name in self._hooks and len(self._hooks[name]) > 0


# === Standard Hook Names ===

class Hooks:
    """Standard hook names used by DarkFactory"""

    # Task lifecycle
    TASK_BEFORE_SELECT = "task:before_select"
    TASK_AFTER_SELECT = "task:after_select"
    TASK_BEFORE_EXECUTE = "task:before_execute"
    TASK_AFTER_EXECUTE = "task:after_execute"
    TASK_COMPLETED = "task:completed"
    TASK_FAILED = "task:failed"
    TASK_BLOCKED = "task:blocked"

    # Validation
    VALIDATE_BEFORE = "validate:before"
    VALIDATE_AFTER = "validate:after"
    VALIDATE_FAILED = "validate:failed"

    # Memory
    MEMORY_BEFORE_STORE = "memory:before_store"
    MEMORY_AFTER_STORE = "memory:after_store"
    MEMORY_BEFORE_SEARCH = "memory:before_search"

    # Skills
    SKILL_CREATED = "skill:created"
    SKILL_BEFORE_USE = "skill:before_use"
    SKILL_AFTER_USE = "skill:after_use"

    # Agent
    AGENT_START = "agent:start"
    AGENT_STOP = "agent:stop"
    AGENT_MESSAGE = "agent:message"

    # Workflow
    WORKFLOW_START = "workflow:start"
    WORKFLOW_STEP = "workflow:step"
    WORKFLOW_COMPLETE = "workflow:complete"
    WORKFLOW_FAILED = "workflow:failed"

    # Plugin
    PLUGIN_LOAD = "plugin:load"
    PLUGIN_ENABLE = "plugin:enable"
    PLUGIN_DISABLE = "plugin:disable"
