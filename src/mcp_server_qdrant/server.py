import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, List, Dict, Any, Optional
import asyncio
from uuid import UUID
from datetime import datetime

from mcp.server import Server
from mcp.server.fastmcp import Context, FastMCP

from mcp_server_qdrant.embeddings.factory import create_embedding_provider
from mcp_server_qdrant.qdrant import Entry, Metadata, QdrantConnector, get_qdrant_client
from mcp_server_qdrant.settings import (
    EmbeddingProviderSettings,
    QdrantSettings,
    ToolSettings,
)

from .services.task_manager import MCPTaskManager
from .models.task import TestResult
from .utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[dict]:
    """
    Context manager to handle the lifespan of the server.
    This is used to configure the embedding provider and Qdrant connector.
    All the configuration is now loaded from the environment variables.
    Settings handle that for us.
    """
    qdrant_connector = None
    try:
        # Embedding provider is created with a factory function so we can add
        # some more providers in the future. Currently, only FastEmbed is supported.
        embedding_provider_settings = EmbeddingProviderSettings()
        embedding_provider = create_embedding_provider(embedding_provider_settings)
        logger.info(
            f"Using embedding provider {embedding_provider_settings.provider_type} with "
            f"model {embedding_provider_settings.model_name}"
        )

        qdrant_configuration = QdrantSettings()
        logger.info(
            f"Connecting to Qdrant at {qdrant_configuration.get_qdrant_location()}"
        )
        
        # Implement retry mechanism for connecting to Qdrant
        max_retries = 10
        retry_delay = 5  # seconds
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Attempting to connect to Qdrant (attempt {attempt}/{max_retries})...")
                qdrant_connector = await QdrantConnector.create(
                    qdrant_url=qdrant_configuration.qdrant_url,
                    qdrant_api_key=qdrant_configuration.qdrant_api_key,
                    collection_name=qdrant_configuration.collection_name,
                    embedding_provider=embedding_provider,
                    qdrant_local_path=qdrant_configuration.qdrant_local_path,
                )
                logger.info("Successfully connected to Qdrant!")
                break
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Failed to connect to Qdrant: {e}. Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Failed to connect to Qdrant after {max_retries} attempts: {e}")
                    raise

        yield {
            "embedding_provider": embedding_provider,
            "qdrant_connector": qdrant_connector,
        }
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise
    finally:
        if qdrant_connector:
            try:
                await qdrant_connector.client.close()
                logger.info("Qdrant connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing Qdrant connection: {e}")


# FastMCP is an alternative interface for declaring the capabilities
# of the server. Its API is based on FastAPI.
mcp = FastMCP("mcp-server-qdrant", lifespan=server_lifespan)

# Load the tool settings from the env variables, if they are set,
# or use the default values otherwise.
tool_settings = ToolSettings()


@mcp.tool(name="qdrant-store", description=tool_settings.tool_store_description)
async def store(
    ctx: Context,
    information: str,
    # The `metadata` parameter is defined as non-optional, but it can be None.
    # If we set it to be optional, some of the MCP clients, like Cursor, cannot
    # handle the optional parameter correctly.
    metadata: Metadata = None,
) -> str:
    """
    Store some information in Qdrant.
    :param ctx: The context for the request.
    :param information: The information to store.
    :param metadata: JSON metadata to store with the information, optional.
    :return: A message indicating that the information was stored.
    """
    await ctx.debug(f"Storing information {information} in Qdrant")
    qdrant_connector: QdrantConnector = ctx.request_context.lifespan_context[
        "qdrant_connector"
    ]
    entry = Entry(content=information, metadata=metadata)
    await qdrant_connector.store(entry)
    return f"Remembered: {information}"


@mcp.tool(name="qdrant-find", description=tool_settings.tool_find_description)
async def find(ctx: Context, query: str) -> List[str]:
    """
    Find memories in Qdrant.
    :param ctx: The context for the request.
    :param query: The query to use for the search.
    :return: A list of entries found.
    """
    await ctx.debug(f"Finding results for query {query}")
    qdrant_connector: QdrantConnector = ctx.request_context.lifespan_context[
        "qdrant_connector"
    ]
    entries = await qdrant_connector.search(query)
    if not entries:
        return [f"No information found for the query '{query}'"]
    content = [
        f"Results for the query '{query}'",
    ]
    for entry in entries:
        # Format the metadata as a JSON string and produce XML-like output
        entry_metadata = json.dumps(entry.metadata) if entry.metadata else ""
        content.append(
            f"<entry><content>{entry.content}</content><metadata>{entry_metadata}</metadata></entry>"
        )
    return content


