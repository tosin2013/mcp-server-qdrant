import click
import asyncio
from .task_commands import task

@click.group()
def cli():
    """MCP Server Qdrant CLI."""
    pass

cli.add_command(task)

def run_async(func):
    """Decorator to run async functions in click commands."""
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper

# Apply async wrapper to task commands
task.commands["create_from_test"].callback = run_async(task.commands["create_from_test"].callback)
task.commands["show"].callback = run_async(task.commands["show"].callback)
task.commands["solve"].callback = run_async(task.commands["solve"].callback) 