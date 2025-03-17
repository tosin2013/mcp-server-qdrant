"""Common test fixtures and configurations for the test suite."""
import os
import pytest
from qdrant_client import QdrantClient
from mcp_server_qdrant.settings import Settings

@pytest.fixture
def settings():
    """Create test settings with in-memory Qdrant database."""
    return Settings(
        qdrant_url=":memory:",
        collection_name="test_collection",
        embedding_provider="fastembed",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
    )

@pytest.fixture
async def qdrant_client(settings):
    """Create a Qdrant client for testing."""
    client = QdrantClient(":memory:")
    yield client
    # Cleanup after tests
    try:
        await client.delete_collection(settings.collection_name)
    except Exception:
        pass
    await client.close()

@pytest.fixture
def test_data():
    """Provide common test data."""
    return {
        "sample_text": "This is a test document",
        "sample_metadata": {"source": "test", "type": "document"},
        "sample_query": "test document"
    }

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    # First clear any existing environment variables that might affect tests
    for key in ["QDRANT_URL", "COLLECTION_NAME", "EMBEDDING_PROVIDER", "EMBEDDING_MODEL", 
                "QDRANT_API_KEY", "QDRANT_LOCAL_PATH", "LOG_LEVEL", 
                "TOOL_STORE_DESCRIPTION", "TOOL_FIND_DESCRIPTION"]:
        monkeypatch.delenv(key, raising=False)
    
    # Then set the test environment variables
    env_vars = {
        "QDRANT_URL": ":memory:",
        "COLLECTION_NAME": "test_collection",
        "EMBEDDING_PROVIDER": "fastembed",
        "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2"
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars 

@pytest.fixture(autouse=True)
def skip_docker_tests(request):
    """Skip Docker-related tests if SKIP_DOCKER_TESTS is set."""
    if os.environ.get("SKIP_DOCKER_TESTS") == "true" and "docker" in request.node.name.lower():
        pytest.skip("Docker tests are skipped in this environment") 