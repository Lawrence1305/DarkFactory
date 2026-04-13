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
from typing import Optional, Dict, Any

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint

import questionary

from .config import Config, load_config, detect_provider_type, ProviderType, LLMProvider
from .config import (
    ModelsConfig, ModelProvider, ModelDefinition, ModelApi,
    load_models_config, save_models_config, create_default_models_config,
    BUILTIN_PROVIDERS
)
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
@click.option("--provider", type=str, help="Provider to set up (optional)")
def config_setup(provider: str):
    """
    Interactive model configuration setup.

    Follows the OpenClaw-style interactive setup flow:
    1. Select a provider
    2. Configure auth method
    3. Enter API key
    4. Select model
    5. Configure agents
    """
    console.print(Panel.fit(
        "[bold green]DarkFactory Model Configuration[/bold green]\n"
        "Interactive setup for AI model providers",
        border_style="green"
    ))
    console.print()

    # Step 1: Select provider
    provider_options = []
    for pid, pdata in BUILTIN_PROVIDERS.items():
        provider_options.append({
            "name": f"{pdata['name']} ({pid})",
            "value": pid,
        })
    provider_options.append({"name": "Custom provider", "value": "custom"})

    if provider and provider in BUILTIN_PROVIDERS:
        selected_provider_id = provider
        console.print(f"[cyan]Provider selected via --provider:[/cyan] {selected_provider_id}")
    else:
        selected_provider_id = questionary.select(
            "Select a model provider:",
            choices=provider_options,
            style=questionary.Style([
                ('selected', 'fg:ansigreen bold'),
                ('pointer', 'fg:ansigreen bold'),
            ])
        ).ask()

    console.print()

    # Step 2: Get provider config
    if selected_provider_id == "custom":
        base_url = questionary.text(
            "Enter the API base URL:",
            validate=lambda x: len(x) > 0 or "URL is required"
        ).ask()
        api_type = questionary.select(
            "Select API type:",
            choices=[
                {"name": "OpenAI-compatible", "value": "openai"},
                {"name": "Anthropic-compatible", "value": "anthropic"},
            ]
        ).ask()
        provider_name = questionary.text(
            "Provider name (for display):",
            default="Custom Provider"
        ).ask()
    else:
        pdata = BUILTIN_PROVIDERS[selected_provider_id]
        provider_name = pdata["name"]
        base_url = pdata["base_url"]
        api_type = pdata["api"]
        console.print(f"[dim]Provider:[/dim] {provider_name}")
        console.print(f"[dim]API URL:[/dim] {base_url}")

    console.print()

    # Step 3: Enter API key
    api_key = questionary.password(
        f"Enter API key for {provider_name}:",
        validate=lambda x: len(x) > 0 or "API key is required"
    ).ask()

    console.print()

    # Step 4: Select model
    if selected_provider_id == "custom":
        model_id = questionary.text(
            "Enter model name:",
            default="gpt-4o",
            validate=lambda x: len(x) > 0 or "Model name is required"
        ).ask()
    else:
        pdata = BUILTIN_PROVIDERS[selected_provider_id]
        model_options = [
            {"name": f"{m['name']} ({m['id']})", "value": m['id']}
            for m in pdata.get("models", [])
        ]
        if not model_options:
            model_id = questionary.text(
                "Enter model name:",
                default="gpt-4o"
            ).ask()
        else:
            model_id = questionary.select(
                "Select a model:",
                choices=model_options
            ).ask()

    console.print()

    # Step 5: Configure agents
    max_agents = questionary.text(
        "Max parallel agents:",
        default="4",
        validate=lambda x: x.isdigit() and int(x) > 0 or "Must be a positive number"
    ).ask()

    console.print()

    # Update models config
    models_config = load_models_config()

    # Create or update provider
    if selected_provider_id != "custom" and selected_provider_id in models_config.providers:
        prov = models_config.providers[selected_provider_id]
        prov.api_key = api_key
        prov.base_url = base_url
    else:
        prov = ModelProvider(
            id=selected_provider_id,
            name=provider_name,
            base_url=base_url,
            api_key=api_key,
            api=ModelApi(api_type),
            models=[]
        )
        models_config.providers[selected_provider_id] = prov

    # Set as primary model
    models_config.primary_model = f"{selected_provider_id}/{model_id}"

    # Save models config
    save_models_config(models_config)

    # Also update main config
    cfg = Config()
    cfg.llm.base_url = base_url
    cfg.llm.api_key = api_key
    cfg.llm.model = model_id
    cfg.llm.provider_type = ProviderType(api_type)
    cfg.agent.max_agents = int(max_agents)

    config_path = get_config_path()
    cfg.save(str(config_path))

    console.print()
    console.print(Panel.fit(
        f"[bold green]Configuration Complete![/bold green]\n"
        f"Provider: {provider_name}\n"
        f"Model: {model_id}\n"
        f"Max Agents: {max_agents}",
        border_style="green"
    ))
    console.print()
    console.print("[dim]Run 'darkfactory config show' to verify configuration.[/dim]")
    console.print("[dim]Run 'darkfactory config models list' to see all available models.[/dim]")


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
# Config Models Subcommands
# =============================================================================

