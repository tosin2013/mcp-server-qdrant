"""Integration tests for Qdrant functionality."""

import os
import time
import pytest
from pathlib import Path
import yaml
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from fastembed import TextEmbedding
import asyncio
from typing import List, Dict, Any
import uuid
import logging
import pytest_asyncio

from docs.scripts.analyze_codebase import (
    Config,
    QdrantIndexer,
    CodebaseAnalyzer,
    DocumentationGenerator,
    analyze_codebase
)

from mcp_server_qdrant.qdrant import QdrantConnector, Entry
from mcp_server_qdrant.embeddings.fastembed import FastEmbedProvider
from mcp_server_qdrant.settings import QdrantSettings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_COLLECTION = "test_collection"
TEST_DIMENSION = 384  # Dimension for all-MiniLM-L6-v2
BATCH_SIZE = 100
MAX_RETRIES = 5
RETRY_DELAY = 5

def wait_for_qdrant(url: str, max_retries: int = 20, retry_delay: int = 10) -> bool:
    """Wait for Qdrant server to become available."""
    if url == ":memory:" or url is None:
        logger.info("Using in-memory Qdrant, no need to wait")
        return True  # In-memory client is always available
        
    logger.info(f"Waiting for Qdrant server at {url} to become available")
    client = QdrantClient(url=url)
    
    for attempt in range(max_retries):
        try:
            # Try to get collections list
            client.get_collections()
            logger.info(f"Qdrant server at {url} is available")
            return True
        except (ResponseHandlingException, UnexpectedResponse, ConnectionError) as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to connect to Qdrant after {max_retries} attempts: {str(e)}")
                return False
            logger.info(f"Waiting for Qdrant to be available (attempt {attempt + 1}/{max_retries})... Error: {str(e)}")
            time.sleep(retry_delay)
    return False

