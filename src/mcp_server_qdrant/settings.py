from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

from mcp_server_qdrant.embeddings.types import EmbeddingProviderType

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


class EmbeddingProviderSettings(BaseSettings):
    """
    Configuration for the embedding provider.
    """

    provider_type: EmbeddingProviderType = Field(
        default=EmbeddingProviderType.FASTEMBED,
        validation_alias="EMBEDDING_PROVIDER",
    )
    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias="EMBEDDING_MODEL",
    )


class QdrantSettings(BaseSettings):
    """
    Configuration for the Qdrant connector.
    """

    location: Optional[str] = Field(default=None, validation_alias="QDRANT_URL")
    api_key: Optional[str] = Field(default=None, validation_alias="QDRANT_API_KEY")
    collection_name: str = Field(validation_alias="COLLECTION_NAME")
    local_path: Optional[str] = Field(
        default=None, validation_alias="QDRANT_LOCAL_PATH"
    )

    def get_qdrant_location(self) -> str:
        """
        Get the Qdrant location, either the URL or the local path.
        """
        return self.location or self.local_path


class Settings(BaseSettings):
    """
    Main settings class that combines all settings.
    """
    qdrant_url: Optional[str] = Field(default=None, alias="QDRANT_URL")
    collection_name: str = Field(alias="COLLECTION_NAME")
    embedding_provider: EmbeddingProviderType = Field(
        default=EmbeddingProviderType.FASTEMBED,
        alias="EMBEDDING_PROVIDER",
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )
    tool_store_description: str = Field(
        default=DEFAULT_TOOL_STORE_DESCRIPTION,
        alias="TOOL_STORE_DESCRIPTION",
    )
    tool_find_description: str = Field(
        default=DEFAULT_TOOL_FIND_DESCRIPTION,
        alias="TOOL_FIND_DESCRIPTION",
    )
    qdrant_api_key: Optional[str] = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_local_path: Optional[str] = Field(default=None, alias="QDRANT_LOCAL_PATH")

    @field_validator("collection_name")
    @classmethod
    def validate_collection_name(cls, v: str) -> str:
        """Validate collection name is not empty."""
        if not v:
            raise ValueError("Collection name cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_qdrant_location(self) -> "Settings":
        """Validate Qdrant location."""
        if self.qdrant_url and self.qdrant_local_path:
            raise ValueError("Cannot specify both qdrant_url and qdrant_local_path")
        return self

    def get_qdrant_location(self) -> Optional[str]:
        """
        Get the Qdrant location, either the URL or the local path.
        """
        return self.qdrant_url or self.qdrant_local_path

    class Config:
        populate_by_name = True
