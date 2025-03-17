import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from mcp_server_qdrant.embeddings.types import EmbeddingProviderType
from mcp_server_qdrant.settings import (
    DEFAULT_TOOL_FIND_DESCRIPTION,
    DEFAULT_TOOL_STORE_DESCRIPTION,
    QdrantSettings,
    ToolSettings,
    Settings,
)


class TestQdrantSettings:
    def test_default_values(self):
        """Test that required fields raise errors when not provided."""
        # Clear any environment variables that might provide default values
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError):
                QdrantSettings()

    @patch.dict(
        os.environ,
        {"QDRANT_URL": "http://localhost:6333", "COLLECTION_NAME": "test_collection"},
    )
    def test_minimal_config(self):
        """Test loading minimal configuration from environment variables."""
        settings = QdrantSettings()
        assert settings.qdrant_url == "http://localhost:6333"
        assert settings.collection_name == "test_collection"
        assert settings.qdrant_api_key is None
        assert settings.qdrant_local_path is None

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
        assert settings.qdrant_url is None  # URL should be None because local path is prioritized
        assert settings.qdrant_api_key == "test_api_key"
        assert settings.collection_name == "my_memories"
        assert settings.qdrant_local_path == "/tmp/qdrant"


class TestToolSettings:
    def test_default_values(self):
        """Test default values are set correctly."""
        settings = ToolSettings()
        assert settings.tool_store_description == DEFAULT_TOOL_STORE_DESCRIPTION
        assert settings.tool_find_description == DEFAULT_TOOL_FIND_DESCRIPTION

    @patch.dict(
        os.environ,
        {"TOOL_STORE_DESCRIPTION": "Custom store description"},
    )
    def test_custom_store_description(self):
        """Test custom store description."""
        settings = ToolSettings()
        assert settings.tool_store_description == "Custom store description"
        assert settings.tool_find_description == DEFAULT_TOOL_FIND_DESCRIPTION

    @patch.dict(
        os.environ,
        {"TOOL_FIND_DESCRIPTION": "Custom find description"},
    )
    def test_custom_find_description(self):
        """Test custom find description."""
        settings = ToolSettings()
        assert settings.tool_store_description == DEFAULT_TOOL_STORE_DESCRIPTION
        assert settings.tool_find_description == "Custom find description"


class TestSettings:
    def test_default_values(self):
        """Test that required fields raise errors when not provided."""
        # Clear any environment variables that might provide default values
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError):
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
        """Test loading full configuration with URL from environment variables."""
        settings = Settings()
        assert settings.qdrant_url == "http://qdrant.example.com:6333"
        assert settings.qdrant_api_key == "test_api_key"
        assert settings.collection_name == "my_memories"
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
        """Test loading full configuration with local path from environment variables."""
        settings = Settings()
        assert settings.qdrant_url is None
        assert settings.qdrant_local_path == "/tmp/qdrant"
        assert settings.collection_name == "my_memories"
        assert settings.embedding_provider == EmbeddingProviderType.FASTEMBED
        assert settings.embedding_model == "custom_model"
        assert settings.tool_store_description == "Custom store description"
        assert settings.tool_find_description == "Custom find description"

    def test_get_qdrant_location(self):
        """Test get_qdrant_location method."""
        with patch.dict(
            os.environ,
            {
                "QDRANT_URL": "http://localhost:6333",
                "COLLECTION_NAME": "test_collection",
            },
        ):
            settings = Settings()
            assert settings.get_qdrant_location() == "http://localhost:6333"

        with patch.dict(
            os.environ,
            {
                "QDRANT_LOCAL_PATH": "/tmp/qdrant",
                "COLLECTION_NAME": "test_collection",
            },
        ):
            settings = Settings()
            assert settings.get_qdrant_location() == "/tmp/qdrant"
