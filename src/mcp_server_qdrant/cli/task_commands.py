import click
from uuid import UUID
import asyncio
from typing import Dict, Any

from ..qdrant import get_qdrant_client
from ..services.task_manager import MCPTaskManager
from ..models.task import TestResult
from ..utils.logger import get_logger

logger = get_logger(__name__)

@click.group()
def task():
    """Task management commands."""
    pass

@task.command()
@click.argument('test_name')
@click.argument('error_message')
@click.option('--context', '-c', type=str, help='JSON string of test context')
@click.option('--platform', '-p', type=str, help='Test platform')
@click.option('--container', type=str, help='Container ID')
async def create_from_test(test_name, error_message, context=None, platform=None, container=None):
    """Create a task from a test failure."""
    try:
        client = await get_qdrant_client()
        manager = MCPTaskManager(client)
        
        test_result = TestResult(
            name=test_name,
            error=error_message,
            context=context or {},
            platform=platform,
            container_id=container
        )
        
        result = await manager.handle_test_failure(test_result)
        
        # Display results
        click.echo("\nSimilar issues found:")
        for issue in result["similar_issues"]:
            click.echo(f"- {issue['title']}: {issue['solution']}")
        
        click.echo("\nSuggested fixes:")
        for i, fix in enumerate(result["suggestions"], 1):
            click.echo(f"{i}. {fix}")
        
        if result["task_id"]:
            click.echo(f"\nTask {result['task_id']} created for tracking")
            
        if result["docs"]:
            click.echo(f"Related docs: {', '.join(result['docs'])}")
            
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise click.ClickException(str(e))

@task.command()
@click.argument('task_id')
async def show(task_id):
    """Show task details."""
    try:
        client = await get_qdrant_client()
        manager = MCPTaskManager(client)
        
        task = await manager.get_task(UUID(task_id))
        
        click.echo(f"\nTask {task.id}")
        click.echo(f"Title: {task.title}")
        click.echo(f"Description: {task.description}")
        click.echo(f"Priority: {task.priority}")
        click.echo(f"Status: {task.status}")
        
        if task.solution:
            click.echo(f"Solution: {task.solution}")
            
        if task.related_docs:
            click.echo(f"Related docs: {', '.join(task.related_docs)}")
            
    except Exception as e:
        logger.error(f"Error showing task: {e}")
        raise click.ClickException(str(e))

@task.command()
@click.argument('task_id')
@click.argument('solution')
async def solve(task_id, solution):
    """Update task with solution."""
    try:
        client = await get_qdrant_client()
        manager = MCPTaskManager(client)
        
        task = await manager.update_task(UUID(task_id), solution)
        click.echo(f"Task {task.id} updated with solution")
        
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise click.ClickException(str(e)) 