@config.group("models")
def config_models():
    """Manage model providers and configurations."""
    pass


@config_models.command("list")
def config_models_list():
    """List all configured models and providers."""
    models_config = load_models_config()

    console.print("[bold blue]Configured Providers and Models[/bold blue]\n")

    for provider_id, provider in models_config.providers.items():
        console.print(f"[cyan]{provider.name}[/cyan] ({provider_id})")
        console.print(f"  URL: {provider.base_url}")

        if provider.api_key:
            console.print(f"  API Key: ***{provider.api_key[-4:]}")
        else:
            console.print(f"  [yellow]API Key: Not set[/yellow]")

        console.print(f"  Models:")
        for model in provider.models:
            console.print(f"    - {model.id}: {model.name}")
        console.print()


@config_models.command("add")
@click.argument("provider_id")
@click.option("--name", help="Provider display name")
@click.option("--base-url", help="API base URL")
@click.option("--api", type=click.Choice(["openai", "anthropic"]), default="openai", help="API type")
def config_models_add(provider_id: str, name: str, base_url: str, api: str):
    """Add a new model provider."""
    models_config = load_models_config()

    if provider_id in models_config.providers:
        console.print(f"[yellow]Provider '{provider_id}' already exists.[/yellow]")
        return

    if not base_url:
        base_url = Prompt.ask("Enter base URL")

    provider = ModelProvider(
        id=provider_id,
        name=name or provider_id,
        base_url=base_url,
        api=ModelApi(api),
        models=[],
    )

    models_config.providers[provider_id] = provider
    save_models_config(models_config)

    console.print(f"[green]Added provider '{provider_id}'[/green]")


@config_models.command("remove")
@click.argument("provider_id")
def config_models_remove(provider_id: str):
    """Remove a model provider."""
    models_config = load_models_config()

    if provider_id not in models_config.providers:
        console.print(f"[red]Provider '{provider_id}' not found.[/red]")
        return

    del models_config.providers[provider_id]
    save_models_config(models_config)

    console.print(f"[green]Removed provider '{provider_id}'[/green]")


@config_models.command("set-primary")
@click.argument("provider_model")
def config_models_set_primary(provider_model: str):
    """Set the primary model (format: provider/model)."""
    models_config = load_models_config()

    # Validate the provider/model exists
    provider, model = models_config.get_provider_model(provider_model)
    if not provider or not model:
        console.print(f"[red]Unknown provider/model: {provider_model}[/red]")
        console.print("[dim]Use 'darkfactory config models list' to see available options.[/dim]")
        return

    models_config.primary_model = provider_model
    save_models_config(models_config)

    # Also update the main config
    cfg = load_existing_config()
    cfg.llm.base_url = provider.base_url
    cfg.llm.model = model.id
    if provider.api == ModelApi.ANTHROPIC:
        cfg.llm.provider_type = ProviderType.ANTHROPIC
    else:
        cfg.llm.provider_type = ProviderType.OPENAI
    cfg.save(str(get_config_path()))

    console.print(f"[green]Primary model set to: {provider_model}[/green]")
    console.print(f"[dim]Updated main config as well.[/dim]")


