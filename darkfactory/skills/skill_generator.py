"""
Skill Generator - Generate skills from experience
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .skill import Skill
from .skill_store import SkillStore


@dataclass
class SkillTrigger:
    """Skill trigger configuration"""
    type: str  # "complex_task", "error_recovery", "user_correction", "pattern_match"
    min_tool_calls: int = 5
    error_patterns: List[str] = field(default_factory=list)
    success_patterns: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskContext:
    """Context from a task execution"""
    task_id: str
    task_title: str
    task_description: str
    steps: List[str]
    tool_call_count: int
    errors: List[str]
    attempts: int
    duration_seconds: float
    conversation_logs: Optional[str] = None
    skills_used: List[str] = field(default_factory=list)
    validation_passed: bool = True


class SkillGenerator:
    """
    Skill Generator - Creates skills from experience

    Based on hermes-agent's self-improvement mechanism.

    Trigger conditions:
    1. Complex task (tool calls >= 5)
    2. Error recovery (overcame a tricky error)
    3. User correction (user effectively corrected agent)
    4. Repeated pattern (same operation succeeded multiple times)

    Generation flow:
    1. Analyze task execution
    2. Detect trigger conditions
    3. Generate skill via LLM
    4. Store skill
    """

    # Trigger detection thresholds
    TRIGGERS = {
        "complex_task": {
            "condition": "tool_call_count >= 5",
            "weight": 1.0,
        },
        "error_recovery": {
            "condition": "errors > 0 AND validation_passed == True",
            "weight": 1.5,  # Higher weight for error recovery
        },
        "user_correction": {
            "condition": "user_corrections > 0",
            "weight": 2.0,  # Highest weight
        },
        "repeated_pattern": {
            "condition": "same_operation_count >= 3",
            "weight": 0.8,
        },
    }

    GENERATION_PROMPT_TEMPLATE = """
# Skill Generation Task

Analyze the following task execution and generate a reusable skill.

## Task Information
- Task ID: {task_id}
- Title: {task_title}
- Description: {task_description}
- Steps: {steps}
- Tool Calls: {tool_call_count}
- Errors: {errors}
- Attempts: {attempts}
- Duration: {duration_seconds}s
- Skills Used: {skills_used}
- Validation: {validation_passed}

## Conversation Logs (if available)
{conversation_logs}

## Generation Requirements

Generate a skill definition with the following structure:

1. **name**: Skill name in kebab-case (e.g., "nextjs-auth-setup")
2. **description**: Brief description (1-2 sentences)
3. **trigger**: When to use this skill
   - type: complex_task | error_recovery | pattern_match
   - conditions: Specific conditions that trigger this skill
4. **steps**: Ordered execution steps (3-7 steps)
5. **pitfalls**: Known traps to avoid (2-5 items)
6. **verification**: How to verify success
7. **examples**: Usage examples (optional)

