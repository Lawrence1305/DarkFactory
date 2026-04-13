"""
Tool Result Pruner - Prune large tool results for context efficiency
"""

from typing import Any, Dict, List, Optional
import re


class ToolResultPruner:
    """
    Tool Result Pruner

    Prunes large tool results to reduce token count while preserving essential information.

    Techniques:
    - Truncate long output
    - Remove stack traces (keep summary)
    - Remove verbose logging
    - Keep error summaries
    """

    # Thresholds
    MAX_OUTPUT_LENGTH = 2000
    MAX_STACKTRACE_LINES = 5

    # Patterns for removal
    VERBOSE_PATTERNS = [
        (r'DEBUG:.*\n', ''),
        (r'INFO:.*\n', ''),
        (r'\[DEBUG\].*\n', ''),
        (r'\[INFO\].*\n', ''),
        (r'Traceback \(most recent call last\):.*', 'Traceback (truncated)'),
    ]

    def prune_tool_result(
        self,
        tool_name: str,
        result: Any,
        max_length: Optional[int] = None,
    ) -> str:
        """
        Prune a tool result

        Args:
            tool_name: Name of the tool
            result: Tool result (usually string)
            max_length: Maximum output length

        Returns:
            Pruned string
        """
        max_len = max_length or self.MAX_OUTPUT_LENGTH

        # Convert to string
        if not isinstance(result, str):
            result = str(result)

        # Apply tool-specific pruning
        if tool_name in ["bash", "shell"]:
            result = self._prune_shell_output(result)
        elif tool_name in ["read", "glob"]:
            result = self._prune_file_output(result)
        elif tool_name == "browser":
            result = self._prune_browser_output(result)

        # General pruning
        result = self._prune_verbose(result)
        result = self._prune_stacktrace(result)

        # Truncate if still too long
        if len(result) > max_len:
            result = result[:max_len - 3] + "..."

        return result

    def _prune_shell_output(self, output: str) -> str:
        """Prune shell command output"""
        lines = output.split('\n')

        # Keep first and last N lines for long output
        if len(lines) > 50:
            kept_lines = lines[:10]
            kept_lines.append(f"... [{len(lines) - 20} lines truncated] ...")
            kept_lines.extend(lines[-10:])
            return '\n'.join(kept_lines)

        return output

    def _prune_file_output(self, content: str) -> str:
        """Prune file content"""
        lines = content.split('\n')

        # Keep first and last N lines for long files
        if len(lines) > 100:
            kept_lines = lines[:30]
            kept_lines.append(f"\n... [{len(lines) - 60} lines truncated] ...\n")
            kept_lines.extend(lines[-30:])
            return '\n'.join(kept_lines)

        return content

    def _prune_browser_output(self, content: str) -> str:
        """Prune browser/Playwright output"""
        # Remove console logs spam
        lines = content.split('\n')
        filtered = []

        for line in lines:
            # Skip repetitive console logs
            if re.match(r'\[console\..*\]', line):
                continue
            filtered.append(line)

        return '\n'.join(filtered)

    def _prune_verbose(self, text: str) -> str:
        """Remove verbose logging"""
        for pattern, replacement in self.VERBOSE_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _prune_stacktrace(self, text: str) -> str:
        """Prune stack traces"""
        lines = text.split('\n')
        pruned_lines = []
        in_traceback = False
        traceback_count = 0

        for line in lines:
            if 'traceback' in line.lower():
                in_traceback = True
                traceback_count = 0
                pruned_lines.append(line)
            elif in_traceback:
                traceback_count += 1
                if traceback_count <= self.MAX_STACKTRACE_LINES:
                    pruned_lines.append(line)
                elif traceback_count == self.MAX_STACKTRACE_LINES + 1:
                    pruned_lines.append(f"... [{traceback_count} stack frames truncated] ...")
                # Skip remaining traceback lines
            else:
                pruned_lines.append(line)

        return '\n'.join(pruned_lines)

    def batch_prune(
        self,
        tool_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Prune multiple tool results

        Args:
            tool_results: List of {tool: str, result: Any}

        Returns:
            List of pruned results
        """
        pruned = []

        for item in tool_results:
            pruned_result = self.prune_tool_result(
                item.get("tool", "unknown"),
                item.get("result", ""),
            )
            pruned.append({
                "tool": item.get("tool"),
                "result": pruned_result,
            })

        return pruned