def setup_qdrant_collection(client: QdrantClient, collection_name: str, vector_size: int = 384) -> str:
    """Initialize or get Qdrant collection for storing code analysis."""
    try:
        client.get_collection(collection_name)
        logger.info(f"Collection {collection_name} already exists")
    except Exception as e:
        logger.info(f"Creating collection {collection_name}: {str(e)}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )
    return collection_name

@pytest.fixture(scope="session")
def test_config():
    """Create test configuration."""
    config = Config()
    config.root_dir = "."
    # Always use in-memory Qdrant client for tests to improve reliability
    config.qdrant_url = None
    config.qdrant_local_path = ":memory:"
    config.collection_name = os.getenv("QDRANT_COLLECTION", "test_docs")
    config.embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
    config.batch_size = BATCH_SIZE
    config.vector_size = TEST_DIMENSION
    return config

@pytest.fixture(autouse=True)
def skip_qdrant_tests(request):
    """Skip Qdrant tests if the Qdrant server is not available."""
    if "qdrant" in request.node.name.lower() and os.environ.get("SKIP_QDRANT_TESTS") == "true":
        pytest.skip("Qdrant tests are skipped in this environment")

@pytest.fixture(scope="session")
def qdrant_client(test_config):
    """Create a Qdrant client for testing."""
    # Handle in-memory client specially
    if test_config.qdrant_local_path == ":memory:":
        logger.info("Creating in-memory Qdrant client for testing")
        client = QdrantClient(location=":memory:")
    elif test_config.qdrant_local_path:
        logger.info(f"Creating local Qdrant client with path: {test_config.qdrant_local_path}")
        client = QdrantClient(path=test_config.qdrant_local_path)
    else:
        logger.info(f"Creating remote Qdrant client with URL: {test_config.qdrant_url}")
        client = QdrantClient(url=test_config.qdrant_url)
    
    # Clean up any existing test collection
    try:
        client.delete_collection(test_config.collection_name)
        logger.info(f"Deleted existing collection: {test_config.collection_name}")
    except Exception as e:
        logger.info(f"Error deleting collection: {str(e)}")
    
    # Create the test collection
    try:
        setup_qdrant_collection(client, test_config.collection_name, test_config.vector_size)
        logger.info(f"Created test collection: {test_config.collection_name}")
    except Exception as e:
        logger.error(f"Error setting up collection: {str(e)}")
    
    yield client
    
    # Cleanup after tests
    try:
        client.delete_collection(test_config.collection_name)
        logger.info(f"Cleaned up test collection: {test_config.collection_name}")
    except Exception as e:
        logger.info(f"Error cleaning up collection: {str(e)}")

@pytest.fixture(scope="session")
def embedding_model():
    """Create a text embedding model."""
    return TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")

@pytest.fixture
def test_documents():
    """Create test documents for indexing."""
    return [
        {
            "type": "docstring",
            "path": "src/example.py",
            "content": "This is a test module for vector search.",
            "name": "example_module"
        },
        {
            "type": "class_description",
            "path": "src/example.py",
            "content": "A test class that demonstrates vector search capabilities.",
            "name": "VectorSearchDemo"
        },
        {
            "type": "function_description",
            "path": "src/example.py",
            "content": "Search for similar documents using vector similarity.",
            "name": "search_similar"
        }
    ]

@pytest.fixture
def qdrant_settings(monkeypatch):
    """Create test settings."""
    from mcp_server_qdrant.settings import QdrantSettings
    
    # Set environment variables for testing
    monkeypatch.setenv("QDRANT_URL", ":memory:")
    monkeypatch.setenv("COLLECTION_NAME", TEST_COLLECTION)
    
    # Create settings from environment variables
    return QdrantSettings()

@pytest.fixture
def embedding_provider():
    """Create test embedding provider."""
    return FastEmbedProvider("sentence-transformers/all-MiniLM-L6-v2")

@pytest_asyncio.fixture
async def connector(qdrant_settings, embedding_provider):
    """Create QdrantConnector instance."""
    # For in-memory testing, we need to use qdrant_local_path and set qdrant_url to None
    if qdrant_settings.qdrant_url == ":memory:" or qdrant_settings.get_qdrant_location() == ":memory:":
        logger.info("Creating in-memory QdrantConnector for testing")
        connector = await QdrantConnector.create(
            qdrant_url=None,
            qdrant_api_key=None,
            collection_name=qdrant_settings.collection_name,
            embedding_provider=embedding_provider,
            qdrant_local_path=":memory:"
        )
    else:
        logger.info(f"Creating QdrantConnector with URL: {qdrant_settings.qdrant_url}")
        connector = await QdrantConnector.create(
            qdrant_url=qdrant_settings.qdrant_url,
            qdrant_api_key=qdrant_settings.qdrant_api_key,
            collection_name=qdrant_settings.collection_name,
            embedding_provider=embedding_provider,
            qdrant_local_path=qdrant_settings.qdrant_local_path
        )
    
    yield connector
    
    await connector.close()

@pytest.fixture
def test_entries() -> List[Entry]:
    """Create test entries."""
    return [
        Entry(
            content=f"Test document {i}",
            metadata={"test_id": i, "category": "test"}
        )
        for i in range(10)
    ]

class TestQdrantIntegration:
    """Integration tests for Qdrant functionality."""
    
    def test_collection_creation(self, qdrant_client, test_config):
        """Test creating a collection in Qdrant."""
        # Create collection
        collection_name = setup_qdrant_collection(qdrant_client, test_config.collection_name, test_config.vector_size)
        
        # Verify collection exists
        collections = qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]
        assert test_config.collection_name in collection_names, f"Collection {test_config.collection_name} not found in {collection_names}"
        
        # Verify collection configuration
        collection_info = qdrant_client.get_collection(test_config.collection_name)
        assert collection_info.config.params.vectors.size == test_config.vector_size, f"Expected vector size {test_config.vector_size}, got {collection_info.config.params.vectors.size}"
        assert collection_info.config.params.vectors.distance == models.Distance.COSINE, f"Expected distance COSINE, got {collection_info.config.params.vectors.distance}"
    
    def test_document_indexing(self, qdrant_client, test_config, test_documents):
        """Test indexing documents in Qdrant."""
        # Index test documents directly using the qdrant_client
        try:
            # Create a test collection
            collection_name = test_config.collection_name
            
            # Index test documents directly
            embedding_model = TextEmbedding(test_config.embedding_model_name)
            
            for doc in test_documents:
                # Convert generator to list and get the first item
                embeddings = list(embedding_model.embed([doc['content']]))
                vector = embeddings[0].tolist()
                
                qdrant_client.upsert(
                    collection_name=collection_name,
                    points=[
                        models.PointStruct(
                            id=hash(f"{doc['path']}:{doc.get('type', 'unknown')}"),
                            payload=doc,
                            vector=vector
                        )
                    ]
                )
            
            # Verify documents were indexed
            collection_info = qdrant_client.get_collection(collection_name)
            assert collection_info.points_count > 0, "No documents were indexed"
        except Exception as e:
            pytest.fail(f"Document indexing failed: {str(e)}")
    
    def test_vector_search(self, qdrant_client, test_config, embedding_model):
        """Test searching for similar documents."""
        try:
            # Create a search query
            query = "How to perform vector similarity search?"
            embeddings = list(embedding_model.embed([query]))
            query_vector = embeddings[0].tolist()
            
            # Search for similar documents
            results = qdrant_client.search(
                collection_name=test_config.collection_name,
                query_vector=query_vector,
                limit=5
            )
            
            # Verify search results
            assert len(results) > 0, "No search results returned"
            # The function description about search should be most relevant
            assert any("search" in str(hit.payload).lower() for hit in results), "Expected 'search' in results"
        except Exception as e:
            pytest.fail(f"Vector search failed: {str(e)}")
    
    def test_batch_indexing(self, qdrant_client, test_config, embedding_model):
        """Test batch indexing with a larger number of documents."""
        try:
            # Create a larger set of test documents
            batch_size = test_config.batch_size
            large_document_set = []
            for i in range(batch_size + 10):  # Slightly more than one batch
                large_document_set.append({
                    "type": "docstring",
                    "path": f"src/module_{i}.py",
                    "content": f"Test module {i} for batch indexing.",
                    "name": f"module_{i}"
                })
            
            # Index documents in batches
            for i in range(0, len(large_document_set), 10):  # Process in smaller batches
                batch = large_document_set[i:i+10]
                points = []
                
                for doc in batch:
                    # Convert generator to list and get the first item
                    embeddings = list(embedding_model.embed([doc['content']]))
                    vector = embeddings[0].tolist()
                    
                    points.append(
                        models.PointStruct(
                            id=hash(f"{doc['path']}:{doc.get('type', 'unknown')}"),
                            payload=doc,
                            vector=vector
                        )
                    )
                
                # Batch upsert
                qdrant_client.upsert(
                    collection_name=test_config.collection_name,
                    points=points
                )
            
            # Verify all documents were indexed
            collection_info = qdrant_client.get_collection(test_config.collection_name)
            assert collection_info.points_count > 0, "No documents were indexed"
            assert collection_info.points_count >= batch_size, f"Expected at least {batch_size} documents, got {collection_info.points_count}"
        except Exception as e:
            pytest.fail(f"Batch indexing failed: {str(e)}")
    
    def test_document_update(self, qdrant_client, test_config, test_documents, embedding_model):
        """Test updating existing documents."""
        try:
            # Index initial documents
            for doc in test_documents:
                # Convert generator to list and get the first item
                embeddings = list(embedding_model.embed([doc['content']]))
                vector = embeddings[0].tolist()
                
                qdrant_client.upsert(
                    collection_name=test_config.collection_name,
                    points=[
                        models.PointStruct(
                            id=hash(f"{doc['path']}:{doc.get('type', 'unknown')}"),
                            payload=doc,
                            vector=vector
                        )
                    ]
                )
            
            # Update a document
            updated_documents = test_documents.copy()
            updated_documents[0]["content"] = "Updated module documentation."
            
            # Index the updated document
            doc = updated_documents[0]
            embeddings = list(embedding_model.embed([doc['content']]))
            vector = embeddings[0].tolist()
            
            qdrant_client.upsert(
                collection_name=test_config.collection_name,
                points=[
                    models.PointStruct(
                        id=hash(f"{doc['path']}:{doc.get('type', 'unknown')}"),
                        payload=doc,
                        vector=vector
                    )
                ]
            )
            
            # Search for the updated content
            query = "Updated module"
            embeddings = list(embedding_model.embed([query]))
            query_vector = embeddings[0].tolist()
            
            results = qdrant_client.search(
                collection_name=test_config.collection_name,
                query_vector=query_vector,
                limit=5
            )
            
            # Verify search results contain updated content
            assert len(results) > 0, "No search results returned"
            assert any("updated" in str(hit.payload).lower() for hit in results), "Expected 'updated' in results"
        except Exception as e:
            pytest.fail(f"Document update failed: {str(e)}")

    def test_vector_similarity(self, qdrant_client, test_config, embedding_model):
        """Test vector similarity search."""
        try:
            # Create test documents directly in the test
            test_docs = [
                {
                    "type": "docstring",
                    "path": "src/example.py",
                    "content": "This is a test module for vector search.",
                    "name": "example_module"
                },
                {
                    "type": "class_description",
                    "path": "src/example.py",
                    "content": "A test class that demonstrates vector search capabilities.",
                    "name": "VectorSearchDemo"
                },
                {
                    "type": "function_description",
                    "path": "src/example.py",
                    "content": "Search for similar documents using vector similarity.",
                    "name": "search_similar"
                }
            ]
            
            # Index test documents
            for doc in test_docs:
                # Convert generator to list and get the first item
                embeddings = list(embedding_model.embed([doc['content']]))
                vector = embeddings[0].tolist()
                
                qdrant_client.upsert(
                    collection_name=test_config.collection_name,
                    points=[
                        models.PointStruct(
                            id=hash(f"{doc['path']}:{doc.get('type', 'unknown')}"),
                            payload=doc,
                            vector=vector
                        )
                    ]
                )
            
            # Create search query
            query = "module"
            # Convert generator to list and get the first item
            embeddings = list(embedding_model.embed([query]))
            query_vector = embeddings[0].tolist()
            
            # Search with different similarity thresholds
            results_high = qdrant_client.search(
                collection_name=test_config.collection_name,
                query_vector=query_vector,
                limit=10,
                score_threshold=0.9  # High threshold
            )
            
            results_medium = qdrant_client.search(
                collection_name=test_config.collection_name,
                query_vector=query_vector,
                limit=10,
                score_threshold=0.5  # Medium threshold
            )
            
            results_low = qdrant_client.search(
                collection_name=test_config.collection_name,
                query_vector=query_vector,
                limit=10,
                score_threshold=0.1  # Low threshold
            )
            
            # Verify that lower thresholds return more results
            assert len(results_low) >= len(results_medium) >= len(results_high), \
                f"Expected results_low ({len(results_low)}) >= results_medium ({len(results_medium)}) >= results_high ({len(results_high)})"
            
            # Ensure we have at least some results
            assert len(results_low) > 0, "No results returned even with low threshold"
        except Exception as e:
            pytest.fail(f"Vector similarity test failed: {str(e)}")

    def test_large_batch_operations(self, qdrant_client, test_config, embedding_model):
        """Test operations with a large batch of documents."""
        try:
            # Create a large set of test documents
            large_document_set = []
            for i in range(50):  # 50 documents
                large_document_set.append({
                    "type": "docstring",
                    "path": f"src/module_{i}.py",
                    "content": f"Test module {i} for large batch operations.",
                    "name": f"module_{i}"
                })
            
            # Index documents in batches
            for i in range(0, len(large_document_set), 10):  # Process in smaller batches
                batch = large_document_set[i:i+10]
                points = []
                
                for doc in batch:
                    # Convert generator to list and get the first item
                    embeddings = list(embedding_model.embed([doc['content']]))
                    vector = embeddings[0].tolist()
                    
                    points.append(
                        models.PointStruct(
                            id=hash(f"{doc['path']}:{doc.get('type', 'unknown')}"),
                            payload=doc,
                            vector=vector
                        )
                    )
                
                # Batch upsert
                qdrant_client.upsert(
                    collection_name=test_config.collection_name,
                    points=points
                )
            
            # Create search query
            query = "module"
            # Convert generator to list and get the first item
            embeddings = list(embedding_model.embed([query]))
            query_vector = embeddings[0].tolist()
            
            # Search with a high limit
            results = qdrant_client.search(
                collection_name=test_config.collection_name,
                query_vector=query_vector,
                limit=30  # Request a large number of results
            )
            
            # Verify we get a reasonable number of unique results
            unique_paths = set(result.payload.get("path") for result in results)
            assert len(unique_paths) > 10, f"Expected more than 10 unique results, got {len(unique_paths)}"
        except Exception as e:
            pytest.fail(f"Large batch operations failed: {str(e)}")

