import logging
import uuid
from typing import Any, Dict, Optional, List
import asyncio
from functools import wraps
import backoff

from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import ResponseHandlingException

from mcp_server_qdrant.embeddings.base import EmbeddingProvider
from mcp_server_qdrant.embeddings.factory import create_embedding_provider
from mcp_server_qdrant.settings import QdrantSettings

logger = logging.getLogger(__name__)

Metadata = Dict[str, Any]

# Maximum number of retries for operations
MAX_RETRIES = 3
# Base delay for exponential backoff (in seconds)
BASE_DELAY = 1
# Maximum delay between retries (in seconds)
MAX_DELAY = 10
# Maximum size of the connection pool
MAX_POOL_SIZE = 10

def with_retry(func):
    """Decorator to add retry logic to Qdrant operations."""
    @wraps(func)
    @backoff.on_exception(
        backoff.expo,
        (ResponseHandlingException, ConnectionError),
        max_tries=MAX_RETRIES,
        max_time=30,
        base=BASE_DELAY,
        max_value=MAX_DELAY,
    )
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Operation failed after {MAX_RETRIES} retries: {str(e)}")
            raise
    return wrapper

class Entry(BaseModel):
    """
    A single entry in the Qdrant collection.
    """
    content: str
    metadata: Optional[Metadata] = None