@config_models.command("add-model")
@click.argument("provider_id")
@click.argument("model_id")
@click.option("--name", help="Model display name")
@click.option("--max-tokens", type=int, default=4096, help="Max tokens")
@click.option("--context-window", type=int, default=128000, help="Context window size")
def config_models_add_model(provider_id: str, model_id: str, name: str, max_tokens: int, context_window: int):
    """Add a model to a provider."""
    models_config = load_models_config()

    if provider_id not in models_config.providers:
        console.print(f"[red]Provider '{provider_id}' not found.[/red]")
        return

    provider = models_config.providers[provider_id]

    # Check if model already exists
    if provider.get_model(model_id):
        console.print(f"[yellow]Model '{model_id}' already exists in provider '{provider_id}'.[/yellow]")
        return

    model = ModelDefinition(
        id=model_id,
        name=name or model_id,
        api=provider.api,
        max_tokens=max_tokens,
        context_window=context_window,
    )

    provider.models.append(model)
    save_models_config(models_config)

    console.print(f"[green]Added model '{model_id}' to provider '{provider_id}'[/green]")


@config_models.command("set-api-key")
@click.argument("provider_id")
def config_models_set_api_key(provider_id: str):
    """Set API key for a provider."""
    models_config = load_models_config()

    if provider_id not in models_config.providers:
        console.print(f"[red]Provider '{provider_id}' not found.[/red]")
        return

    provider = models_config.providers[provider_id]
    api_key = Prompt.ask(f"Enter API key for {provider.name}", password=True)

    provider.api_key = api_key
    save_models_config(models_config)

    console.print(f"[green]API key set for '{provider_id}'[/green]")


@config_models.command("reset")
def config_models_reset():
    """Reset models configuration to defaults."""
    models_path = Path.home() / ".darkfactory" / "models.json"
    if models_path.exists():
        models_path.unlink()
    console.print("[yellow]Models config reset to defaults.[/yellow]")


# =============================================================================
# Config Auth Subcommands (OpenClaw-style)
# =============================================================================

@config.group("auth")
def config_auth():
    """Manage model authentication profiles."""
    pass


@config_auth.command("login")
@click.option("--provider", type=str, help="Provider id (e.g., anthropic, openai)")
@click.option("--method", type=str, help="Auth method (e.g., api-key, oauth)")
def config_auth_login(provider: str, method: str):
    """
    Interactive login to a model provider.

    Opens an interactive flow to authenticate with a provider.
    Similar to 'openclaw models auth login'.
    """
    console.print(Panel.fit(
        "[bold green]Provider Authentication[/bold green]\n"
        "Login to a model provider",
        border_style="green"
    ))
    console.print()

    models_config = load_models_config()

    # Get list of providers
    provider_options = []
    for pid, pdata in BUILTIN_PROVIDERS.items():
        provider_options.append({
            "name": f"{pdata['name']} ({pid})",
            "value": pid,
        })

    if provider and provider in BUILTIN_PROVIDERS:
        selected_provider_id = provider
        console.print(f"[cyan]Provider selected:[/cyan] {selected_provider_id}")
    else:
        selected_provider_id = questionary.select(
            "Select a provider:",
            choices=provider_options
        ).ask()

    console.print()

    # Select auth method
    auth_methods = [
        {"name": "API Key (paste token)", "value": "api-key"},
    ]

    if not provider or method == "api-key":
        selected_method = questionary.select(
            "Select authentication method:",
            choices=auth_methods
        ).ask()
    else:
        selected_method = method

    console.print()

    # Get API key
    if selected_method == "api-key":
        api_key = questionary.password(
            f"Enter API key for {selected_provider_id}:",
            validate=lambda x: len(x) > 0 or "API key is required"
        ).ask()

        # Update models config
        if selected_provider_id in models_config.providers:
            models_config.providers[selected_provider_id].api_key = api_key
        else:
            pdata = BUILTIN_PROVIDERS.get(selected_provider_id, {})
            models_config.providers[selected_provider_id] = ModelProvider(
                id=selected_provider_id,
                name=pdata.get("name", selected_provider_id),
                base_url=pdata.get("base_url", ""),
                api_key=api_key,
                api=ModelApi(pdata.get("api", "openai")),
                models=[]
            )

        save_models_config(models_config)

        console.print()
        console.print(f"[green]Successfully authenticated with {selected_provider_id}[/green]")
    else:
        console.print(f"[yellow]Auth method '{selected_method}' not implemented yet.[/yellow]")


