"""Unit tests for the settings module."""
import pytest
from mcp_server_qdrant.settings import Settings
from mcp_server_qdrant.embeddings.types import EmbeddingProviderType

def test_settings_with_url(mock_env_vars):
    """Test settings initialization with URL configuration."""
    settings = Settings()
    assert settings.qdrant_url == ":memory:"
    assert settings.collection_name == "test_collection"
    assert settings.embedding_provider == EmbeddingProviderType.FASTEMBED
    assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"

def test_settings_validation():
    """Test settings validation."""
    with pytest.raises(ValueError):
        Settings(QDRANT_URL="invalid-url", QDRANT_LOCAL_PATH="/some/path")
    
    with pytest.raises(ValueError):
        Settings(COLLECTION_NAME="")
    
    with pytest.raises(ValueError):
        Settings(EMBEDDING_PROVIDER="invalid_provider")

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