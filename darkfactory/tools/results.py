"""
Tool Results - Standardized output format for tool execution
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
from datetime import datetime
import json


@dataclass
class ToolError:
    """Tool execution error"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ToolResult:
    """
    Tool Execution Result

    Standardized result format for all tool executions.
    """
    success: bool
    tool: str
    output: Any = None
    error: Optional[ToolError] = None
    duration_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "tool": self.tool,
            "output": self.output,
            "error": self.error.code + ": " + self.error.message if self.error else None,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)

    def __str__(self) -> str:
        """String representation"""
        if self.success:
            output_preview = str(self.output)[:100]
            if len(str(self.output)) > 100:
                output_preview += "..."
            return f"ToolResult({self.tool}): success - {output_preview}"
        else:
            return f"ToolResult({self.tool}): error - {self.error.message if self.error else 'unknown'}"


class ToolOutput:
    """
    Tool Output Builder

    Helper to build structured tool output.
    """

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self._sections: List[Dict[str, Any]] = []

    def add_section(self, title: str, content: Any, format: str = "text") -> "ToolOutput":
        """
        Add a section to the output

        Args:
            title: Section title
            content: Section content
            format: Content format (text, json, table)

        Returns:
            Self for chaining
        """
        self._sections.append({
            "title": title,
            "content": content,
            "format": format,
        })
        return self

    def add_table(self, title: str, headers: List[str], rows: List[List[Any]]) -> "ToolOutput":
        """Add a table section"""
        self._sections.append({
            "title": title,
            "type": "table",
            "headers": headers,
            "rows": rows,
        })
        return self

    def add_list(self, title: str, items: List[str]) -> "ToolOutput":
        """Add a list section"""
        self._sections.append({
            "title": title,
            "type": "list",
            "items": items,
        })
        return self

    def build(self) -> Dict[str, Any]:
        """Build the output dictionary"""
        return {
            "tool": self.tool_name,
            "sections": self._sections,
        }

    def __str__(self) -> str:
        """Build text representation"""
        lines = [f"[{self.tool_name}]"]

        for section in self._sections:
            lines.append(f"\n{section['title']}:")
            lines.append(f"  {section['content']}")

        return "\n".join(lines)
