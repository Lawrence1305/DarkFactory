"""
Tool Executor - Execute tools with proper error handling and result formatting
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from .registry import ToolRegistry, get_registry
from .results import ToolResult, ToolError

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Tool Executor

    Executes tools with proper error handling, logging, and result formatting.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or get_registry()
        self._execution_history: List[Dict[str, Any]] = []

    def execute(
        self,
        tool_name: str,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """
        Execute a tool

        Args:
            tool_name: Name of the tool to execute
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            ToolResult with success status and output
        """
        start_time = datetime.now()
        args = args or []
        kwargs = kwargs or {}

        tool = self.registry.get_tool(tool_name)
        if tool is None:
            error = ToolError(
                code="TOOL_NOT_FOUND",
                message=f"Tool not found: {tool_name}",
            )
            return ToolResult(
                success=False,
                tool=tool_name,
                error=error,
                duration_ms=0,
            )

        try:
            logger.info(f"Executing tool: {tool_name}")
            output = tool.execute(*args, **kwargs)

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            result = ToolResult(
                success=True,
                tool=tool_name,
                output=output,
                duration_ms=duration_ms,
            )

            self._execution_history.append({
                "tool": tool_name,
                "success": True,
                "duration_ms": duration_ms,
                "timestamp": start_time.isoformat(),
            })

            return result

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            logger.error(f"Tool execution error ({tool_name}): {e}")

            error = ToolError(
                code="EXECUTION_ERROR",
                message=str(e),
            )

            result = ToolResult(
                success=False,
                tool=tool_name,
                error=error,
                duration_ms=duration_ms,
            )

            self._execution_history.append({
                "tool": tool_name,
                "success": False,
                "error": str(e),
                "duration_ms": duration_ms,
                "timestamp": start_time.isoformat(),
            })

            return result

    def execute_batch(
        self,
        executions: List[Dict[str, Any]],
    ) -> List[ToolResult]:
        """
        Execute multiple tools in batch

        Args:
            executions: List of {tool: str, args?: list, kwargs?: dict}

        Returns:
            List of ToolResults
        """
        results = []
        for exec_item in executions:
            result = self.execute(
                exec_item["tool"],
                args=exec_item.get("args"),
                kwargs=exec_item.get("kwargs"),
            )
            results.append(result)

        return results

    def get_history(
        self,
        tool_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get execution history

        Args:
            tool_name: Filter by tool name
            limit: Maximum entries to return

        Returns:
            List of execution records
        """
        history = self._execution_history

        if tool_name:
            history = [h for h in history if h["tool"] == tool_name]

        return history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self._execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "average_duration_ms": 0,
            }

        total = len(self._execution_history)
        successes = sum(1 for h in self._execution_history if h["success"])
        total_duration = sum(h["duration_ms"] for h in self._execution_history)

        return {
            "total_executions": total,
            "success_rate": successes / total if total > 0 else 0.0,
            "average_duration_ms": total_duration // total if total > 0 else 0,
            "by_tool": self._get_stats_by_tool(),
        }

    def _get_stats_by_tool(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics grouped by tool"""
        stats: Dict[str, Dict[str, Any]] = {}

        for h in self._execution_history:
            tool = h["tool"]
            if tool not in stats:
                stats[tool] = {"total": 0, "successes": 0, "failures": 0}

            stats[tool]["total"] += 1
            if h["success"]:
                stats[tool]["successes"] += 1
            else:
                stats[tool]["failures"] += 1

        return stats
