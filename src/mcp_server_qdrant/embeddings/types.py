from enum import Enum
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingProviderType(Enum):
    FASTEMBED = "fastembed"


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

    model_config = SettingsConfigDict(populate_by_name=True)