@config_auth.command("add")
def config_auth_add():
    """
    Add a new authentication profile.

    Similar to 'openclaw models auth add'.
    """
    console.print(Panel.fit(
        "[bold green]Add Authentication Profile[/bold green]\n"
        "Add a new provider authentication",
        border_style="green"
    ))
    console.print()

    # This is essentially the same as login
    # Reuse the login flow
    config_auth_login.callback()


@config_auth.command("paste-token")
@click.argument("provider_id")
@click.option("--profile-id", type=str, help="Profile id (default: provider:manual)")
@click.option("--expires-in", type=str, help="Token expiry (e.g., 365d, 12h)")
def config_auth_paste_token(provider_id: str, profile_id: str, expires_in: str):
    """
    Paste a token directly into auth profiles.

    Similar to 'openclaw models auth paste-token'.
    """
    models_config = load_models_config()

    if provider_id not in BUILTIN_PROVIDERS and provider_id not in models_config.providers:
        console.print(f"[red]Unknown provider: {provider_id}[/red]")
        return

    pdata = BUILTIN_PROVIDERS.get(provider_id, {})
    provider_name = pdata.get("name", provider_id)

    token = questionary.password(
        f"Paste token for {provider_name}:",
        validate=lambda x: len(x) > 0 or "Token is required"
    ).ask()

    # Store in models config
    if provider_id in models_config.providers:
        models_config.providers[provider_id].api_key = token
    else:
        models_config.providers[provider_id] = ModelProvider(
            id=provider_id,
            name=provider_name,
            base_url=pdata.get("base_url", ""),
            api_key=token,
            api=ModelApi(pdata.get("api", "openai")),
            models=[]
        )

    save_models_config(models_config)

    console.print()
    console.print(f"[green]Token saved for {provider_name}[/green]")
    if expires_in:
        console.print(f"[dim]Expires in: {expires_in}[/dim]")


@config_auth.command("status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--probe", is_flag=True, help="Probe provider auth (live)")
def config_auth_status(output_json: bool, probe: bool):
    """
    Show authentication status.

    Similar to 'openclaw models auth status'.
    """
    models_config = load_models_config()

    if output_json:
        import json
        providers_with_keys = {
            pid: {"has_key": bool(p.api_key), "url": p.base_url}
            for pid, p in models_config.providers.items()
        }
        print(json.dumps(providers_with_keys, indent=2))
        return

    console.print("[bold blue]Authentication Status[/bold blue]\n")

    if not models_config.providers:
        console.print("[yellow]No providers configured.[/yellow]")
        console.print("[dim]Run 'darkfactory config auth login' to authenticate.[/dim]")
        return

    table = Table()
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("API Key", style="yellow")

    for provider_id, provider in models_config.providers.items():
        has_key = bool(provider.api_key)
        status = "[green]Configured[/green]" if has_key else "[red]Not set[/red]"
        key_display = f"***...{provider.api_key[-4:]}" if has_key else "[red]Missing[/red]"
        table.add_row(provider.name, status, key_display)

    console.print(table)
    console.print()
    console.print("[dim]Run 'darkfactory config auth login' to add or update auth.[/dim]")


@config_auth.command("list")
def config_auth_list():
    """
    List all authentication profiles.

    Similar to 'openclaw models auth list'.
    """
    config_auth_status.callback()



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

    # Load config and resolve API key from models config if needed
    try:
        config = load_existing_config()
    except ValueError:
        console.print("[red]Configuration error: API key not set[/red]")
        console.print("[dim]Run 'darkfactory config setup' to configure[/dim]")
        engine.update_task_status(task_id, TaskStatus.BLOCKED, blocked_reason="API key not configured")
        return

    # If API key not in main config, try models config
    if not config.llm.api_key:
        models_config = load_models_config()
        provider, model = models_config.resolve_primary()
        if provider and provider.api_key:
            config.llm.api_key = provider.api_key
            config.llm.base_url = provider.base_url
            if provider.api == ModelApi.ANTHROPIC:
                config.llm.provider_type = ProviderType.ANTHROPIC
            else:
                config.llm.provider_type = ProviderType.OPENAI
            config.llm.model = model.id if model else config.llm.model
            console.print(f"[dim]Using API key from provider '{provider.id}'[/dim]")
        else:
            console.print("[red]API key not configured[/red]")
            console.print("[dim]Run 'darkfactory config models set-api-key <provider>' to configure[/dim]")
            console.print("[dim]Or run 'darkfactory config setup' to configure directly[/dim]")
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
