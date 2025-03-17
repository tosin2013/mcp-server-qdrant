"""Unit tests for the settings module."""
import pytest
from mcp_server_qdrant.settings import Settings
from mcp_server_qdrant.embeddings.types import EmbeddingProviderType

def test_settings_with_url(mock_env_vars):
    """Test settings initialization with URL configuration."""
    settings = Settings()
    # When qdrant_url is ":memory:", it gets converted to None and qdrant_local_path becomes ":memory:"
    assert settings.qdrant_url is None
    assert settings.qdrant_local_path == ":memory:"
    assert settings.collection_name == "test_collection"
    assert settings.embedding_provider == EmbeddingProviderType.FASTEMBED
    assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    # Verify that get_qdrant_location() still returns ":memory:"
    assert settings.get_qdrant_location() == ":memory:"

def test_settings_validation():
    """Test settings validation."""
    # Test that providing both URL and local path prioritizes local path
    settings = Settings(
        QDRANT_URL="http://localhost:6333",
        QDRANT_LOCAL_PATH="/some/path",
        COLLECTION_NAME="test_collection"
    )
    assert settings.qdrant_url is None
    assert settings.qdrant_local_path == "/some/path"
    
    # Test that empty collection name raises ValueError
    with pytest.raises(ValueError):
        Settings(COLLECTION_NAME="", QDRANT_URL=":memory:")
    
    # Test that invalid embedding provider raises ValueError
    with pytest.raises(ValueError):
        Settings(COLLECTION_NAME="test_collection", EMBEDDING_PROVIDER="invalid_provider")

def test_settings_local_path():
    """Test settings with local path configuration."""
    settings = Settings(
        QDRANT_LOCAL_PATH="/tmp/qdrant",
        COLLECTION_NAME="test_collection"
    )
    assert settings.qdrant_local_path == "/tmp/qdrant"
    assert settings.qdrant_url is None

def test_settings_tool_descriptions():
    """Test custom tool descriptions."""
    custom_store_desc = "Custom store description"
    custom_find_desc = "Custom find description"
    
    settings = Settings(
        QDRANT_URL=":memory:",
        COLLECTION_NAME="test_collection",
        TOOL_STORE_DESCRIPTION=custom_store_desc,
        TOOL_FIND_DESCRIPTION=custom_find_desc
    )
    
    assert settings.tool_store_description == custom_store_desc
    assert settings.tool_find_description == custom_find_desc 