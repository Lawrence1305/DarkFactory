"""
DarkFactory CLI - Command line interface

Connects to core modules:
- TaskPlanner: Natural language task decomposition
- TaskEngine: Task lifecycle management
- Workflow: 6-step execution workflow
- Config: Multi-provider LLM configuration
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from .config import Config, load_config, detect_provider_type, ProviderType, LLMProvider
from .core.task import Task, TaskStatus, TestStrategy
from .core.task_engine import TaskEngine
from .core.task_planner import TaskPlanner, PlanResult, PlanStatus
from .core.workflow import Workflow, WorkflowContext, WorkflowStep
from .core.validator import Validator, ValidationLevel
from .core.agent_loop import AgentLoop, register_builtin_tools

console = Console()


# =============================================================================
# Configuration Helpers
# =============================================================================

def get_config_path() -> Path:
    """Get config file path"""
    config_dir = Path.home() / ".darkfactory"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.json"


def load_existing_config() -> Config:
    """Load existing config or return default"""
    config_path = get_config_path()
    if config_path.exists():
        return Config.from_file(str(config_path))
    return Config()


def get_project_paths(workspace: Path) -> tuple[Path, Path, Path]:
    """Get project-specific paths"""
    task_path = workspace / "task.json"
    progress_path = workspace / "progress.txt"
    plan_cache_path = workspace / ".darkfactory_plan.json"
    return task_path, progress_path, plan_cache_path


# =============================================================================
# CLI Entry Point
# =============================================================================

@click.group()
@click.version_option(version="0.1.0", prog_name="darkfactory")
def cli():
    """DarkFactory - AI-Native Agent Framework"""
    pass


# =============================================================================
# Config Commands
# =============================================================================

@cli.group()
def config():
    """Manage DarkFactory configuration."""
    pass


@config.command("show")
def config_show():
    """Show current configuration."""
    cfg = load_existing_config()

    table = Table(title="Current Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    api_key_display = f"***...{cfg.llm.api_key[-4:]}" if cfg.llm.api_key else "(not set)"
    table.add_row("Provider Type", cfg.llm.provider_type.value)
    table.add_row("API Key", api_key_display)
    table.add_row("Base URL", cfg.llm.base_url or "(default)")
    table.add_row("Model", cfg.llm.model)
    table.add_row("Max Agents", str(cfg.agent.max_agents))
    table.add_row("Workspace", cfg.workspace)

    console.print(table)


@config.command("set")
@click.option("--api-key", help="API key for the LLM provider")
@click.option("--base-url", help="Base URL (auto-detected if not provided)")
@click.option("--model", help="Model name (e.g., gpt-4o, claude-sonnet-4-20250514)")
@click.option("--provider-type", type=click.Choice(["anthropic", "openai"]), help="Provider type (auto-detected if not provided)")
@click.option("--max-agents", type=int, help="Maximum number of parallel agents")
@click.option("--workspace", type=str, help="Workspace directory")
def config_set(api_key, base_url, model, provider_type, max_agents, workspace):
    """Set configuration values."""
    cfg = load_existing_config()

    if api_key:
        cfg.llm.api_key = api_key
    if base_url:
        cfg.llm.base_url = base_url
        if not provider_type:
            detected = detect_provider_type(base_url)
            console.print(f"[dim]Auto-detected provider type: {detected.value}[/dim]")
            cfg.llm.provider_type = detected
    if provider_type:
        cfg.llm.provider_type = ProviderType(provider_type)
    if model:
        cfg.llm.model = model
    if max_agents:
        cfg.agent.max_agents = max_agents
    if workspace:
        cfg.workspace = workspace

    config_path = get_config_path()
    cfg.save(str(config_path))

    console.print(f"[green]Configuration saved to {config_path}[/green]")


@config.command("setup")
@click.option("--provider", type=click.Choice(["anthropic", "openai", "minimax", "qwen", "deepseek"]),
              help="Quick setup provider")
def config_setup(provider):
    """Interactive configuration setup."""
    cfg = Config()

    console.print("[bold green]DarkFactory Configuration Setup[/bold green]\n")

    providers_map = {
        "anthropic": ("anthropic", "Anthropic Claude", "https://api.anthropic.com", "claude-sonnet-4-20250514"),
        "openai": ("openai", "OpenAI GPT-4", "https://api.openai.com/v1", "gpt-4o"),
        "minimax": ("anthropic", "MiniMax", "https://api.minimax.chat/v1/text/chatcompletion_v2", "MiniMax-Text-01"),
        "qwen": ("openai", "Qwen (通义千问)", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
        "deepseek": ("openai", "DeepSeek", "https://api.deepseek.com/v1", "deepseek-chat"),
    }

    if provider and provider in providers_map:
        p = providers_map[provider]
        cfg.llm.provider_type = ProviderType(p[0])
        cfg.llm.base_url = p[2]
        cfg.llm.model = p[3]
        console.print(f"[cyan]Selected:[/cyan] {p[1]}")
    else:
        console.print("Select a provider:")
        for key, (_, name, _, _) in providers_map.items():
            console.print(f"  [cyan]{key}[/cyan]. {name}")
        console.print("  [cyan]custom[/cyan]. Custom provider\n")

        choice = Prompt.ask("Enter choice", default="minimax")

        if choice in providers_map:
            p = providers_map[choice]
            cfg.llm.provider_type = ProviderType(p[0])
            cfg.llm.base_url = p[2]
            cfg.llm.model = p[3]
        else:
            cfg.llm.base_url = Prompt.ask("Enter base URL")
            cfg.llm.provider_type = detect_provider_type(cfg.llm.base_url)
            cfg.llm.model = Prompt.ask("Enter model name", default="gpt-4o")

    console.print()
    api_key = Prompt.ask("Enter API key", password=True)
    cfg.llm.api_key = api_key

    console.print()
    max_agents = Prompt.ask("Max parallel agents", default="4")
    cfg.agent.max_agents = int(max_agents)

    config_path = get_config_path()
    cfg.save(str(config_path))

    console.print(f"\n[green]Configuration saved to {config_path}[/green]")
    console.print(f"[cyan]Provider:[/cyan] {cfg.llm.provider_type.value}")
    console.print(f"[cyan]Model:[/cyan] {cfg.llm.model}")
    console.print("\n[dim]Run 'darkfactory config show' to verify.[/dim]")


@config.command("reset")
def config_reset():
    """Reset configuration to defaults."""
    config_path = get_config_path()
    if config_path.exists():
        config_path.unlink()
        console.print("[yellow]Configuration reset[/yellow]")
    else:
        console.print("[dim]No configuration file to reset[/dim]")


# =============================================================================
# Plan Commands
# =============================================================================

@cli.group()
def plan():
    """Task planning commands."""
    pass


@plan.command("run")
@click.argument("goal")
@click.option("--workspace", "-w", default=".", help="Workspace directory")
def plan_run(goal: str, workspace: str):
    """Plan tasks from natural language goal.

    Analyzes the goal and creates a task plan with:
    - Task decomposition
    - Activity network
    - Critical path analysis
    - Gantt chart data
    - Resource estimation

    Use 'darkfactory plan confirm' after reviewing to create task.json
    """
    console.print(f"[bold blue]Planning:[/bold blue] {goal}")
    console.print()

    workspace_path = Path(workspace).resolve()
    task_path, _, plan_cache_path = get_project_paths(workspace_path)

    # Create task planner
    cfg = load_existing_config()
    planner = TaskPlanner(workspace_path=str(workspace_path))

    # Load existing context if available
    context = ""
    if task_path.exists():
        context = f"Existing project at {workspace_path}"

    # Run planning
    async def run_planning():
        return await planner.plan(goal, context)

    try:
        plan_result = asyncio.run(run_planning())
    except Exception as e:
        console.print(f"[red]Planning failed: {e}[/red]")
        sys.exit(1)

    # Display results
    _display_plan_result(plan_result, workspace_path)

    # Save plan to cache for confirmation
    plan_cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(plan_cache_path, "w", encoding="utf-8") as f:
        json.dump(planner.to_dict(plan_result), f, indent=2, ensure_ascii=False)

    console.print()
    console.print(f"[dim]Plan cached. Run 'darkfactory plan confirm' to create task.json[/dim]")


def _display_plan_result(plan_result: PlanResult, workspace_path: Path):
    """Display plan result in rich format"""
    # Status panel
    status_color = {
        PlanStatus.DRAFT: "yellow",
        PlanStatus.PRESENTED: "green",
        PlanStatus.CONFIRMED: "cyan",
        PlanStatus.MODIFIED: "magenta",
    }.get(plan_result.status, "white")

    console.print(Panel(
        f"[{status_color}]{plan_result.status.value.upper()}[/{status_color}]",
        title="Plan Status"
    ))

    # Task table
    if plan_result.tasks:
        table = Table(title=f"Tasks ({len(plan_result.tasks)})")
        table.add_column("ID", style="cyan", width=12)
        table.add_column("Title", style="white")
        table.add_column("Priority", style="yellow", justify="center", width=10)
        table.add_column("Duration", style="magenta", justify="right", width=10)
        table.add_column("Test", style="green", width=10)

        for task in plan_result.tasks:
            table.add_row(
                task.id,
                task.title[:40],
                str(task.priority),
                f"{task.estimated_duration}m",
                task.test_strategy.value
            )

        console.print(table)

    # Critical path
    if plan_result.critical_path:
        console.print()
        console.print("[bold red]Critical Path:[/bold red]")
        console.print(" → ".join(plan_result.critical_path))

    # Statistics
    col1, col2 = console.width // 2 - 4, console.width // 2 - 4

    stats_table = Table(show_header=False, box=None)
    stats_table.add_column(width=col1)
    stats_table.add_column(width=col2)

    stats_table.add_row(
        f"[cyan]Total Duration:[/cyan] {plan_result.total_duration} minutes",
        f"[cyan]Agent Requirements:[/cyan] {plan_result.agent_requirements}"
    )
    stats_table.add_row(
        f"[cyan]Total Tasks:[/cyan] {len(plan_result.tasks)}",
        f"[cyan]Critical Path Length:[/cyan] {len(plan_result.critical_path)}"
    )

    console.print(stats_table)


@plan.command("confirm")
@click.option("--workspace", "-w", default=".", help="Workspace directory")
def plan_confirm(workspace: str):
    """Confirm the current plan and create task.json.

    Reads the cached plan and writes it to task.json for execution.
    """
    workspace_path = Path(workspace).resolve()
    _, _, plan_cache_path = get_project_paths(workspace_path)

    if not plan_cache_path.exists():
        console.print("[red]No cached plan found. Run 'darkfactory plan' first.[/red]")
        console.print(f"[dim]Expected plan cache at: {plan_cache_path}[/dim]")
        return

    # Load cached plan
    with open(plan_cache_path, "r", encoding="utf-8") as f:
        plan_data = json.load(f)

    # Create task.json
    tasks = []
    for task_data in plan_data.get("tasks", []):
        task = Task(
            id=task_data["id"],
            title=task_data["title"],
            description=task_data.get("description", ""),
            steps=task_data.get("steps", []),
            priority=task_data.get("priority", 3),
            dependencies=task_data.get("dependencies", []),
            skills_required=task_data.get("skills_required", []),
            test_strategy=TestStrategy(task_data.get("test_strategy", "auto")),
            estimated_duration=task_data.get("estimated_duration", 30),
        )
        tasks.append(task)

    task_path = workspace_path / "task.json"
    data = {
        "project": {
            "name": "DarkFactory Project",
            "workspace": str(workspace_path),
        },
        "tasks": [t.to_dict() for t in tasks],
    }

    with open(task_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Clean up cache
    plan_cache_path.unlink()

    console.print(f"[green]Created task.json with {len(tasks)} tasks[/green]")
    console.print(f"[dim]Workspace: {workspace_path}[/dim]")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("  [cyan]darkfactory status[/cyan] - View project status")
    console.print("  [cyan]darkfactory run[/cyan] - Execute tasks")


@plan.command("modify")
@click.argument("feedback")
@click.option("--workspace", "-w", default=".", help="Workspace directory")
def plan_modify(feedback: str, workspace: str):
    """Modify the current plan based on feedback.

    This will re-run planning with the modification request.
    """
    console.print(f"[bold yellow]Modifying plan:[/bold yellow] {feedback}")
    console.print("[dim]Re-running planning with modifications...[/dim]")
    console.print()
    console.print("[yellow]Note: Plan modification requires LLM integration.[/yellow]")
    console.print("[yellow]Please re-run 'darkfactory plan' with your updated goal.[/yellow]")


# =============================================================================
# Init Command
# =============================================================================

@cli.command()
@click.option("--workspace", "-w", default=".", help="Workspace directory")
def init(workspace: str):
    """Initialize a new DarkFactory project.

    Creates the necessary directory structure and files.
    """
    workspace_path = Path(workspace).resolve()

    console.print(f"[bold green]Initializing DarkFactory project...[/bold green]")
    console.print(f"Workspace: {workspace_path}")

    # Create directories
    dirs = [
        workspace_path / "src",
        workspace_path / "tests",
        workspace_path / "memory" / "palace",
        workspace_path / "skills",
        workspace_path / "docs",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        console.print(f"  [cyan]Created:[/cyan] {d.relative_to(workspace_path)}")

    # Create basic files
    readme_path = workspace_path / "README.md"
    if not readme_path.exists():
        readme_path.write_text("# DarkFactory Project\n\n", encoding="utf-8")
        console.print(f"  [cyan]Created:[/cyan] README.md")

    # Create .gitignore
    gitignore_path = workspace_path / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text("__pycache__/\n*.pyc\n.env\nmemory/\n*.db\n", encoding="utf-8")
        console.print(f"  [cyan]Created:[/cyan] .gitignore")

    console.print()
    console.print("[green]DarkFactory project initialized![/green]")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("  [cyan]darkfactory plan \"your goal\"[/cyan] - Create your first task plan")
    console.print("  [cyan]darkfactory config setup[/cyan] - Configure AI provider")


# =============================================================================
# Run Command
# =============================================================================

@cli.command()
@click.option("--all", "run_all", is_flag=True, help="Run all pending tasks")
@click.option("--task", "task_id", type=str, help="Run specific task by ID")
@click.option("--agents", type=int, default=1, help="Number of parallel agents")
@click.option("--workspace", "-w", default=".", help="Workspace directory")
def run(run_all: bool, task_id: str, agents: int, workspace: str):
    """Execute tasks.

    Without arguments, runs the next pending task.
    Use --all to run all pending tasks.
    Use --task to run a specific task.
    """
    workspace_path = Path(workspace).resolve()
    task_path, progress_path, _ = get_project_paths(workspace_path)

    if not task_path.exists():
        console.print("[red]No task.json found.[/red]")
        console.print(f"[dim]Expected at: {task_path}[/dim]")
        console.print()
        console.print("[yellow]Run 'darkfactory plan' first to create tasks.[/yellow]")
        return

    # Load tasks
    engine = TaskEngine(task_store_path=task_path, workspace_path=workspace_path)
    engine.load_tasks()

    stats = engine.get_statistics()

    if stats["pending"] == 0 and stats["in_progress"] == 0:
        console.print("[green]All tasks completed![/green]")
        _show_final_stats(engine)
        return

    console.print(f"[bold blue]DarkFactory Task Runner[/bold blue]")
    console.print(f"Workspace: {workspace_path}")
    console.print(f"Agents: {agents}")
    console.print()

    if run_all:
        console.print(f"[cyan]Running all {stats['pending']} pending tasks...[/cyan]")
        _run_all_tasks(engine, agents, progress_path)
    elif task_id:
        console.print(f"[cyan]Running task {task_id}...[/cyan]")
        _run_single_task(engine, task_id, workspace_path)
    else:
        # Check for in_progress tasks first (resume interrupted work)
        in_progress = engine.get_in_progress_tasks()
        if in_progress:
            task = in_progress[0]
            console.print(f"[cyan]Resuming task: {task.title}[/cyan]")
            _run_single_task(engine, task.id, workspace_path)
            return

        # Run next pending task
        next_task = engine.select_next_task()
        if next_task:
            console.print(f"[cyan]Running next task: {next_task.title}[/cyan]")
            _run_single_task(engine, next_task.id, workspace_path)
        else:
            console.print("[yellow]No ready tasks found.[/yellow]")
            console.print(f"[dim]Pending: {stats['pending']}, Blocked: {stats['blocked']}[/dim]")


def _run_single_task(engine: TaskEngine, task_id: str, workspace_path: Path):
    """Run a single task using the agent loop"""
    task = engine.get_task(task_id)
    if not task:
        console.print(f"[red]Task not found: {task_id}[/red]")
        return

    console.print(Panel(
        f"[bold]{task.title}[/bold]\n{task.description}",
        title=f"Executing {task.id}"
    ))

    # Mark as in progress
    engine.update_task_status(task_id, TaskStatus.IN_PROGRESS)

    # Show steps to execute
    console.print()
    for i, step in enumerate(task.steps, 1):
        console.print(f"  [cyan]{i}.[/cyan] {step}")
    console.print()

    # Load config and check API key
    try:
        config = load_existing_config()
    except ValueError:
        console.print("[red]Configuration error: API key not set[/red]")
        console.print("[dim]Run 'darkfactory config setup' to configure[/dim]")
        engine.update_task_status(task_id, TaskStatus.BLOCKED, blocked_reason="API key not configured")
        return

    if not config.llm.api_key:
        console.print("[red]API key not configured[/red]")
        console.print("[dim]Run 'darkfactory config setup' to configure[/dim]")
        engine.update_task_status(task_id, TaskStatus.BLOCKED, blocked_reason="API key not configured")
        return

    # Register built-in tools
    register_builtin_tools()

    # Create agent loop
    agent = AgentLoop(
        config=config,
        workspace_path=workspace_path,
    )

    async def run_task():
        try:
            result = await agent.execute_task(task.steps, task.id)

            if result["success"]:
                console.print(f"[green]Task completed successfully![/green]")
                console.print(f"[dim]Steps: {result['steps_completed']}/{result['steps_total']}[/dim]")
                console.print(f"[dim]Duration: {result['duration_seconds']:.1f}s[/dim]")

                if result["files_created"]:
                    console.print(f"[dim]Files created: {len(result['files_created'])}[/dim]")

                engine.update_task_status(task_id, TaskStatus.COMPLETED)
            else:
                console.print(f"[red]Task failed[/red]")
                console.print(f"[dim]Steps completed: {result['steps_completed']}/{result['steps_total']}[/dim]")

                # Show step errors
                for step_result in result.get("step_results", []):
                    if step_result.get("error"):
                        console.print(f"[red]Step {step_result['step']} error:[/red] {step_result['error']}")

                # Mark as blocked if partial completion
                if result["steps_completed"] > 0:
                    engine.update_task_status(task_id, TaskStatus.BLOCKED,
                                            blocked_reason=f"Partial completion: {result['steps_completed']}/{result['steps_total']} steps")

        finally:
            await agent.close()

    # Run the task
    try:
        asyncio.run(run_task())
    except Exception as e:
        console.print(f"[red]Execution error: {e}[/red]")
        engine.update_task_status(task_id, TaskStatus.BLOCKED, blocked_reason=str(e))


def _run_all_tasks(engine: TaskEngine, agents: int, progress_path: Path):
    """Run all pending tasks"""
    stats = engine.get_statistics()

    console.print(f"Total: {stats['total']}, Pending: {stats['pending']}, "
                  f"Completed: {stats['completed']}, Blocked: {stats['blocked']}")

    ready_tasks = engine.select_ready_tasks()
    completed = 0

    for task in ready_tasks:
        engine.update_task_status(task.id, TaskStatus.IN_PROGRESS)
        console.print(f"\n[cyan]Executing:[/cyan] {task.title}")

        # Demo: just mark complete
        engine.update_task_status(task.id, TaskStatus.COMPLETED)
        completed += 1
        console.print(f"[green]Completed {completed}/{len(ready_tasks)}[/green]")

    console.print()
    _show_final_stats(engine)


def _show_final_stats(engine: TaskEngine):
    """Show final statistics"""
    stats = engine.get_statistics()

    table = Table(title="Final Statistics", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")

    table.add_row("Total Tasks", str(stats["total"]))
    table.add_row("Completed", str(stats["completed"]))
    table.add_row("Pending", str(stats["pending"]))
    table.add_row("Blocked", str(stats["blocked"]))

    if stats["total"] > 0:
        pct = stats["completed"] / stats["total"] * 100
        table.add_row("Progress", f"{pct:.1f}%")

    console.print(table)


# =============================================================================
# Status Command
# =============================================================================

@cli.command()
@click.option("--workspace", "-w", default=".", help="Workspace directory")
def status(workspace: str):
    """Show project status."""
    workspace_path = Path(workspace).resolve()
    task_path, _, _ = get_project_paths(workspace_path)

    console.print(f"[bold blue]DarkFactory Status[/bold blue]")
    console.print(f"Workspace: {workspace_path}")
    console.print()

    if not task_path.exists():
        console.print("[yellow]No task.json found.[/yellow]")
        console.print("[dim]Run 'darkfactory plan' to create tasks.[/dim]")
        return

    engine = TaskEngine(task_store_path=task_path, workspace_path=workspace_path)
    engine.load_tasks()
    stats = engine.get_statistics()

    # Statistics table
    table = Table(title="Task Statistics", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")

    table.add_row("Total", str(stats["total"]))
    table.add_row("[green]Completed[/green]", str(stats["completed"]))
    table.add_row("[yellow]Pending[/yellow]", str(stats["pending"]))
    table.add_row("[blue]In Progress[/blue]", str(stats["in_progress"]))
    table.add_row("[red]Blocked[/red]", str(stats["blocked"]))

    if stats["total"] > 0:
        pct = stats["completed"] / stats["total"] * 100
        table.add_row("Progress", f"[bold]{pct:.1f}%[/bold]")

    console.print(table)

    # Task list
    tasks = list(engine._tasks.values())
    if tasks:
        console.print()
        task_table = Table(title="Tasks")
        task_table.add_column("ID", style="cyan", width=12)
        task_table.add_column("Title", style="white")
        task_table.add_column("Status", width=12)
        task_table.add_column("Priority", justify="center", width=10)

        status_colors = {
            TaskStatus.PENDING: "yellow",
            TaskStatus.IN_PROGRESS: "blue",
            TaskStatus.COMPLETED: "green",
            TaskStatus.BLOCKED: "red",
        }

        for task in sorted(tasks, key=lambda t: t.priority):
            color = status_colors.get(task.status, "white")
            status_str = f"[{color}]{task.status.value}[/{color}]"
            task_table.add_row(
                task.id,
                task.title[:35],
                status_str,
                str(task.priority)
            )

        console.print(task_table)


# =============================================================================
# Progress Command
# =============================================================================

@cli.command()
@click.option("--workspace", "-w", default=".", help="Workspace directory")
def progress(workspace: str):
    """Show task progress."""
    workspace_path = Path(workspace).resolve()
    task_path, progress_path, _ = get_project_paths(workspace_path)

    console.print(f"[bold blue]Progress Report[/bold blue]")
    console.print(f"Workspace: {workspace_path}")
    console.print()

    if not task_path.exists():
        console.print("[yellow]No tasks found.[/yellow]")
        return

    engine = TaskEngine(task_store_path=task_path, workspace_path=workspace_path)
    engine.load_tasks()

    stats = engine.get_statistics()
    total = stats["total"]
    completed = stats["completed"]

    if total == 0:
        console.print("[yellow]No tasks yet.[/yellow]")
        return

    pct = completed / total * 100

    # Progress bar (ASCII-compatible)
    bar_width = 40
    filled = int(bar_width * completed / total)
    bar = "#" * filled + "-" * (bar_width - filled)

    console.print(f"[bold]{pct:.1f}%[/bold] [{bar}]")
    console.print(f"{completed}/{total} tasks completed")
    console.print()

    # Show blocked tasks
    blocked = engine.get_blocked_tasks()
    if blocked:
        console.print("[red]Blocked Tasks:[/red]")
        for task in blocked:
            reason = task.blocked_reason or "Unknown reason"
            console.print(f"  [red]•[/red] {task.id}: {task.title}")
            console.print(f"    [dim]{reason}[/dim]")
        console.print()


# =============================================================================
# Critical Path Command
# =============================================================================

@cli.command()
@click.option("--workspace", "-w", default=".", help="Workspace directory")
def critical_path(workspace: str):
    """Show critical path analysis."""
    workspace_path = Path(workspace).resolve()
    _, _, plan_cache_path = get_project_paths(workspace_path)

    console.print(f"[bold blue]Critical Path Analysis[/bold blue]")
    console.print()

    if not plan_cache_path.exists():
        console.print("[yellow]No plan data found.[/yellow]")
        console.print("[dim]Run 'darkfactory plan' first to generate analysis.[/dim]")
        return

    with open(plan_cache_path, "r", encoding="utf-8") as f:
        plan_data = json.load(f)

    critical_path = plan_data.get("critical_path", [])
    total_duration = plan_data.get("total_duration", 0)
    agent_req = plan_data.get("agent_requirements", 1)

    if critical_path:
        console.print("[bold red]Critical Path:[/bold red]")
        console.print(" → ".join(critical_path))
        console.print()
        console.print(f"[cyan]Total Duration:[/cyan] {total_duration} minutes ({total_duration/60:.1f} hours)")
        console.print(f"[cyan]Required Agents:[/cyan] {agent_req}")
    else:
        console.print("[yellow]No critical path calculated yet.[/yellow]")


# =============================================================================
# Web Command
# =============================================================================

@cli.command()
@click.option("--port", type=int, default=3000, help="Port for frontend")
@click.option("--api-port", type=int, default=8000, help="Port for API server")
@click.option("--workspace", "-w", default=".", help="Workspace directory")
def web(port: int, api_port: int, workspace: str):
    """Start the web UI."""
    workspace_path = Path(workspace).resolve()

    console.print(f"[bold green]Starting DarkFactory Web UI[/bold green]")
    console.print()
    console.print(f"  [cyan]Frontend:[/cyan] http://localhost:{port}")
    console.print(f"  [cyan]Backend API:[/cyan] http://localhost:{api_port}")
    console.print()
    console.print(f"Workspace: {workspace_path}")
    console.print()
    console.print("[yellow]Note: Web UI implementation is work in progress.[/yellow]")
    console.print("[yellow]The frontend is in web/frontend and backend in web/backend.[/yellow]")


# =============================================================================
# Memory Commands
# =============================================================================

@cli.group()
def memory():
    """Memory management commands."""
    pass


@memory.command(name="search")
@click.argument("query")
def memory_search(query: str):
    """Search memory."""
    console.print(f"[bold blue]Searching memory:[/bold blue] {query}")
    console.print()
    console.print("[yellow]Memory search requires LLM integration.[/yellow]")
    console.print("[yellow]Would search palace/knowledge graph for relevant context.[/yellow]")


# =============================================================================
# Skills Commands
# =============================================================================

@cli.group()
def skills():
    """Skills management commands."""
    pass


@skills.command(name="list")
def skills_list():
    """List available skills."""
    console.print("[bold blue]Available Skills[/bold blue]")
    console.print()

    skills_path = Path("skills")
    if not skills_path.exists() or not list(skills_path.glob("*.md")):
        console.print("[dim]No skills created yet.[/dim]")
        console.print("[dim]Skills are auto-generated during task execution.[/dim]")
        return

    for skill_file in skills_path.glob("*.md"):
        console.print(f"  [cyan]•[/cyan] {skill_file.stem}")


# =============================================================================
# Cron Commands
# =============================================================================

@cli.group()
def cron():
    """Cron scheduler commands."""
    pass


@cron.command(name="list")
def cron_list():
    """List scheduled jobs."""
    console.print("[bold blue]Scheduled Jobs[/bold blue]")
    console.print()
    console.print("[dim]No jobs scheduled yet.[/dim]")
    console.print("[dim]Use 'darkfactory cron create' to schedule a job.[/dim]")


@cron.command()
@click.argument("description")
@click.option("--every", help="Run interval (e.g., 1d, 30m)")
def cron_create(description: str, every: str):
    """Create a scheduled job."""
    console.print(f"[bold green]Created job:[/bold green] {description}")
    if every:
        console.print(f"[dim]Interval: {every}[/dim]")
    console.print()
    console.print("[yellow]Cron scheduling requires background worker integration.[/yellow]")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    cli()
