"""
DarkFactory CLI Entry Point
"""

import sys
import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config, load_config, detect_provider_type, ProviderType

console = Console()


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


# Create CLI group
@click.group()
@click.version_option(version="0.1.0", prog_name="darkfactory")
def cli():
    """DarkFactory - AI-native Agent Framework"""
    pass


# ============ Config Command Group ============

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

    table.add_row("Provider Type", cfg.llm.provider_type.value)
    table.add_row("API Key", f"***...{cfg.llm.api_key[-4:]}" if cfg.llm.api_key else "(not set)")
    table.add_row("Base URL", cfg.llm.base_url or "(default)")
    table.add_row("Model", cfg.llm.model)
    table.add_row("Max Agents", str(cfg.agent.max_agents))

    console.print(table)


@config.command("set")
@click.option("--api-key", help="API key for the LLM provider")
@click.option("--base-url", help="Base URL (auto-detected if not provided)")
@click.option("--model", help="Model name (e.g., gpt-4o, claude-sonnet-4-20250514)")
@click.option("--provider-type", type=click.Choice(["anthropic", "openai"]), help="Provider type (auto-detected if not provided)")
@click.option("--max-agents", type=int, help="Maximum number of parallel agents")
def config_set(api_key, base_url, model, provider_type, max_agents):
    """Set configuration values."""
    cfg = load_existing_config()

    # Update values
    if api_key:
        cfg.llm.api_key = api_key

    if base_url:
        cfg.llm.base_url = base_url
        # Auto-detect provider type from base_url if not explicitly specified
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

    # Save config
    config_path = get_config_path()
    cfg.save(str(config_path))

    console.print(f"[green]Configuration saved to {config_path}[/green]")
    console.print(f"[dim]Provider type: {cfg.llm.provider_type.value}[/dim]")
    console.print(f"[dim]Model: {cfg.llm.model}[/dim]")


