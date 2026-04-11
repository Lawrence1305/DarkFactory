"""
Context Compressor - Compress conversation context for LLM efficiency
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import re


class CompressionStrategy(Enum):
    """Strategy for compression"""
    TRUNCATE = "truncate"
    SUMMARIZE = "summarize"
    SELECTIVE = "selective"
    MIXED = "mixed"


@dataclass
class CompressionResult:
    """Result of compression operation"""
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    strategy: CompressionStrategy
    sections_kept: List[str]
    sections_removed: List[str]


class ContextCompressor:
    """
    Context Compressor

    Compresses conversation context to fit within LLM token limits.
    Uses mixed strategy: preserves important sections, summarizes rest.

    Based on hermes-agent's context compression approach.
    """

    # Token limits
    MAX_TOKENS = 128000  # Claude 100k context
    RESERVED_TOKENS = 2000  # Reserve for response
    TARGET_TOKENS = MAX_TOKENS - RESERVED_TOKENS

    # Importance scores for different content types
    CONTENT_PRIORITY = {
        "system": 100,
        "task": 90,
        "skill": 80,
        "memory": 70,
        "tool_result": 50,
        "user_message": 40,
        "assistant_message": 30,
    }

    def __init__(
        self,
        max_tokens: int = TARGET_TOKENS,
        strategy: CompressionStrategy = CompressionStrategy.MIXED,
    ):
        self.max_tokens = max_tokens
        self.strategy = strategy

    def compress(
        self,
        messages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], CompressionResult]:
        """
        Compress conversation messages

        Args:
            messages: List of conversation messages
            metadata: Optional metadata for context

        Returns:
            Tuple of (compressed messages, compression result)
        """
        original_tokens = self._estimate_tokens(messages)

        if original_tokens <= self.max_tokens:
            return messages, CompressionResult(
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                strategy=self.strategy,
                sections_kept=["all"],
                sections_removed=[],
            )

        if self.strategy == CompressionStrategy.TRUNCATE:
            return self._truncate(messages, original_tokens)
        elif self.strategy == CompressionStrategy.SUMMARIZE:
            return self._summarize(messages, metadata)
        elif self.strategy == CompressionStrategy.SELECTIVE:
            return self._selective(messages)
        else:
            return self._mixed(messages, metadata)

    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Estimate token count (rough approximation)"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += len(content) // 4  # Rough estimate: 4 chars per token
        return total

    def _truncate(
        self,
        messages: List[Dict[str, Any]],
        original_tokens: int,
    ) -> Tuple[List[Dict[str, Any]], CompressionResult]:
        """Truncate oldest messages"""
        compressed = []
        tokens = 0

        for msg in reversed(messages):
            msg_tokens = self._estimate_tokens([msg])
            if tokens + msg_tokens <= self.max_tokens:
                compressed.insert(0, msg)
                tokens += msg_tokens
            else:
                break

        removed = len(messages) - len(compressed)
        return compressed, CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=tokens,
            compression_ratio=tokens / original_tokens,
            strategy=self.strategy,
            sections_kept=[f"{len(compressed)} messages"],
            sections_removed=[f"{removed} messages truncated"],
        )

    def _summarize(
        self,
        messages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], CompressionResult]:
        """Summarize older messages into a context block"""
        # Keep recent messages intact
        recent_count = max(5, len(messages) // 4)
        recent = messages[-recent_count:]
        older = messages[:-recent_count]

        # Create summary of older messages
        summary = self._create_summary(older, metadata)

        compressed = recent.copy()
        compressed.insert(0, {
            "role": "system",
            "content": f"[Earlier context summarized]\n{summary}"
        })

        tokens = self._estimate_tokens(compressed)
        return compressed, CompressionResult(
            original_tokens=self._estimate_tokens(messages),
            compressed_tokens=tokens,
            compression_ratio=tokens / self._estimate_tokens(messages),
            strategy=self.strategy,
            sections_kept=["recent messages", "summary"],
            sections_removed=[f"{len(older)} messages summarized"],
        )

    def _create_summary(
        self,
        messages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        """Create a summary of older messages"""
        lines = [f"Summary of {len(messages)} earlier messages:"]

        # Extract key information
        tools_used = set()
        tasks_mentioned = []
        errors = []

        for msg in messages:
            content = msg.get("content", "")

            # Extract tool mentions
            tool_matches = re.findall(r'( инструмент| tool| using) (\w+)', content, re.I)
            for match in tool_matches:
                tools_used.add(match[1] if isinstance(match, tuple) else match)

            # Extract task mentions
            task_matches = re.findall(r'(task|task #)(\d+)', content, re.I)
            for match in task_matches:
                tasks_mentioned.append(match[1] if isinstance(match, tuple) else match)

            # Extract errors
            if 'error' in content.lower() or 'failed' in content.lower():
                errors.append(content[:100])

        if tools_used:
            lines.append(f"- Tools used: {', '.join(tools_used)}")
        if tasks_mentioned:
            lines.append(f"- Tasks discussed: {', '.join(set(tasks_mentioned))}")
        if errors:
            lines.append(f"- Errors encountered: {len(errors)}")
            lines.append(f"  Last error: {errors[-1][:80]}...")

        return "\n".join(lines)

    def _selective(
        self,
        messages: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], CompressionResult]:
        """Selectively keep important messages"""
        scored = []
        for i, msg in enumerate(messages):
            role = msg.get("role", "")
            content = msg.get("content", "")
            priority = self.CONTENT_PRIORITY.get(role, 50)

            # Boost priority for certain content
            if "task" in content.lower():
                priority += 10
            if "skill" in content.lower():
                priority += 15
            if "error" in content.lower() or "failed" in content.lower():
                priority += 20

            scored.append((i, msg, priority))

        # Sort by priority and keep top
        scored.sort(key=lambda x: -x[2])

        compressed = []
        tokens = 0
        kept_indices = set()

        for i, msg, priority in scored:
            msg_tokens = self._estimate_tokens([msg])
            if tokens + msg_tokens <= self.max_tokens:
                compressed.append(msg)
                tokens += msg_tokens
                kept_indices.add(i)

        # Re-sort to maintain order
        compressed.sort(key=lambda m: messages.index(m))

        return compressed, CompressionResult(
            original_tokens=self._estimate_tokens(messages),
            compressed_tokens=tokens,
            compression_ratio=tokens / self._estimate_tokens(messages),
            strategy=self.strategy,
            sections_kept=[f"{len(compressed)} selective messages"],
            sections_removed=[f"{len(messages) - len(compressed)} messages removed"],
        )

    def _mixed(
        self,
        messages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], CompressionResult]:
        """
        Mixed strategy: truncate older, summarize very old

        Keeps recent messages intact, summarizes very old ones.
        """
        # Keep last 50% intact
        keep_count = len(messages) // 2
        recent = messages[-keep_count:]
        older = messages[:-keep_count]

        # Summarize older
        summary = self._create_summary(older, metadata)

        compressed = recent.copy()
        compressed.insert(0, {
            "role": "system",
            "content": f"[Earlier context summarized]\n{summary}"
        })

        tokens = self._estimate_tokens(compressed)
        return compressed, CompressionResult(
            original_tokens=self._estimate_tokens(messages),
            compressed_tokens=tokens,
            compression_ratio=tokens / self._estimate_tokens(messages),
            strategy=self.strategy,
            sections_kept=["recent messages"],
            sections_removed=[f"{len(older)} messages summarized"],
        )