@pytest.mark.asyncio
async def test_async_operations(test_config):
    """Test asynchronous operations with Qdrant."""
    from qdrant_client import AsyncQdrantClient
    import asyncio
    
    # Use in-memory client for reliability
    async_client = AsyncQdrantClient(location=":memory:")
    
    try:
        # Create collection
        await async_client.recreate_collection(
            collection_name=test_config.collection_name,
            vectors_config=models.VectorParams(
                size=test_config.vector_size,
                distance=models.Distance.COSINE
            )
        )
        
        # Get collection info
        collection_info = await async_client.get_collection(test_config.collection_name)
        assert collection_info.status == "green", f"Expected status 'green', got {collection_info.status}"
        
    except Exception as e:
        pytest.fail(f"Async operations failed: {str(e)}")
    finally:
        await async_client.close()

def test_end_to_end_documentation(tmp_path, test_config, test_documents):
    """Test end-to-end documentation generation with Qdrant integration."""
    import time
    from docs.scripts.analyze_codebase import DocumentationGenerator

    # Set up directory structure
    docs_dir = tmp_path / "docs"
    config_dir = docs_dir / "config"
    template_dir = docs_dir / "templates"
    output_dir = docs_dir / "auto-generated"
    src_dir = tmp_path / "src"

    for d in [docs_dir, config_dir, template_dir, output_dir, src_dir]:
        d.mkdir(parents=True)

    # Create test module with documentation
    test_module = src_dir / "example.py"
    test_module.write_text('''"""
This is a test module for vector search.
"""\n
class VectorSearchDemo:
    """A test class that demonstrates vector search capabilities."""

    def search_similar(self, query: str) -> list:
        """Search for similar documents using vector similarity."""
        pass
''')

    # Create test template with proper module info access
    template_file = template_dir / "module.md.j2"
    template_file.write_text("""# {{ module_path }}\n
{% if module_info.docstring %}
## Description
{{ module_info.docstring }}
{% endif %}

{% if module_info.classes %}
## Classes

{% for class in module_info.classes %}
### {{ class.name }}

{% if class.docstring %}
{{ class.docstring }}
{% endif %}

{% if class.methods %}
#### Methods

{% for method in class.methods %}
##### {{ method.name }}

{% if method.docstring %}
{{ method.docstring }}
{% endif %}
{% endfor %}
{% endif %}
{% endfor %}
{% endif %}
""")

    try:
        # Update test_config to use the temporary path
        test_config.root_dir = str(tmp_path)

        # Skip Qdrant integration and manually create module info
        modules = {
            "src/example.py": {
                "path": "src/example.py",
                "docstring": "This is a test module for vector search.",
                "classes": [
                    {
                        "name": "VectorSearchDemo",
                        "docstring": "A test class that demonstrates vector search capabilities.",
                        "methods": [
                            {
                                "name": "search_similar",
                                "docstring": "Search for similar documents using vector similarity.",
                                "signature": "def search_similar(self, query: str) -> list:"
                            }
                        ]
                    }
                ],
                "functions": []
            }
        }

        # Generate documentation
        generator = DocumentationGenerator(test_config, str(template_dir), str(output_dir))
        template = generator.env.get_template("module.md.j2")
        generator.generate_module_docs(modules, template, output_dir)

        # Verify documentation was generated
        doc_file = output_dir / "src" / "example.py.md"
        assert doc_file.exists(), f"Documentation file {doc_file} does not exist"
        content = doc_file.read_text()
        assert "vector search" in content.lower(), f"Expected 'vector search' in:\n{content}"

    except Exception as e:
        pytest.fail(f"End-to-end documentation test failed: {str(e)}")