class QdrantConnector:
    """
    Encapsulates the connection to a Qdrant server and all the methods to interact with it.
    Implements connection pooling and retry logic for resilience.
    """
    def __init__(
        self,
        qdrant_url: str,
        qdrant_api_key: str | None,
        collection_name: str,
        embedding_provider: EmbeddingProvider,
        qdrant_local_path: str | None = None,
        max_pool_size: int = MAX_POOL_SIZE,
    ):
        self.qdrant_url = qdrant_url
        self.qdrant_api_key = qdrant_api_key
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider
        self.qdrant_local_path = qdrant_local_path
        self.max_pool_size = max_pool_size
        self._connection_semaphore = asyncio.Semaphore(max_pool_size)
        self._init_client()

    def _init_client(self):
        """Initialize the Qdrant client with proper configuration."""
        # Special handling for in-memory mode
        if self.qdrant_local_path == ":memory:" or self.qdrant_url == ":memory:":
            logger.info("Using in-memory Qdrant client")
            self.client = AsyncQdrantClient(
                location=":memory:",
                timeout=30.0  # Increased timeout for stability
            )
        elif self.qdrant_local_path:
            logger.info(f"Using local path Qdrant client: {self.qdrant_local_path}")
            self.client = AsyncQdrantClient(
                path=self.qdrant_local_path,
                timeout=30.0  # Increased timeout for stability
            )
        else:
            logger.info(f"Using remote Qdrant client: {self.qdrant_url}")
            self.client = AsyncQdrantClient(
                url=self.qdrant_url,
                api_key=self.qdrant_api_key,
                timeout=30.0,
                prefer_grpc=True  # Use gRPC for better performance
            )

    @classmethod
    async def create(
        cls,
        qdrant_url: str,
        qdrant_api_key: str | None,
        collection_name: str,
        embedding_provider: EmbeddingProvider,
        qdrant_local_path: str | None = None,
        max_pool_size: int = MAX_POOL_SIZE,
    ) -> "QdrantConnector":
        """Create a new QdrantConnector instance and initialize the collection."""
        # Handle special case for in-memory mode
        if qdrant_url == ":memory:":
            qdrant_url = None
            qdrant_local_path = ":memory:"
            
        instance = cls(
            qdrant_url=qdrant_url,
            qdrant_api_key=qdrant_api_key,
            collection_name=collection_name,
            embedding_provider=embedding_provider,
            qdrant_local_path=qdrant_local_path,
            max_pool_size=max_pool_size,
        )
        await instance._ensure_collection_exists()
        return instance

    @with_retry
    async def _ensure_collection_exists(self):
        """Ensure that the collection exists, creating it if necessary."""
        async with self._connection_semaphore:
            try:
                collection_exists = await self.client.collection_exists(self.collection_name)
                if not collection_exists:
                    logger.info(f"Creating collection: {self.collection_name}")
                    sample_vector = await self.embedding_provider.embed_query("sample text")
                    vector_size = len(sample_vector)
                    vector_name = self.embedding_provider.get_vector_name()
                    
                    # Create collection with optimized configuration
                    await self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config={
                            vector_name: models.VectorParams(
                                size=vector_size,
                                distance=models.Distance.COSINE,
                                on_disk=True,  # Store vectors on disk for large datasets
                            )
                        },
                        optimizers_config=models.OptimizersConfigDiff(
                            indexing_threshold=20000,  # Optimize for larger datasets
                            memmap_threshold=10000,
                        ),
                        hnsw_config=models.HnswConfigDiff(
                            m=16,  # Increased for better recall
                            ef_construct=100,  # Balanced build time vs quality
                            full_scan_threshold=10000,
                        ),
                    )
                    logger.info(f"Collection {self.collection_name} created successfully")
                else:
                    logger.info(f"Collection {self.collection_name} already exists")
            except Exception as e:
                logger.error(f"Error ensuring collection exists: {str(e)}")
                raise

    @with_retry
    async def store(self, entry: Entry):
        """Store information in the Qdrant collection with retry logic."""
        async with self._connection_semaphore:
            await self._ensure_collection_exists()
            embeddings = await self.embedding_provider.embed_documents([entry.content])
            vector_name = self.embedding_provider.get_vector_name()
            
            # Add to Qdrant with optimized payload
            payload = {
                "document": entry.content,
                "metadata": entry.metadata,
                "timestamp": str(uuid.uuid1()),  # Add timestamp for versioning
            }
            
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=uuid.uuid4().hex,
                        vector={vector_name: embeddings[0]},
                        payload=payload,
                    )
                ],
            )
            logger.debug(f"Stored entry in collection {self.collection_name}")

    @with_retry
    async def search(self, query: str, limit: int = 10) -> List[Entry]:
        """Find points in the Qdrant collection with retry logic."""
        async with self._connection_semaphore:
            collection_exists = await self.client.collection_exists(self.collection_name)
            if not collection_exists:
                logger.warning(f"Collection {self.collection_name} does not exist, returning empty results")
                return []

            query_vector = await self.embedding_provider.embed_query(query)
            vector_name = self.embedding_provider.get_vector_name()

            # Optimized search with better parameters
            search_results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=models.NamedVector(name=vector_name, vector=query_vector),
                limit=limit,
                score_threshold=0.7,  # Add minimum similarity threshold
                with_payload=True,
                search_params=models.SearchParams(
                    hnsw_ef=128,  # Increased for better recall
                    exact=False,  # Use approximate search for better performance
                ),
            )

            logger.debug(f"Found {len(search_results)} results for query: {query}")
            return [
                Entry(
                    content=result.payload["document"],
                    metadata=result.payload.get("metadata"),
                )
                for result in search_results
            ]

    async def close(self):
        """Properly close the Qdrant client connection."""
        if hasattr(self, 'client'):
            await self.client.close()

async def get_qdrant_client() -> QdrantConnector:
    """Get a QdrantConnector instance configured with settings from environment variables."""
    settings = QdrantSettings()
    embedding_provider = create_embedding_provider(settings.embedding_provider)
    
    # Handle special case for in-memory mode
    qdrant_url = settings.qdrant_url
    qdrant_local_path = settings.qdrant_local_path
    
    if qdrant_url == ":memory:":
        qdrant_url = None
        qdrant_local_path = ":memory:"
    
    return await QdrantConnector.create(
        qdrant_url=qdrant_url,
        qdrant_api_key=settings.qdrant_api_key,
        collection_name=settings.collection_name,
        embedding_provider=embedding_provider,
        qdrant_local_path=qdrant_local_path,
    )
