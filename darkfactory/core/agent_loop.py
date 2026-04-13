"""
Agent Loop - Main execution loop for task completion

The agent loop:
1. Receives a task with steps
2. For each step, sends context to LLM
3. LLM decides which tools to use
4. Executes tools and gets results
5. Continues until step is complete
6. Records results and moves to next step
"""

import asyncio
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from ..llm.client import LLMClient, Message, MessageRole, create_llm_client
from ..config import Config, LLMConfig
from ..tools.registry import ToolRegistry, get_registry
from ..tools.executor import ToolExecutor
from ..tools.results import ToolResult


@dataclass
class AgentStep:
    """A single step in agent execution"""
    step_number: int
    instruction: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    result: str = ""
    completed: bool = False
    error: Optional[str] = None


@dataclass
class AgentContext:
    """Context passed to LLM during agent execution"""
    task_id: str
    task_title: str
    workspace_path: Path
    config: Config
    steps: List[AgentStep] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    commands_executed: List[str] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)


class AgentLoop:
    """
    Agent Loop - Executes tasks using LLM + tools

    The agent receives a task, breaks it into steps,
    and iteratively calls the LLM with tool results until
    the step is complete.
    """

    # System prompt for the agent
    SYSTEM_PROMPT = """You are DarkFactory Agent, an AI coding assistant.

You execute tasks by calling tools. For each step:
1. Read the step instruction
2. Call appropriate tools to complete it
3. Report the result

Available tools:
{tool_descriptions}

Working directory: {workspace}

Guidelines:
- Always verify file existence after creation
- Use proper error handling
- Report progress clearly
- If stuck, try alternative approaches
"""

    def __init__(
        self,
        config: Config,
        workspace_path: Path,
        max_iterations_per_step: int = 10,
    ):
        self.config = config
        self.workspace_path = Path(workspace_path)
        self.max_iterations = max_iterations_per_step
        self.registry = get_registry()
        self.executor = ToolExecutor(self.registry)

        # Initialize LLM client
        self.llm: Optional[LLMClient] = None

    async def initialize(self) -> None:
        """Initialize LLM client"""
        if self.llm is None:
            self.llm = create_llm_client(self.config.llm)

    async def close(self) -> None:
        """Close LLM client"""
        if self.llm:
            await self.llm.close()
            self.llm = None

    async def execute_task(self, task_steps: List[str], task_id: str = "unknown") -> Dict[str, Any]:
        """
        Execute a task with multiple steps

        Args:
            task_steps: List of step instructions
            task_id: Task identifier

        Returns:
            Execution result with status and details
        """
        await self.initialize()

        context = AgentContext(
            task_id=task_id,
            task_title="",
            workspace_path=self.workspace_path,
            config=self.config,
        )

        results = []
        start_time = datetime.now()

        for i, step_instruction in enumerate(task_steps, 1):
            step_result = await self._execute_step(
                step_number=i,
                instruction=step_instruction,
                context=context,
            )
            results.append(step_result)

            if not step_result.completed and step_result.error:
                # Step failed, abort
                break

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return {
            "success": all(r.completed for r in results),
            "steps_completed": sum(1 for r in results if r.completed),
            "steps_total": len(task_steps),
            "duration_seconds": duration,
            "step_results": [
                {
                    "step": r.step_number,
                    "instruction": r.instruction,
                    "completed": r.completed,
                    "error": r.error,
                    "tool_calls": r.tool_calls,
                    "result": r.result,
                }
                for r in results
            ],
            "files_created": context.files_created,
            "commands_executed": context.commands_executed,
        }

    async def _execute_step(
        self,
        step_number: int,
        instruction: str,
        context: AgentContext,
    ) -> AgentStep:
        """Execute a single step"""
        step = AgentStep(
            step_number=step_number,
            instruction=instruction,
        )

        # Build messages for LLM
        messages = await self._build_step_messages(instruction, context, step)

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            # Call LLM
            try:
                response = await self.llm.chat(messages)
            except Exception as e:
                step.error = f"LLM error: {e}"
                return step

            # Parse tool calls from response
            tool_calls = self._parse_tool_calls(response.content)

            if not tool_calls:
                # No tool calls, step is complete
                step.completed = True
                step.result = response.content
                return step

            # Execute tool calls
            for tc in tool_calls:
                tool_name = tc.get("name")
                tool_args = tc.get("args", {})

                # Execute tool
                result = self.executor.execute(tool_name, kwargs=tool_args)

                step.tool_calls.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result.output if result.success else None,
                    "error": result.error.message if result.error else None,
                })

                # Track created files
                if tool_name == "write_file" and result.success:
                    path = tool_args.get("path", "")
                    if path:
                        context.files_created.append(str(path))

                # Track executed commands
                if tool_name == "execute_command":
                    cmd = tool_args.get("command", "")
                    if cmd:
                        context.commands_executed.append(cmd)

            # Add assistant response and tool results to messages
            messages.append(Message(role=MessageRole.ASSISTANT, content=response.content))

            # Add tool results as user message
            tool_result_text = self._format_tool_results(step.tool_calls[-len(tool_calls):])
            messages.append(Message(role=MessageRole.USER, content=tool_result_text))

        # Max iterations reached
        step.error = f"Max iterations ({self.max_iterations}) reached"
        return step

    async def _build_step_messages(
        self,
        instruction: str,
        context: AgentContext,
        step: AgentStep,
    ) -> List[Message]:
        """Build messages for a step"""
        # System message
        tool_descriptions = self._get_tool_descriptions()
        system = self.SYSTEM_PROMPT.format(
            tool_descriptions=tool_descriptions,
            workspace=str(context.workspace_path),
        )

        # Build context about what's already been done
        context_info = ""
        if step.step_number > 1:
            context_info = "\n\nPrevious steps completed:\n"
            for i, step_result in enumerate(context.steps, 1):
                context_info += f"Step {i}: {step_result}\n"

        # Current step instruction
        user_content = f"""{context_info}

Current step to execute:
Step {step.step_number}: {instruction}

Execute this step by calling the appropriate tools. Report when complete.
"""

        return [
            Message(role=MessageRole.SYSTEM, content=system),
            Message(role=MessageRole.USER, content=user_content),
        ]

    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Parse tool calls from LLM response"""
        tool_calls = []

        # Look for tool call blocks: <tool_call>...</tool_call>
        pattern = r'<tool_call>\s*<tool name="(\w+)"[^>]*>(.*?)</tool>\s*</tool_call>'
        matches = re.findall(pattern, content, re.DOTALL)

        for tool_name, args_str in matches:
            # Parse arguments from the args string
            args = self._parse_args(args_str)
            tool_calls.append({
                "name": tool_name,
                "args": args,
            })

        return tool_calls

    def _parse_args(self, args_str: str) -> Dict[str, Any]:
        """Parse tool arguments from XML-like string"""
        args = {}

        # Parse <arg_name>value</arg_name> pairs
        pattern = r'<(\w+)>(.*?)</\1>'
        matches = re.findall(pattern, args_str, re.DOTALL)

        for name, value in matches:
            # Try to parse as JSON, otherwise treat as string
            value = value.strip()
            try:
                args[name] = json.loads(value)
            except json.JSONDecodeError:
                args[name] = value

        return args

    def _format_tool_results(self, tool_calls: List[Dict[str, Any]]) -> str:
        """Format tool results for LLM"""
        lines = ["Tool execution results:"]

        for tc in tool_calls:
            lines.append(f"\n[{tc['tool']}]")
            if tc.get("error"):
                lines.append(f"ERROR: {tc['error']}")
            else:
                result = tc.get("result", "")
                if isinstance(result, dict):
                    result = json.dumps(result, indent=2)
                lines.append(f"Result: {result}")

        return "\n".join(lines)

    def _get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for system prompt"""
        tools = self.registry.list_tools()

        if not tools:
            return "No tools registered."

        lines = []
        for tool in tools:
            lines.append(f"- {tool.name}: {tool.description}")

        return "\n".join(lines)