Output format: JSON object with these fields.
"""

    def __init__(
        self,
        skill_store: SkillStore,
        llm_client: Optional[Any] = None,  # LLM client for generation
    ):
        self.skill_store = skill_store
        self.llm_client = llm_client

    def should_create_skill(self, context: TaskContext) -> bool:
        """
        Determine if a skill should be created

        Args:
            context: Task execution context

        Returns:
            True if trigger conditions are met
        """
        # Complex task
        if context.tool_call_count >= 5:
            return True

        # Error recovery (克服了棘手错误)
        if len(context.errors) > 0 and context.validation_passed:
            return True

        # Multiple attempts
        if context.attempts > 1:
            return True

        return False

    def detect_trigger_type(self, context: TaskContext) -> Optional[str]:
        """
        Detect which trigger type applies

        Args:
            context: Task execution context

        Returns:
            Trigger type or None
        """
        triggers_met = []

        if context.tool_call_count >= 5:
            triggers_met.append("complex_task")

        if len(context.errors) > 0 and context.validation_passed:
            triggers_met.append("error_recovery")

        if context.attempts > 1:
            triggers_met.append("repeated_pattern")

        # Return highest priority trigger
        priority = ["user_correction", "error_recovery", "complex_task", "repeated_pattern"]
        for trigger in priority:
            if trigger in triggers_met:
                return trigger

        return None

    async def generate_from_task(
        self,
        context: TaskContext,
    ) -> Optional[Skill]:
        """
        Generate a skill from task execution

        Args:
            context: Task execution context

        Returns:
            Generated Skill or None
        """
        if not self.should_create_skill(context):
            return None

        trigger_type = self.detect_trigger_type(context)

        # Build prompt
        prompt = self.GENERATION_PROMPT_TEMPLATE.format(
            task_id=context.task_id,
            task_title=context.task_title,
            task_description=context.task_description,
            steps=json.dumps(context.steps, ensure_ascii=False),
            tool_call_count=context.tool_call_count,
            errors=json.dumps(context.errors, ensure_ascii=False),
            attempts=context.attempts,
            duration_seconds=context.duration_seconds,
            skills_used=json.dumps(context.skills_used),
            validation_passed=context.validation_passed,
            conversation_logs=context.conversation_logs or "Not available",
        )

        # Generate via LLM if available
        if self.llm_client:
            response = await self._call_llm(prompt)
            return self._parse_skill_response(response, context)
        else:
            # Fallback: simple skill generation
            return self._generate_simple_skill(context)

    def _generate_simple_skill(self, context: TaskContext) -> Skill:
        """
        Generate a simple skill without LLM

        Used as fallback when LLM is not available.
        """
        # Create skill name from task title
        name = context.task_title.lower().replace(" ", "-")[:30]

        # Determine skill type
        skill_type = "general"
        if any(kw in context.task_title.lower() for kw in ["test", "验证"]):
            skill_type = "testing"
        elif any(kw in context.task_title.lower() for kw in ["debug", "bug", "修复"]):
            skill_type = "debugging"
        elif any(kw in context.task_title.lower() for kw in ["auth", "登录", "注册"]):
            skill_type = "security"

        # Extract pitfalls from errors
        pitfalls = [f"Error: {e}" for e in context.errors[:3]]

        # Build verification from steps
        verification = {}
        if context.validation_passed:
            verification["success"] = "All steps completed without errors"
        else:
            verification["check"] = "Verify all steps completed"

        skill = Skill(
            name=name,
            description=f"Skill for: {context.task_title}",
            trigger={
                "type": self.detect_trigger_type(context) or "complex_task",
                "conditions": {
                    "tool_call_count": context.tool_call_count,
                },
            },
            steps=context.steps[:5],  # Limit steps
            pitfalls=pitfalls,
            verification=verification,
            source_task_id=context.task_id,
            skill_type=skill_type,
        )

        return skill

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM for skill generation"""
        # This would call the configured LLM client
        # For now, return empty to use simple generation
        return ""

    def _parse_skill_response(
        self,
        response: str,
        context: TaskContext,
    ) -> Optional[Skill]:
        """Parse LLM response into Skill"""
        try:
            # Try to parse JSON
            data = json.loads(response)

            skill = Skill(
                name=data["name"],
                description=data.get("description", ""),
                trigger=data.get("trigger", {}),
                steps=data.get("steps", []),
                pitfalls=data.get("pitfalls", []),
                verification=data.get("verification", {}),
                examples=data.get("examples", []),
                source_task_id=context.task_id,
                skill_type=data.get("type", "general"),
            )

            return skill

        except (json.JSONDecodeError, KeyError):
            # Fall back to simple generation
            return self._generate_simple_skill(context)

    def create_skill_from_error(
        self,
        error: str,
        recovery_steps: List[str],
        context: str,
    ) -> Skill:
        """
        Create skill from error recovery

        Args:
            error: Error description
            recovery_steps: How it was resolved
            context: Context where error occurred

        Returns:
            Generated Skill
        """
        name = f"error-recovery-{error[:20].lower().replace(' ', '-')}"

        skill = Skill(
            name=name,
            description=f"Recovery skill for: {error}",
            trigger={
                "type": "error_recovery",
                "conditions": {
                    "error_pattern": error,
                },
            },
            steps=recovery_steps,
            pitfalls=[f"Original error: {error}"],
            verification={
                "success": "Error no longer occurs",
                "verify": "Run the same operation that caused the error",
            },
            skill_type="debugging",
        )

        return skill

    def store_generated_skill(self, skill: Skill) -> None:
        """Store a generated skill"""
        self.skill_store.store_skill(skill)


class TriggerDetector:
    """
    Skill Trigger Detector

    Monitors task execution and detects when skill creation should be triggered.
    """

    def __init__(self):
        self._operation_counts: Dict[str, int] = {}

    def record_operation(self, operation: str) -> None:
        """Record an operation for pattern detection"""
        self._operation_counts[operation] = self._operation_counts.get(operation, 0) + 1

    def get_repeated_operations(self, threshold: int = 3) -> List[str]:
        """Get operations that exceeded the threshold"""
        return [
            op for op, count in self._operation_counts.items()
            if count >= threshold
        ]

    def reset_counts(self) -> None:
        """Reset operation counts"""
        self._operation_counts.clear()
