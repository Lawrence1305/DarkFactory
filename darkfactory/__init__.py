"""
DarkFactory CLI - Command line interface
"""

import click
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """DarkFactory - AI-Native Agent Framework"""
    pass


@cli.command()
@click.argument("goal")
def plan(goal: str):
    """Plan tasks from natural language goal"""
    click.echo(f"Planning: {goal}")
    click.echo("This would invoke TaskPlanner to decompose the goal...")


@cli.command()
def confirm():
    """Confirm the current plan and generate task.json"""
    click.echo("Confirming plan...")


@cli.command()
def modify():
    """Modify the current plan"""
    click.echo("Modifying plan...")


@cli.command()
def init():
    """Initialize a new DarkFactory project"""
    click.echo("Initializing DarkFactory project...")


@cli.command()
@click.option("--all", is_flag=True, help="Run all tasks in parallel")
@click.option("--agents", default=1, help="Number of parallel agents")
@click.option("--task", help="Run specific task ID")
def run(all: bool, agents: int, task: str):
    """Execute tasks"""
    if all:
        click.echo(f"Running all tasks with {agents} agents...")
    elif task:
        click.echo(f"Running task {task}...")
    else:
        click.echo("Running next task...")


@cli.command()
def status():
    """Show project status"""
    click.echo("DarkFactory Status")
    click.echo("=================")
    click.echo("Tasks: 0 total, 0 completed, 0 pending")


@cli.command()
def progress():
    """Show task progress"""
    click.echo("Progress: 0%")


@cli.command()
def critical_path():
    """Show critical path"""
    click.echo("Critical Path Analysis")
    click.echo("Not yet implemented")


@cli.command()
def web():
    """Start the web UI"""
    click.echo("Starting web UI on http://localhost:3000")
    click.echo("Backend API on http://localhost:8000")


if __name__ == "__main__":
    cli()
