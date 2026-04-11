"""
Workflow Engine - 6-step mandatory workflow execution
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from .task import Task, TaskStatus, TaskResult


class WorkflowStep(Enum):
    """Workflow steps"""
    INIT = "init"
    SELECT = "select"
    ANALYZE = "analyze"
    IMPLEMENT = "implement"
    VALIDATE = "validate"
    UPDATE = "update"
    COMMIT = "commit"


@dataclass
class WorkflowContext:
    """
    Workflow execution context - passed between steps
    """
    task: Optional[Task] = None
    current_step: WorkflowStep = WorkflowStep.INIT
    progress_data: Dict[str, Any] = field(default_factory=dict)
    tool_call_count: int = 0
    errors_encountered: List[str] = field(default_factory=list)
    attempts: int = 0
    validation_results: Dict[str, bool] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """Result of workflow execution"""
    success: bool
    output: Any = None
    errors: List[str] = field(default_factory=list)
    task_result: Optional[TaskResult] = None
    blocked: bool = False
    blocked_reason: Optional[str] = None


class Workflow:
    """
    6-Step Mandatory Workflow Engine

    Step 1: Initialize    → Run initialization scripts
    Step 2: Select Task   → Select passes=false + highest priority task
    Step 3: Analyze      → Call skills/knowledge graph for history
    Step 4: Implement    → Implement according to task.steps
    Step 5: Validate     → Layered testing (browser | lint | unit)
    Step 6: Record       → Update progress.txt + task.json + git commit

    Blocking handling:
    - If task cannot be completed (missing env config, external deps unavailable)
    - Immediately stop workflow
    - Write to progress.txt with current progress and blocking reason
    - Mark task as BLOCKED
    """

    STEP_HANDLERS: Dict[WorkflowStep, str] = {
        WorkflowStep.INIT: "_handle_init",
        WorkflowStep.SELECT: "_handle_select",
        WorkflowStep.ANALYZE: "_handle_analyze",
        WorkflowStep.IMPLEMENT: "_handle_implement",
        WorkflowStep.VALIDATE: "_handle_validate",
        WorkflowStep.UPDATE: "_handle_update",
        WorkflowStep.COMMIT: "_handle_commit",
    }

    def __init__(
        self,
        task_engine: Any,  # TaskEngine
        context_manager: Any,  # ContextManager
        validator: Any,  # Validator
        skill_loader: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
    ):
        self.task_engine = task_engine
        self.context_manager = context_manager
        self.validator = validator
        self.skill_loader = skill_loader
        self.memory_manager = memory_manager
        self._hooks: Dict[WorkflowStep, List[Callable]] = {
            step: [] for step in WorkflowStep
        }

    def register_hook(self, step: WorkflowStep, handler: Callable) -> None:
        """Register a hook to be called before/after a step"""
        if step not in self._hooks:
            self._hooks[step] = []
        self._hooks[step].append(handler)

    async def run(self, task: Task) -> WorkflowResult:
        """
        Execute the full workflow for a task

        Args:
            task: Task to execute

        Returns:
            WorkflowResult
        """
        ctx = WorkflowContext(
            task=task,
            start_time=datetime.now(),
        )

        # Step 1: Initialize
        ctx.current_step = WorkflowStep.INIT
        result = await self._execute_step(ctx)
        if not result.success:
            return result

        # Step 2: Select
        ctx.current_step = WorkflowStep.SELECT
        result = await self._execute_step(ctx)
        if not result.success:
            return result

        # Step 3: Analyze
        ctx.current_step = WorkflowStep.ANALYZE
        result = await self._execute_step(ctx)
        if not result.success:
            return result

        # Step 4: Implement
        ctx.current_step = WorkflowStep.IMPLEMENT
        result = await self._execute_step(ctx)
        if not result.success:
            return result

        # Step 5: Validate
        ctx.current_step = WorkflowStep.VALIDATE
        result = await self._execute_step(ctx)
        if not result.success:
            return result

        # Step 6: Update
        ctx.current_step = WorkflowStep.UPDATE
        result = await self._execute_step(ctx)
        if not result.success:
            return result

        # Step 7: Commit
        ctx.current_step = WorkflowStep.COMMIT
        result = await self._execute_step(ctx)

        ctx.end_time = datetime.now()

        return result

    async def _execute_step(self, ctx: WorkflowContext) -> WorkflowResult:
        """Execute a single step"""
        # Call pre-hook
        await self._call_hooks(ctx.current_step, "pre", ctx)

        # Get handler name
        handler_name = self.STEP_HANDLERS.get(ctx.current_step)
        if not handler_name:
            return WorkflowResult(success=True)

        # Get handler method
        handler = getattr(self, handler_name, None)
        if not handler:
            return WorkflowResult(success=True)

        # Execute handler
        try:
            result = await handler(ctx)
            return result
        except Exception as e:
            return WorkflowResult(
                success=False,
                errors=[str(e)],
            )
        finally:
            # Call post-hook
            await self._call_hooks(ctx.current_step, "post", ctx)

    async def _call_hooks(
        self,
        step: WorkflowStep,
        phase: str,  # "pre" or "post"
        ctx: WorkflowContext,
    ) -> None:
        """Call registered hooks"""
        hooks = self._hooks.get(step, [])
        for hook in hooks:
            try:
                if phase == "pre":
                    await hook(ctx, is_pre=True)
                else:
                    await hook(ctx, is_pre=False)
            except Exception:
                pass  # Don't let hooks break workflow

    async def _handle_init(self, ctx: WorkflowContext) -> WorkflowResult:
        """Initialize step - verify environment is ready"""
        # Verify workspace exists
        # Verify dependencies are installed
        # Verify git repo is clean or has meaningful status
        return WorkflowResult(success=True)

    async def _handle_select(self, ctx: WorkflowContext) -> WorkflowResult:
        """Select step - confirm task selection"""
        if ctx.task:
            return WorkflowResult(success=True)

        # Select next task
        next_task = self.task_engine.select_next_task()
        if not next_task:
            return WorkflowResult(
                success=False,
                blocked=True,
                blocked_reason="No tasks available to execute",
            )

        ctx.task = next_task
        ctx.task.status = TaskStatus.IN_PROGRESS
        self.task_engine.update_task_status(
            next_task.id,
            TaskStatus.IN_PROGRESS,
        )

        return WorkflowResult(success=True)

    async def _handle_analyze(self, ctx: WorkflowContext) -> WorkflowResult:
        """Analyze step - load relevant skills and memory"""
        if not ctx.task:
            return WorkflowResult(success=False, errors=["No task selected"])

        # Load relevant skills
        if self.skill_loader:
            skills = self.skill_loader.find_relevant_skills(ctx.task)
            ctx.metadata["relevant_skills"] = skills

        # Load relevant memory
        if self.memory_manager:
            memory_context = self.memory_manager.wake_up(wing=ctx.task.id)
            ctx.metadata["memory_context"] = memory_context

        # Check knowledge graph
        # kg_query for related entities

        return WorkflowResult(success=True)

    async def _handle_implement(self, ctx: WorkflowContext) -> WorkflowResult:
        """Implement step - execute task steps"""
        if not ctx.task:
            return WorkflowResult(success=False, errors=["No task selected"])

        # In a full implementation, this would:
        # 1. Use LLM to generate code for each step
        # 2. Track tool call count
        # 3. Handle errors and retries
        # 4. Update progress

        ctx.attempts += 1

        return WorkflowResult(success=True)

    async def _handle_validate(self, ctx: WorkflowContext) -> WorkflowResult:
        """Validate step - run appropriate tests"""
        if not ctx.task:
            return WorkflowResult(success=False, errors=["No task selected"])

        # Run validation based on test_strategy
        validation_result = await self.validator.validate(ctx.task)

        ctx.validation_results = {
            "passed": validation_result.passed,
            "level": validation_result.level.value,
        }

        if not validation_result.passed:
            return WorkflowResult(
                success=False,
                errors=[validation_result.message],
            )

        return WorkflowResult(success=True)

    async def _handle_update(self, ctx: WorkflowContext) -> WorkflowResult:
        """Update step - record progress"""
        if not ctx.task:
            return WorkflowResult(success=False, errors=["No task selected"])

        # Update task status
        self.task_engine.update_task_status(
            ctx.task.id,
            TaskStatus.COMPLETED,
        )

        # Record result
        duration = 0.0
        if ctx.start_time and ctx.end_time:
            duration = (ctx.end_time - ctx.start_time).total_seconds()

        task_result = TaskResult(
            task_id=ctx.task.id,
            success=True,
            tool_call_count=ctx.tool_call_count,
            attempts=ctx.attempts,
            duration_seconds=duration,
            validation_results=ctx.validation_results,
        )

        self.task_engine.record_result(task_result)

        return WorkflowResult(
            success=True,
            task_result=task_result,
        )

    async def _handle_commit(self, ctx: WorkflowContext) -> WorkflowResult:
        """Commit step - git commit"""
        # In a full implementation:
        # 1. git add .
        # 2. git commit -m "task title - completed"
        return WorkflowResult(success=True)

    def handle_blocking(
        self,
        ctx: WorkflowContext,
        reason: str,
        required_actions: List[str],
    ) -> WorkflowResult:
        """
        Handle blocking situation

        Write to progress.txt, mark task as BLOCKED
        """
        if ctx.task:
            self.task_engine.update_task_status(
                ctx.task.id,
                TaskStatus.BLOCKED,
                blocked_reason=reason,
            )

        # Write blocking info to progress.txt
        self._write_blocking_progress(ctx, reason, required_actions)

        return WorkflowResult(
            success=False,
            blocked=True,
            blocked_reason=reason,
            errors=[f"Task blocked: {reason}"],
        )

    def _write_blocking_progress(
        self,
        ctx: WorkflowContext,
        reason: str,
        required_actions: List[str],
    ) -> None:
        """Write blocking information to progress.txt"""
        progress_path = self.task_engine.workspace_path / "progress.txt"

        lines = [
            f"## BLOCKED - {datetime.now().isoformat()}",
            f"**Task**: {ctx.task.title if ctx.task else 'Unknown'}",
            "",
            "### Completed Work:",
        ]

        if ctx.progress_data:
            for key, value in ctx.progress_data.items():
                lines.append(f"- {key}: {value}")

        lines.extend([
            "",
            "### Blocking Reason:",
            f"- {reason}",
            "",
            "### Required Actions:",
        ])

        for i, action in enumerate(required_actions, 1):
            lines.append(f"{i}. {action}")

        lines.append("")
        lines.append("---")

        with open(progress_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