# =============================================================================
# Built-in Tools
# =============================================================================

def register_builtin_tools() -> None:
    """Register built-in tools"""
    registry = get_registry()

    # Read file
    def read_file(path: str, **kwargs) -> str:
        """Read file contents"""
        file_path = Path(path)
        if not file_path.exists():
            return f"Error: File not found: {path}"
        try:
            return file_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

    # Write file
    def write_file(path: str, content: str, **kwargs) -> str:
        """Write content to file"""
        file_path = Path(path)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return f"File written: {path}"
        except Exception as e:
            return f"Error writing file: {e}"

    # Execute command
    def execute_command(command: str, cwd: Optional[str] = None, **kwargs) -> str:
        """Execute shell command"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = []
            if result.stdout:
                output.append(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                output.append(f"STDERR:\n{result.stderr}")
            if result.returncode != 0:
                output.append(f"Exit code: {result.returncode}")
            return "\n".join(output) or "Command completed (no output)"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error executing command: {e}"

    # List directory
    def list_directory(path: str = ".", **kwargs) -> str:
        """List directory contents"""
        dir_path = Path(path)
        if not dir_path.exists():
            return f"Error: Directory not found: {path}"
        if not dir_path.is_dir():
            return f"Error: Not a directory: {path}"

        try:
            items = []
            for item in sorted(dir_path.iterdir()):
                item_type = "DIR" if item.is_dir() else "FILE"
                items.append(f"{item_type}: {item.name}")
            return "\n".join(items) or "Directory is empty"
        except Exception as e:
            return f"Error listing directory: {e}"

    # Check file exists
    def file_exists(path: str, **kwargs) -> str:
        """Check if file exists"""
        exists = Path(path).exists()
        return f"{'Exists' if exists else 'Not found'}: {path}"

    # Create directory
    def create_directory(path: str, **kwargs) -> str:
        """Create directory"""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return f"Directory created: {path}"
        except Exception as e:
            return f"Error creating directory: {e}"

    # Register tools
    registry.register(
        "read_file",
        read_file,
        description="Read file contents",
        category="file",
    )

    registry.register(
        "write_file",
        write_file,
        description="Write content to file (creates or overwrites)",
        category="file",
    )

    registry.register(
        "execute_command",
        execute_command,
        description="Execute shell command and return output",
        category="execution",
    )

    registry.register(
        "list_directory",
        list_directory,
        description="List directory contents",
        category="file",
    )

    registry.register(
        "file_exists",
        file_exists,
        description="Check if file or directory exists",
        category="file",
    )

    registry.register(
        "create_directory",
        create_directory,
        description="Create a directory",
        category="file",
    )