@config.command("setup")
@click.option("--provider", type=click.Choice(["anthropic", "openai", "minimax", "qwen", "deepseek"]), help="Quick setup provider")
def config_setup(provider):
    """Interactive configuration setup."""
    cfg = Config()

    console.print("[bold green]DarkFactory Configuration Setup[/bold green]\n")

    # Provider selection
    if provider:
        providers = {
            "anthropic": ("anthropic", "Anthropic Claude", "api.anthropic.com", "claude-sonnet-4-20250514"),
            "openai": ("openai", "OpenAI GPT-4", "api.openai.com", "gpt-4o"),
            "minimax": ("anthropic", "MiniMax", "api.minimax.chat/v1/text/chatcompletion_v2", "MiniMax-Text-01"),
            "qwen": ("openai", "Qwen (通义千问)", "dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
            "deepseek": ("openai", "DeepSeek", "api.deepseek.com/v1", "deepseek-chat"),
        }
        p = providers.get(provider, providers["openai"])
        cfg.llm.provider_type = ProviderType(p[0])
        cfg.llm.base_url = p[2]
        cfg.llm.model = p[3]
        console.print(f"[cyan]Selected:[/cyan] {p[1]}")
        console.print(f"[dim]Base URL: {p[2]}[/dim]")
        console.print(f"[dim]Model: {p[3]}[/dim]\n")
    else:
        console.print("Select a provider:")
        console.print("  1. Anthropic (Claude)")
        console.print("  2. OpenAI (GPT-4)")
        console.print("  3. MiniMax")
        console.print("  4. Qwen (通义千问)")
        console.print("  5. DeepSeek")
        console.print("  6. Custom (enter base URL manually)\n")

        choice = Prompt.ask("Enter choice", default="1")

        custom_providers = {
            "1": ("anthropic", "", "claude-sonnet-4-20250514"),
            "2": ("openai", "", "gpt-4o"),
            "3": ("anthropic", "api.minimax.chat/v1/text/chatcompletion_v2", "MiniMax-Text-01"),
            "4": ("openai", "dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
            "5": ("openai", "api.deepseek.com/v1", "deepseek-chat"),
        }

        if choice in custom_providers:
            p = custom_providers[choice]
            cfg.llm.provider_type = ProviderType(p[0])
            cfg.llm.base_url = p[1]
            cfg.llm.model = p[2]
        else:
            console.print("[yellow]Custom provider selected[/yellow]")
            cfg.llm.base_url = Prompt.ask("Enter base URL")
            cfg.llm.provider_type = detect_provider_type(cfg.llm.base_url)
            console.print(f"[dim]Auto-detected provider type: {cfg.llm.provider_type.value}[/dim]")
            cfg.llm.model = Prompt.ask("Enter model name", default="gpt-4o")

    # API Key
    console.print()
    api_key = Prompt.ask("Enter API key", password=True)
    cfg.llm.api_key = api_key

    # Max agents
    console.print()
    max_agents = Prompt.ask("Max parallel agents", default="4")
    cfg.agent.max_agents = int(max_agents)

    # Save
    config_path = get_config_path()
    cfg.save(str(config_path))

    console.print(f"\n[green]Configuration saved to {config_path}[/green]")
    console.print(f"[cyan]Provider type:[/cyan] {cfg.llm.provider_type.value}")
    console.print(f"[cyan]Model:[/cyan] {cfg.llm.model}")
    console.print("\n[dim]Run 'darkfactory config show' to verify configuration.[/dim]")


@config.command("reset")
def config_reset():
    """Reset configuration to defaults."""
    config_path = get_config_path()
    if config_path.exists():
        config_path.unlink()
        console.print("[yellow]Configuration reset[/yellow]")
    else:
        console.print("[dim]No configuration file to reset[/dim]")


# ============ Original CLI Commands ============

@cli.command()
def plan():
    """This command requires a goal argument."""
    console.print("[yellow]Use: darkfactory plan \"your goal\"[/yellow]")


@cli.command()
@click.argument("goal")
def plan_goal(goal: str):
    """Plan tasks from natural language description."""
    console.print(f"[bold blue]Planning:[/bold blue] {goal}")
    console.print("[yellow]This will analyze your goal and create a task plan...[/yellow]")
    console.print("[dim]Use 'darkfactory plan confirm' after reviewing the plan.[/dim]")


@cli.command()
def confirm():
    """Confirm the current plan and create task.json"""
    console.print("[bold green]Plan confirmed![/bold green]")
    console.print("[dim]Creating task.json...[/dim]")


@cli.command()
@click.argument("feedback")
def modify(feedback: str):
    """Modify the current plan based on feedback."""
    console.print(f"[bold yellow]Modifying plan:[/bold yellow] {feedback}")
    console.print("[dim]Re-analyzing and regenerating plan...[/dim]")


@cli.command()
def init():
    """Initialize the environment."""
    console.print("[bold green]Initializing DarkFactory...[/bold green]")


@cli.command()
@click.option("--all", "run_all", is_flag=True, help="Run all pending tasks")
@click.option("--task", "task_id", type=int, help="Run specific task by ID")
@click.option("--agents", type=int, default=1, help="Number of parallel agents")
def run(run_all: bool, task_id: int, agents: int):
    """Run tasks."""
    if run_all:
        console.print(f"[bold blue]Running all tasks with {agents} agents...[/bold blue]")
    elif task_id:
        console.print(f"[bold blue]Running task {task_id}...[/bold blue]")
    else:
        console.print("[bold blue]Running next pending task...[/bold blue]")


@cli.command()
def status():
    """Show project status."""
    table = Table(title="DarkFactory Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Tasks", "0")
    table.add_row("Completed", "0")
    table.add_row("In Progress", "0")
    table.add_row("Blocked", "0")

    console.print(table)


@cli.command()
def progress():
    """Show task progress."""
    console.print("[bold blue]Progress Report[/bold blue]")
    console.print("[dim]No tasks yet. Use 'darkfactory plan' to start.[/dim]")


@cli.command()
def critical_path():
    """Show critical path analysis."""
    console.print("[bold blue]Critical Path Analysis[/bold blue]")
    console.print("[dim]No analysis available yet.[/dim]")


@cli.group()
def memory():
    """Memory management commands."""
    pass


@memory.command(name="search")
@click.argument("query")
def memory_search(query: str):
    """Search memory."""
    console.print(f"[bold blue]Searching memory for:[/bold blue] {query}")


@cli.group()
def skills():
    """Skills management commands."""
    pass


@skills.command(name="list")
def skills_list():
    """List available skills."""
    console.print("[bold blue]Available Skills[/bold blue]")
    console.print("[dim]No skills created yet.[/dim]")


@cli.group()
def cron():
    """Cron scheduler commands."""
    pass


@cron.command(name="list")
def cron_list():
    """List scheduled jobs."""
    console.print("[bold blue]Scheduled Jobs[/bold blue]")
    console.print("[dim]No jobs scheduled yet.[/dim]")


@cron.command()
@click.argument("description")
@click.option("--every", help="Run interval (e.g., 1d, 30m)")
def cron_create(description: str, every: str):
    """Create a scheduled job."""
    console.print(f"[bold green]Created job:[/bold green] {description}")
    if every:
        console.print(f"[dim]Interval: {every}[/dim]")


@cli.command()
@click.option("--port", type=int, default=3000, help="Port to run the web server")
def web(port: int):
    """Start the web UI."""
    console.print(f"[bold green]Starting DarkFactory Web UI on port {port}...[/bold green]")
    console.print(f"[dim]Open http://localhost:{port} in your browser[/dim]")


if __name__ == "__main__":
    cli()
