import os
from unittest.mock import patch

import pytest

from mcp_server_qdrant.embeddings.types import EmbeddingProviderType
from mcp_server_qdrant.settings import (
    DEFAULT_TOOL_FIND_DESCRIPTION,
    DEFAULT_TOOL_STORE_DESCRIPTION,
    EmbeddingProviderSettings,
    QdrantSettings,
    ToolSettings,
    Settings,
)


class TestQdrantSettings:
    def test_default_values(self):
        """Test that required fields raise errors when not provided."""
        with pytest.raises(ValueError):
            # Should raise error because required fields are missing
            QdrantSettings()

    @patch.dict(
        os.environ,
        {"QDRANT_URL": "http://localhost:6333", "COLLECTION_NAME": "test_collection"},
    )
    def test_minimal_config(self):
        """Test loading minimal configuration from environment variables."""
        settings = QdrantSettings()
        assert settings.location == "http://localhost:6333"
        assert settings.collection_name == "test_collection"
        assert settings.api_key is None
        assert settings.local_path is None

    @patch.dict(
        os.environ,
        {
            "QDRANT_URL": "http://qdrant.example.com:6333",
            "QDRANT_API_KEY": "test_api_key",
            "COLLECTION_NAME": "my_memories",
            "QDRANT_LOCAL_PATH": "/tmp/qdrant",
        },
    )
    def test_full_config(self):
        """Test loading full configuration from environment variables."""
        settings = QdrantSettings()
        assert settings.location == "http://qdrant.example.com:6333"
        assert settings.api_key == "test_api_key"
        assert settings.collection_name == "my_memories"
        assert settings.local_path == "/tmp/qdrant"


class TestEmbeddingProviderSettings:
    def test_default_values(self):
        """Test default values are set correctly."""
        settings = EmbeddingProviderSettings()
        assert settings.provider_type == EmbeddingProviderType.FASTEMBED
        assert settings.model_name == "sentence-transformers/all-MiniLM-L6-v2"

    @patch.dict(
        os.environ,
        {"EMBEDDING_MODEL": "custom_model"},
    )
    def test_custom_values(self):
        """Test loading custom values from environment variables."""
        settings = EmbeddingProviderSettings()
        assert settings.provider_type == EmbeddingProviderType.FASTEMBED
        assert settings.model_name == "custom_model"


class TestToolSettings:
    def test_default_values(self):
        """Test that default values are set correctly when no env vars are provided."""
        settings = ToolSettings()
        assert settings.tool_store_description == DEFAULT_TOOL_STORE_DESCRIPTION
        assert settings.tool_find_description == DEFAULT_TOOL_FIND_DESCRIPTION

    @patch.dict(
        os.environ,
        {"TOOL_STORE_DESCRIPTION": "Custom store description"},
    )
    def test_custom_store_description(self):
        """Test loading custom store description from environment variable."""
        settings = ToolSettings()
        assert settings.tool_store_description == "Custom store description"
        assert settings.tool_find_description == DEFAULT_TOOL_FIND_DESCRIPTION

    @patch.dict(
        os.environ,
        {"TOOL_FIND_DESCRIPTION": "Custom find description"},
    )
    def test_custom_find_description(self):
        """Test loading custom find description from environment variable."""
        settings = ToolSettings()
        assert settings.tool_store_description == DEFAULT_TOOL_STORE_DESCRIPTION
        assert settings.tool_find_description == "Custom find description"

    @patch.dict(
        os.environ,
        {
            "TOOL_STORE_DESCRIPTION": "Custom store description",
            "TOOL_FIND_DESCRIPTION": "Custom find description",
        },
    )
    def test_all_custom_values(self):
        """Test loading all custom values from environment variables."""
        settings = ToolSettings()
        assert settings.tool_store_description == "Custom store description"
        assert settings.tool_find_description == "Custom find description"


class TestSettings:
    def test_default_values(self):
        """Test that required fields raise errors when not provided."""
        with pytest.raises(ValueError):
            # Should raise error because required fields are missing
            Settings()

    @patch.dict(
        os.environ,
        {
            "QDRANT_URL": "http://localhost:6333",
            "COLLECTION_NAME": "test_collection",
        },
    )
    def test_minimal_config(self):
        """Test loading minimal configuration from environment variables."""
        settings = Settings()
        assert settings.qdrant_url == "http://localhost:6333"
        assert settings.collection_name == "test_collection"
        assert settings.embedding_provider == EmbeddingProviderType.FASTEMBED
        assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert settings.tool_store_description == DEFAULT_TOOL_STORE_DESCRIPTION
        assert settings.tool_find_description == DEFAULT_TOOL_FIND_DESCRIPTION
        assert settings.qdrant_api_key is None
        assert settings.qdrant_local_path is None

    @patch.dict(
        os.environ,
        {
            "QDRANT_URL": "http://qdrant.example.com:6333",
            "QDRANT_API_KEY": "test_api_key",
            "COLLECTION_NAME": "my_memories",
            "EMBEDDING_PROVIDER": "fastembed",
            "EMBEDDING_MODEL": "custom_model",
            "TOOL_STORE_DESCRIPTION": "Custom store description",
            "TOOL_FIND_DESCRIPTION": "Custom find description",
        },
    )
    def test_full_config_with_url(self):
        """Test loading full configuration from environment variables with URL."""
        settings = Settings()
        assert settings.qdrant_url == "http://qdrant.example.com:6333"
        assert settings.qdrant_api_key == "test_api_key"
        assert settings.collection_name == "my_memories"
        assert settings.qdrant_local_path is None
        assert settings.embedding_provider == EmbeddingProviderType.FASTEMBED
        assert settings.embedding_model == "custom_model"
        assert settings.tool_store_description == "Custom store description"
        assert settings.tool_find_description == "Custom find description"

    @patch.dict(
        os.environ,
        {
            "QDRANT_LOCAL_PATH": "/tmp/qdrant",
            "COLLECTION_NAME": "my_memories",
            "EMBEDDING_PROVIDER": "fastembed",
            "EMBEDDING_MODEL": "custom_model",
            "TOOL_STORE_DESCRIPTION": "Custom store description",
            "TOOL_FIND_DESCRIPTION": "Custom find description",
        },
    )
    def test_full_config_with_local_path(self):
        """Test loading full configuration from environment variables with local path."""
        settings = Settings()
        assert settings.qdrant_url is None
        assert settings.qdrant_api_key is None
        assert settings.collection_name == "my_memories"
        assert settings.qdrant_local_path == "/tmp/qdrant"
        assert settings.embedding_provider == EmbeddingProviderType.FASTEMBED
        assert settings.embedding_model == "custom_model"
        assert settings.tool_store_description == "Custom store description"
        assert settings.tool_find_description == "Custom find description"

    def test_get_qdrant_location(self):
        """Test the get_qdrant_location method."""
        # Test with URL
        settings = Settings(QDRANT_URL="http://example.com", COLLECTION_NAME="test")
        assert settings.get_qdrant_location() == "http://example.com"

        # Test with local path
        settings = Settings(QDRANT_LOCAL_PATH="/tmp/qdrant", COLLECTION_NAME="test")
        assert settings.get_qdrant_location() == "/tmp/qdrant"

        # Test with both (URL should take precedence)
        with pytest.raises(ValueError):
            Settings(
                QDRANT_URL="http://example.com",
                QDRANT_LOCAL_PATH="/tmp/qdrant",
                COLLECTION_NAME="test",
            )

        # Test with neither
        settings = Settings(COLLECTION_NAME="test")
        assert settings.get_qdrant_location() is None
