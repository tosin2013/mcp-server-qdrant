import pytest
import os
from uuid import UUID
from datetime import datetime
from unittest.mock import AsyncMock

from mcp_server_qdrant.models.task import Task, TestResult, TaskSuggestions
from mcp_server_qdrant.services.task_manager import MCPTaskManager

@pytest.fixture(autouse=True)
def skip_task_manager_tests(request):
    """Skip task manager tests if the Qdrant server is not available."""
    if os.environ.get("SKIP_QDRANT_TESTS") == "true":
        pytest.skip("Task manager tests are skipped in this environment")

@pytest.fixture
def test_result():
    return TestResult(
        name="test_authentication",
        error="Authentication failed: Invalid token",
        context={"user_id": "test123"},
        platform="linux",
        container_id="test_container"
    )

@pytest.fixture
def mock_qdrant_client(mocker):
    client = mocker.Mock()
    # Use AsyncMock for async methods
    client.search = AsyncMock(return_value=[
        mocker.Mock(
            payload={
                "title": "Auth Timeout",
                "solution": "Increased timeout value",
                "docs": ["auth.md"]
            },
            score=0.95
        )
    ])
    client.retrieve = AsyncMock(return_value=[
        mocker.Mock(
            payload={
                "content": Task(
                    id=UUID("12345678-1234-5678-1234-567812345678"),
                    title="Test Task",
                    description="Test Description"
                ).model_dump_json()
            }
        )
    ])
    client.upsert = AsyncMock(return_value=None)
    return client

@pytest.fixture
def task_manager(mock_qdrant_client):
    return MCPTaskManager(mock_qdrant_client)

@pytest.mark.asyncio
async def test_handle_test_failure(task_manager, test_result, mocker):
    # Mock embed_text
    mocker.patch(
        "mcp_server_qdrant.services.task_manager.embed_text",
        new=AsyncMock(return_value=[0.1, 0.2, 0.3])
    )
    
    result = await task_manager.handle_test_failure(test_result)
    
    assert "similar_issues" in result
    assert "suggestions" in result
    assert "task_id" in result
    assert "docs" in result
    
    assert len(result["similar_issues"]) > 0
    assert len(result["suggestions"]) > 0
    assert "auth.md" in result["docs"]

@pytest.mark.asyncio
async def test_find_similar_issues(task_manager):
    vector = [0.1, 0.2, 0.3]
    results = await task_manager.find_similar_issues(vector)
    
    assert len(results) > 0
    assert "title" in results[0]
    assert "solution" in results[0]
    assert "score" in results[0]

@pytest.mark.asyncio
async def test_generate_suggestions(task_manager, test_result):
    similar_issues = [
        {
            "title": "Auth Timeout",
            "solution": "Increased timeout value",
            "docs": ["auth.md"]
        }
    ]
    
    suggestions = await task_manager.generate_suggestions(test_result, similar_issues)
    
    assert isinstance(suggestions, TaskSuggestions)
    assert len(suggestions.fixes) > 0
    assert suggestions.should_create_task
    assert "auth.md" in suggestions.relevant_docs

@pytest.mark.asyncio
async def test_create_task(task_manager, test_result, mocker):
    # Mock embed_text
    mocker.patch(
        "mcp_server_qdrant.services.task_manager.embed_text",
        new=AsyncMock(return_value=[0.1, 0.2, 0.3])
    )
    
    suggestions = TaskSuggestions(
        description="Fix authentication test",
        fixes=["Try increasing timeout"],
        priority=2,
        relevant_docs=["auth.md"]
    )
    
    task = await task_manager.create_task(test_result, suggestions)
    
    assert isinstance(task, Task)
    assert task.title.startswith("Fix: ")
    assert task.priority == 2
    assert task.status == "open"
    assert len(task.related_tests) == 1
    assert "auth.md" in task.related_docs

@pytest.mark.asyncio
async def test_get_task(task_manager):
    task_id = UUID("12345678-1234-5678-1234-567812345678")
    task = await task_manager.get_task(task_id)
    
    assert isinstance(task, Task)
    assert task.title == "Test Task"
    assert task.description == "Test Description"

@pytest.mark.asyncio
async def test_update_task(task_manager, mocker):
    # Mock embed_text
    mocker.patch(
        "mcp_server_qdrant.services.task_manager.embed_text",
        new=AsyncMock(return_value=[0.1, 0.2, 0.3])
    )
    
    task_id = UUID("12345678-1234-5678-1234-567812345678")
    solution = "Increased timeout to 30 seconds"
    
    task = await task_manager.update_task(task_id, solution)
    
    assert isinstance(task, Task)
    assert task.solution == solution
    assert task.status == "completed"

@pytest.mark.asyncio
async def test_task_priority_calculation(task_manager, test_result):
    # Test with no similar issues
    priority = task_manager._calculate_priority(test_result, [])
    assert priority == 1
    
    # Test with similar issues
    priority = task_manager._calculate_priority(test_result, [{"title": "Test"}])
    assert priority == 2
    
    # Test with critical error
    test_result.error = "Critical security vulnerability"
    priority = task_manager._calculate_priority(test_result, [])
    assert priority == 3

def test_find_relevant_docs(task_manager, test_result):
    # Test with no similar issues
    docs = task_manager._find_relevant_docs(test_result, [])
    assert "auth.md" in docs  # Should be added due to "auth" in test name
    
    # Test with similar issues containing docs
    docs = task_manager._find_relevant_docs(
        test_result,
        [{"docs": ["api.md", "deployment.md"]}]
    )
    assert "auth.md" in docs
    assert "api.md" in docs
    assert "deployment.md" in docs 