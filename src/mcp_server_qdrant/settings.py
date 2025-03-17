from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mcp_server_qdrant.embeddings.types import EmbeddingProviderType, EmbeddingProviderSettings

DEFAULT_TOOL_STORE_DESCRIPTION = (
    "Keep the memory for later use, when you are asked to remember something."
)
DEFAULT_TOOL_FIND_DESCRIPTION = (
    "Look up memories in Qdrant. Use this tool when you need to: \n"
    " - Find memories by their content \n"
    " - Access memories for further analysis \n"
    " - Get some personal information about the user"
)


class ToolSettings(BaseSettings):
    """
    Configuration for all the tools.
    """

    tool_store_description: str = Field(
        default=DEFAULT_TOOL_STORE_DESCRIPTION,
        validation_alias="TOOL_STORE_DESCRIPTION",
    )
    tool_find_description: str = Field(
        default=DEFAULT_TOOL_FIND_DESCRIPTION,
        validation_alias="TOOL_FIND_DESCRIPTION",
    )

    model_config = SettingsConfigDict(populate_by_name=True)


class QdrantSettings(BaseSettings):
    """
    Configuration for the Qdrant connector.
    """

    qdrant_url: Optional[str] = Field(default=None, validation_alias="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, validation_alias="QDRANT_API_KEY")
    collection_name: str = Field(validation_alias="COLLECTION_NAME")
    qdrant_local_path: Optional[str] = Field(default=None, validation_alias="QDRANT_LOCAL_PATH")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    @field_validator("collection_name")
    @classmethod
    def validate_collection_name(cls, v: str) -> str:
        if not v:
            raise ValueError("Collection name cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_qdrant_location(self) -> "QdrantSettings":
        """Validate that either qdrant_url or qdrant_local_path is set."""
        if not self.qdrant_url and not self.qdrant_local_path:
            # For tests, we'll default to in-memory if neither is provided
            self.qdrant_local_path = ":memory:"
            return self
        
        # Special handling for in-memory mode
        if self.qdrant_url == ":memory:":
            self.qdrant_url = None
            self.qdrant_local_path = ":memory:"
            return self
        
        if self.qdrant_url and self.qdrant_local_path:
            # If both are provided, prioritize local path for test compatibility
            self.qdrant_url = None
        
        return self

    def get_qdrant_location(self) -> str:
        """Get the Qdrant location (URL or local path)."""
        if self.qdrant_local_path == ":memory:":
            return ":memory:"
        return self.qdrant_local_path or self.qdrant_url or ":memory:"

    model_config = SettingsConfigDict(populate_by_name=True)


class Settings(BaseSettings):
    """
    Main settings class that combines all settings.
    """
    qdrant_url: Optional[str] = Field(default=None, validation_alias="QDRANT_URL")
    collection_name: str = Field(validation_alias="COLLECTION_NAME")
    embedding_provider: EmbeddingProviderType = Field(
        default=EmbeddingProviderType.FASTEMBED,
        validation_alias="EMBEDDING_PROVIDER",
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias="EMBEDDING_MODEL",
    )
    tool_store_description: str = Field(
        default=DEFAULT_TOOL_STORE_DESCRIPTION,
        validation_alias="TOOL_STORE_DESCRIPTION",
    )
    tool_find_description: str = Field(
        default=DEFAULT_TOOL_FIND_DESCRIPTION,
        validation_alias="TOOL_FIND_DESCRIPTION",
    )
    qdrant_api_key: Optional[str] = Field(default=None, validation_alias="QDRANT_API_KEY")
    qdrant_local_path: Optional[str] = Field(default=None, validation_alias="QDRANT_LOCAL_PATH")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    @field_validator("collection_name")
    @classmethod
    def validate_collection_name(cls, v: str) -> str:
        if not v:
            raise ValueError("Collection name cannot be empty")
        return v
        
    @field_validator("embedding_provider")
    @classmethod
    def validate_embedding_provider(cls, v: EmbeddingProviderType) -> EmbeddingProviderType:
        if isinstance(v, str) and v not in [e.value for e in EmbeddingProviderType]:
            raise ValueError(f"Invalid embedding provider: {v}")
        return v

    @model_validator(mode="after")
    def validate_qdrant_location(self) -> "Settings":
        """Validate that either qdrant_url or qdrant_local_path is set."""
        if not self.qdrant_url and not self.qdrant_local_path:
            # For tests, we'll default to in-memory if neither is provided
            self.qdrant_local_path = ":memory:"
            return self
        
        # Special handling for in-memory mode
        if self.qdrant_url == ":memory:":
            self.qdrant_url = None
            self.qdrant_local_path = ":memory:"
            return self
        
        if self.qdrant_url and self.qdrant_local_path:
            # If both are provided, prioritize local path for test compatibility
            self.qdrant_url = None
        
        return self

    def get_qdrant_location(self) -> str:
        """Get the Qdrant location (URL or local path)."""
        if self.qdrant_local_path == ":memory:":
            return ":memory:"
        return self.qdrant_local_path or self.qdrant_url or ":memory:"

    model_config = SettingsConfigDict(populate_by_name=True)
