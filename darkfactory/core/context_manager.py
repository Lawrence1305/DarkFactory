"""
Context Manager - manages multi-layer context and compression
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from .task import Task


@dataclass
class ContextSlice:
    """
    Context slice - a single piece of context
    """
    role: str  # system, user, assistant, tool
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """
    Context Manager

    Responsibilities:
    1. Manage multi-layer context (system, memory, conversation)
    2. Detect context bloat
    3. Trigger compression flow
    4. Provide memory retrieval

    Based on hermes-agent's context compressor:
    - Protect head (system + first 3 turns)
    - Protect tail (~20K tokens)
    - Summarize middle turns
    """

    # Context thresholds
    DEFAULT_THRESHOLD_PERCENT = 0.50  # Compress when at 50% of max
    DEFAULT_MAX_TOKENS = 200_000

    # Protection settings
    PROTECT_FIRST_N = 3  # Protect first 3 turns
    PROTECT_LAST_TOKENS = 20_000  # Protect last 20K tokens

    # Summary settings
    SUMMARY_TARGET_RATIO = 0.20  # Target 20% of original size
    SUMMARY_TOKENS_CEILING = 12_000
    MIN_SUMMARY_TOKENS = 2_000

    def __init__(
        self,
        memory_stack: Optional[Any] = None,  # MemoryStack from memory module
        compressor: Optional[Any] = None,  # ContextCompressor
        token_counter: Optional[Any] = None,  # Token counter
        max_tokens: int = DEFAULT_MAX_TOKENS,
        threshold_percent: float = DEFAULT_THRESHOLD_PERCENT,
    ):
        self.memory_stack = memory_stack
        self.compressor = compressor
        self.token_counter = token_counter
        self.max_tokens = max_tokens
        self.threshold_percent = threshold_percent

        self._contexts: List[ContextSlice] = []
        self._compaction_count = 0
        self._previous_summary: Optional[str] = None

    def build_system_prompt(self) -> str:
        """
        Build system prompt - combining L0 + L1 memory

        L0: Identity (~50 tokens) - always loaded
        L1: Essential Facts (~120 tokens) - always loaded
        """
        if self.memory_stack:
            return self.memory_stack.wake_up()

        return ""

    def add_context(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Add a context slice"""
        slice = ContextSlice(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self._contexts.append(slice)

    def should_compress(self, prompt_tokens: Optional[int] = None) -> bool:
        """
        Check if compression is needed

        Args:
            prompt_tokens: Current token count (if known)

        Returns:
            True if compression should be triggered
        """
        if prompt_tokens is None:
            prompt_tokens = self._estimate_tokens()

        threshold = int(self.max_tokens * self.threshold_percent)
        return prompt_tokens >= threshold

    def compress(self) -> List[ContextSlice]:
        """
        Compress context

        Algorithm:
        1. Prune old tool results (no LLM call)
        2. Protect head messages (system + first 3 turns)
        3. Protect tail messages (~20K tokens)
        4. Summarize middle turns with LLM
        5. Iteratively update summary
        """
        if not self._contexts:
            return []

        # Phase 1: Prune old tool results
        pruned_contexts = self._prune_old_tool_results(self._contexts)

        # Phase 2: Find boundaries
        head_end = self._find_head_end(pruned_contexts)
        tail_start = self._find_tail_start(pruned_contexts)

        if head_end >= tail_start:
            return pruned_contexts

        # Phase 3: Generate summary
        middle_slices = pruned_contexts[head_end:tail_start]
        summary = self._generate_summary(middle_slices)

        # Phase 4: Assemble compressed context
        compressed = []
        compressed.extend(pruned_contexts[:head_end])

        if summary:
            compressed.append(ContextSlice(
                role="system",
                content=f"[CONTEXT COMPACTION] Earlier turns summarized:\n\n{summary}",
                metadata={"is_compacted": True},
            ))
        else:
            # Summary failed, add marker
            compressed.append(ContextSlice(
                role="user",
                content=f"[CONTEXT COMPACTION] {len(middle_slices)} turns removed without summary.",
            ))

        compressed.extend(pruned_contexts[tail_start:])

        # Phase 5: Sanitize tool pairs
        compressed = self._sanitize_tool_pairs(compressed)

        self._contexts = compressed
        self._compaction_count += 1

        return compressed

    def _prune_old_tool_results(
        self,
        contexts: List[ContextSlice],
        protect_tail_tokens: int = 5_000,
    ) -> List[ContextSlice]:
        """
        Prune old tool results without LLM calls

        Replace long results with placeholders to save tokens
        """
        # Simple implementation - just return as-is for now
        # In full implementation, would:
        # 1. Find tool_result messages
        # 2. Check if preceded by tool_call with LLM
        # 3. Replace long ones with placeholders
        return contexts

    def _find_head_end(self, contexts: List[ContextSlice]) -> int:
        """
        Find the end of protected head

        Protect: system messages + first PROTECT_FIRST_N turns
        """
        count = 0
        for i, ctx in enumerate(contexts):
            if ctx.role == "system":
                continue
            count += 1
            if count > self.PROTECT_FIRST_N:
                return i
        return len(contexts)

    def _find_tail_start(self, contexts: List[ContextSlice]) -> int:
        """
        Find the start of protected tail

        Protect: approximately PROTECT_LAST_TOKENS worth of recent messages
        """
        total_tokens = sum(self._estimate_slice_tokens(c) for c in contexts)
        target_tokens = total_tokens - self.PROTECT_LAST_TOKENS

        if target_tokens <= 0:
            return 0

        accumulated = 0
        for i, ctx in enumerate(reversed(contexts)):
            accumulated += self._estimate_slice_tokens(ctx)
            if accumulated >= target_tokens:
                return len(contexts) - i
        return 0

    def _generate_summary(self, slices: List[ContextSlice]) -> Optional[str]:
        """
        Generate structured summary of middle turns

        Template:
        ## Goal
        ## Constraints & Preferences
        ## Progress
        ### Done
        ### In Progress
        ### Blocked
        ## Key Decisions
        ## Relevant Files
        ## Next Steps
        ## Critical Context
        ## Tools & Patterns
        """
        if not slices:
            return None

        if self.compressor:
            return self.compressor.summarize(slices, self._previous_summary)

        # Fallback: simple concatenation
        if self._previous_summary:
            return f"(Previous summary + {len(slices)} new turns)"

        return f"Summary of {len(slices)} turns"

    def _sanitize_tool_pairs(
        self,
        contexts: List[ContextSlice],
    ) -> List[ContextSlice]:
        """
        Fix orphaned tool_call / tool_result pairs

        Problems:
        1. tool_result references a deleted assistant tool_call
        2. assistant message has tool_calls but result was deleted

        Fix:
        1. Delete orphaned tool results
        2. Insert stub results for orphaned tool calls
        """
        # Simple implementation - just return as-is
        return contexts

    def _estimate_tokens(self) -> int:
        """Estimate total tokens in context"""
        return sum(self._estimate_slice_tokens(c) for c in self._contexts)

    def _estimate_slice_tokens(self, slice: ContextSlice) -> int:
        """Estimate tokens in a single slice"""
        # Rough estimate: 4 chars per token
        return len(slice.content) // 4

    def get_context_for_llm(self) -> List[Dict[str, str]]:
        """Get context in format for LLM API"""
        return [
            {"role": c.role, "content": c.content}
            for c in self._contexts
        ]

    def recall_memory(
        self,
        query: str,
        wing: Optional[str] = None,
        room: Optional[str] = None,
    ) -> str:
        """
        Retrieve memory - L2 on-demand recall

        From Palace's wing/room retrieve relevant memories
        """
        if self.memory_stack:
            return self.memory_stack.recall(wing=wing, room=room, n_results=10)
        return ""

    def search_memory(
        self,
        query: str,
        n_results: int = 5,
    ) -> str:
        """
        Deep search memory - L3

        Semantic search across entire Palace
        """
        if self.memory_stack:
            return self.memory_stack.search(query, n_results=n_results)
        return ""

    def clear_context(self) -> None:
        """Clear context - for new task start"""
        self._contexts = []
        self._previous_summary = None
        self._compaction_count = 0

    def get_compaction_count(self) -> int:
        """Get number of times context was compacted"""
        return self._compaction_count

    def get_context_stats(self) -> Dict[str, Any]:
        """Get context statistics"""
        return {
            "slice_count": len(self._contexts),
            "estimated_tokens": self._estimate_tokens(),
            "max_tokens": self.max_tokens,
            "compaction_count": self._compaction_count,
        }