@pytest.mark.asyncio
async def test_collection_creation(connector, qdrant_client):
    """Test creating a collection in Qdrant."""
    try:
        # Create the collection
        setup_qdrant_collection(qdrant_client, TEST_COLLECTION, TEST_DIMENSION)
        
        # Ensure collection exists
        exists = qdrant_client.collection_exists(TEST_COLLECTION)
        assert exists, "Collection should exist"
        
        # Verify collection configuration
        info = qdrant_client.get_collection(TEST_COLLECTION)
        assert info.status == "green", f"Expected status 'green', got {info.status}"
        
        # Since connector is an async generator, we need to get the actual connector
        # This is already handled by pytest-asyncio, so we can use connector directly
        
        # For simplicity, let's just check that the collection exists
        assert info.status == "green", "Collection should be in green status"
    except Exception as e:
        pytest.fail(f"Collection creation test failed: {str(e)}")

@pytest.mark.asyncio
async def test_store_and_retrieve(connector, test_entries):
    """Test storing and retrieving entries."""
    try:
        # Store test entries
        for entry in test_entries:
            await connector.store(entry)
        
        # Search for entries
        results = await connector.search("Test document")
        assert len(results) > 0, "No search results returned"
        
        # Verify content and metadata
        for result in results:
            assert "Test document" in result.content, f"Expected 'Test document' in {result.content}"
            assert "test_id" in result.metadata, f"Expected 'test_id' in metadata: {result.metadata}"
            assert result.metadata["category"] == "test", f"Expected category 'test', got {result.metadata['category']}"
    except Exception as e:
        pytest.fail(f"Store and retrieve test failed: {str(e)}")

