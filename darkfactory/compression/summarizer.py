"""
Summarizer - Generate summaries for context compression
"""

from typing import Dict, Any, List, Optional
import re


class Summarizer:
    """
    Summarizer for conversation context

    Generates concise summaries while preserving key information.
    """

    def summarize_messages(
        self,
        messages: List[Dict[str, Any]],
        max_length: int = 500,
    ) -> str:
        """
        Summarize a list of messages

        Args:
            messages: Messages to summarize
            max_length: Maximum summary length in characters

        Returns:
            Summary string
        """
        if not messages:
            return "No messages to summarize."

        # Extract key elements
        tools = self._extract_tools(messages)
        tasks = self._extract_tasks(messages)
        errors = self._extract_errors(messages)
        outcomes = self._extract_outcomes(messages)

        # Build summary
        parts = []

        if tasks:
            parts.append(f"Tasks: {', '.join(tasks[:5])}")
        if tools:
            parts.append(f"Tools: {', '.join(tools[:10])}")
        if errors:
            parts.append(f"Errors: {len(errors)} encountered")
        if outcomes:
            parts.append(f"Outcomes: {outcomes[:2]}")

        summary = " | ".join(parts)

        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."

        return summary

    def summarize_task_execution(
        self,
        task_id: str,
        steps: List[str],
        result: str,
        errors: List[str],
    ) -> str:
        """
        Summarize task execution

        Args:
            task_id: Task identifier
            steps: Execution steps
            result: Execution result
            errors: Any errors encountered

        Returns:
            Summary string
        """
        lines = [f"Task #{task_id} execution summary:"]

        if steps:
            lines.append(f"- Steps completed: {len(steps)}")
            lines.append(f"- Last step: {steps[-1][:50]}...")

        if result:
            lines.append(f"- Result: {result[:100]}...")

        if errors:
            lines.append(f"- Errors: {len(errors)}")
            lines.append(f"- Last error: {errors[-1][:50]}...")

        return "\n".join(lines)

    def _extract_tools(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract tool mentions from messages"""
        tools = set()
        patterns = [
            r'using (tool| инструмент) (\w+)',
            r'tool: (\w+)',
            r'executed (\w+)\(',
        ]

        for msg in messages:
            content = msg.get("content", "")
            for pattern in patterns:
                matches = re.findall(pattern, content, re.I)
                for match in matches:
                    tool = match[1] if isinstance(match, tuple) else match
                    tools.add(tool)

        return list(tools)

    def _extract_tasks(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract task mentions from messages"""
        tasks = []
        pattern = r'(?:task|task #)(\d+)'

        for msg in messages:
            content = msg.get("content", "")
            matches = re.findall(pattern, content, re.I)
            tasks.extend([f"#{m}" for m in matches])

        return list(dict.fromkeys(tasks))  # Remove duplicates while preserving order

    def _extract_errors(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract error messages"""
        errors = []

        for msg in messages:
            content = msg.get("content", "")
            if 'error' in content.lower() or 'failed' in content.lower():
                # Extract the error message
                error_match = re.search(r'error[:\s]+([^\n]+)', content, re.I)
                if error_match:
                    errors.append(error_match.group(1)[:100])

        return errors

    def _extract_outcomes(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract outcomes from messages"""
        outcomes = []

        for msg in messages:
            content = msg.get("content", "")
            if any(kw in content.lower() for kw in ["completed", "success", "passed", "done"]):
                # Find the outcome phrase
                match = re.search(r'(completed|success|passed)[:\s]+([^\n]+)', content, re.I)
                if match:
                    outcomes.append(match.group(2)[:50])

        return outcomes