class MCPServer:
    """MCP Server implementation for task management."""

    def __init__(self):
        self.task_manager = None
        self.tools = {
            "handle_test_failure": self.handle_test_failure,
            "get_task": self.get_task,
            "update_task": self.update_task,
            "search_similar_tasks": self.search_similar_tasks,
            "health_check": self.health_check
        }

    async def initialize(self):
        """Initialize the server with Qdrant client."""
        client = await get_qdrant_client()
        self.task_manager = MCPTaskManager(client)

    async def handle_test_failure(
        self,
        test_name: str,
        error_message: str,
        context: Optional[Dict] = None,
        platform: Optional[str] = None,
        container_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """MCP tool to handle test failures and create tasks."""
        test_result = TestResult(
            name=test_name,
            error=error_message,
            context=context or {},
            platform=platform,
            container_id=container_id
        )
        return await self.task_manager.handle_test_failure(test_result)

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """MCP tool to retrieve task details."""
        task = await self.task_manager.get_task(UUID(task_id))
        return task.model_dump()

    async def update_task(self, task_id: str, solution: str) -> Dict[str, Any]:
        """MCP tool to update task with solution."""
        task = await self.task_manager.update_task(UUID(task_id), solution)
        return task.model_dump()

    async def search_similar_tasks(self, query: str) -> Dict[str, Any]:
        """MCP tool to search for similar tasks."""
        vector = await embed_text(query)
        similar = await self.task_manager.find_similar_issues(vector)
        return {"similar_tasks": similar}

    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check of the server and its dependencies.
        Checks:
        - Qdrant connection and collection status
        - Embedding provider availability
        - Memory usage and system metrics
        """
        health_status = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Check Qdrant connection and collection
            if self.task_manager and self.task_manager.client:
                try:
                    # Test Qdrant connection
                    collection_exists = await self.task_manager.client.collection_exists(
                        self.task_manager.collection
                    )
                    
                    if collection_exists:
                        collection_info = await self.task_manager.client.get_collection(
                            self.task_manager.collection
                        )
                        health_status["checks"]["qdrant"] = {
                            "status": "healthy",
                            "collection": {
                                "name": self.task_manager.collection,
                                "points_count": collection_info.points_count,
                                "vectors_config": str(collection_info.config.params.vectors),
                                "status": collection_info.status
                            }
                        }
                    else:
                        health_status["checks"]["qdrant"] = {
                            "status": "warning",
                            "message": "Collection not initialized",
                            "collection_name": self.task_manager.collection
                        }
                        health_status["status"] = "warning"
                except Exception as e:
                    health_status["checks"]["qdrant"] = {
                        "status": "error",
                        "message": f"Qdrant error: {str(e)}"
                    }
                    health_status["status"] = "error"
            else:
                health_status["checks"]["qdrant"] = {
                    "status": "error",
                    "message": "Task manager not initialized"
                }
                health_status["status"] = "error"

            # Check embedding provider
            try:
                # Test embedding with a sample text
                sample_vector = await self.task_manager.embedding_provider.embed_query("test")
                health_status["checks"]["embedding_provider"] = {
                    "status": "healthy",
                    "model": self.task_manager.embedding_provider.model_name,
                    "vector_size": len(sample_vector)
                }
            except Exception as e:
                health_status["checks"]["embedding_provider"] = {
                    "status": "error",
                    "message": f"Embedding provider error: {str(e)}"
                }
                health_status["status"] = "error"

            # Add system metrics
            import psutil
            health_status["checks"]["system"] = {
                "status": "healthy",
                "memory_usage_percent": psutil.Process().memory_percent(),
                "cpu_usage_percent": psutil.Process().cpu_percent(),
                "open_files": len(psutil.Process().open_files()),
                "threads": psutil.Process().num_threads()
            }

            return health_status

        except Exception as e:
            return {
                "status": "error",
                "message": f"Health check failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests."""
        try:
            tool_name = request.get("tool")
            if tool_name not in self.tools:
                return {
                    "error": f"Unknown tool: {tool_name}",
                    "available_tools": list(self.tools.keys())
                }

            params = request.get("parameters", {})
            result = await self.tools[tool_name](**params)
            return {"result": result}

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {"error": str(e)}

async def main():
    """Main MCP server loop."""
    server = MCPServer()
    await server.initialize()

    while True:
        try:
            # Read request from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, input)
            request = json.loads(line)
            
            # Process request
            response = await server.handle_request(request)
            
            # Send response to stdout
            print(json.dumps(response))
            
        except EOFError:
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    asyncio.run(main())