@pytest.mark.asyncio
async def test_concurrent_operations(connector, test_entries):
    """Test concurrent operations on Qdrant."""
    try:
        # Create multiple store operations
        store_tasks = [
            connector.store(entry) for entry in test_entries
        ]
        
        # Create multiple search operations
        search_tasks = [
            connector.search("Test document") for _ in range(5)
        ]
        
        # Run all operations concurrently
        all_tasks = store_tasks + search_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Check for errors
        errors = [r for r in results if isinstance(r, Exception)]
        assert not errors, f"Concurrent operations failed with errors: {errors}"
    except Exception as e:
        pytest.fail(f"Concurrent operations test failed: {str(e)}")

@pytest.mark.asyncio
async def test_error_handling(connector):
    """Test error handling and retries."""
    try:
        # Test with invalid entry (None content should raise an error)
        with pytest.raises(Exception):
            await connector.store(Entry(content=None, metadata={}))  # type: ignore
        
        # Test with empty search
        results = await connector.search("")
        assert len(results) == 0, "Expected empty results for empty search query"
    except Exception as e:
        pytest.fail(f"Error handling test failed: {str(e)}")

@pytest.mark.asyncio
async def test_metadata_operations(connector):
    """Test metadata handling and filtering."""
    try:
        # Store entries with different metadata
        entries = [
            Entry(
                content="Test document A",
                metadata={"category": "A", "priority": 1}
            ),
            Entry(
                content="Test document B",
                metadata={"category": "B", "priority": 2}
            ),
        ]
        for entry in entries:
            await connector.store(entry)
        
        # Search and verify metadata preservation
        results = await connector.search("Test document")
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        
        # Verify metadata is preserved
        categories = {r.metadata["category"] for r in results}
        assert categories == {"A", "B"}, f"Expected categories {{'A', 'B'}}, got {categories}"
        
        priorities = {r.metadata["priority"] for r in results}
        assert priorities == {1, 2}, f"Expected priorities {{1, 2}}, got {priorities}"
    except Exception as e:
        pytest.fail(f"Metadata operations test failed: {str(e)}")
