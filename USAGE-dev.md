# MCP Server Qdrant Usage Guide

This document provides instructions for using the MCP Server with Qdrant for vector storage and retrieval.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Health Checks](#health-checks)
- [Working with ADRs](#working-with-adrs)
- [Qdrant Dashboard](#qdrant-dashboard)
- [Task Management](#task-management)
- [Code Analysis](#code-analysis)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher
- curl (for testing endpoints)

## Getting Started

### Starting the Services

To start the MCP server and Qdrant, use Docker Compose:

```bash
docker-compose up -d
```

This will start:
- Qdrant vector database on port 6333 (HTTP) and 6334 (gRPC)
- MCP server on port 8000

### Verifying the Services

You can verify that both services are running with:

```bash
docker-compose ps
```

## Health Checks

Both services expose health check endpoints:

### MCP Server Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-03-17 04:55:22.427585",
  "service": "mcp-server-qdrant",
  "server_initialized": true
}
```

### Qdrant Health

```bash
curl http://localhost:6333/healthz
```

Expected response: HTTP 200 OK

## Working with ADRs

The system can store and retrieve Architecture Decision Records (ADRs) using Qdrant's vector database.

### Storing ADRs

ADRs are stored in the `docs/adrs` directory and can be indexed into Qdrant using the provided test script:

```bash
python test_mcp_server.py
```

This script:
1. Creates a collection for ADR data
2. Extracts content from ADR markdown files
3. Stores the content with metadata in Qdrant
4. Performs a test search to verify retrieval

### Searching ADRs

You can search for ADRs directly using the Qdrant API:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.1, ..., 0.1],
    "limit": 3,
    "with_payload": true
  }' \
  http://localhost:6333/collections/test_adr_collection/points/search
```

In a production environment, you would use actual embeddings generated from your search query.

## Qdrant Dashboard

Qdrant provides a built-in web dashboard for visualizing and interacting with your vector data.

### Accessing the Dashboard

After starting the services, you can access the Qdrant dashboard at:

```
http://localhost:6333/dashboard
```

### Viewing Collections

1. Navigate to the "Collections" tab in the dashboard
2. You'll see a list of all collections, including:
   - `mcp_unified_store` - The main collection used by the MCP server
   - `test_adr_collection` - The collection created by the test script (if you've run it)

### Exploring Data

To explore the data in a collection:

1. Click on a collection name in the dashboard
2. Navigate to the "Points" tab to see the stored vectors
3. Use the "Search" tab to perform vector searches
4. Use the "Payload" tab to view the metadata associated with each point

### Visualizing Vectors

The dashboard provides visualization tools for your vector data:

1. Navigate to the "Visualization" tab in a collection
2. Select the vectors you want to visualize
3. Choose a dimensionality reduction method (t-SNE, PCA, etc.)
4. Explore the vector space visually

### Dashboard Features

- **Collections Management**: Create, configure, and delete collections
- **Points Management**: Add, update, and delete points
- **Search**: Perform vector searches with various parameters
- **Visualization**: Visualize vector spaces in 2D or 3D
- **Monitoring**: View system metrics and performance statistics

## Task Management

The MCP server includes task management functionality for handling test failures and development tasks.

### Task Creation

When a test fails, the system can automatically create a task:

```python
from mcp_server_qdrant.models.task import TestResult
from mcp_server_qdrant.services.task_manager import MCPTaskManager

# Create a test result
test_result = TestResult(
    name="test_authentication",
    error="Authentication failed: Invalid token format",
    context={"user_id": "test123"}
)

# Handle the test failure
task_manager = MCPTaskManager(qdrant_client)
result = await task_manager.handle_test_failure(test_result)

# Get the task ID
task_id = result["task_id"]
```

### Task Retrieval

You can retrieve a task by its ID:

```python
task = await task_manager.get_task(task_id)
print(task.title)
print(task.description)
print(task.status)
```

### Task Update

You can update a task with a solution:

```python
updated_task = await task_manager.update_task(
    task_id,
    solution="Fixed by updating the token validation logic"
)
```

## Code Analysis

The system includes functionality for analyzing your codebase and storing the results in Qdrant.

### Running Code Analysis

```python
from mcp_server_qdrant.analysis.analyzer import CodebaseAnalyzer
from mcp_server_qdrant.analysis.config import AnalysisConfig

# Configure the analyzer
config = AnalysisConfig(
    root_dir="./src",
    ignore_dirs=["__pycache__", ".git"],
    supported_extensions={".py": "python", ".md": "markdown"}
)

# Create the analyzer
analyzer = CodebaseAnalyzer("./src", config)

# Analyze the codebase
results = analyzer.analyze_structure()

# Store the results
summary = analyzer.analyze_and_store()
print(f"Analyzed {summary['files_analyzed']} files")
```

## Troubleshooting

### Common Issues

#### MCP Server Not Starting

If the MCP server fails to start, check:
1. Qdrant is running and healthy
2. The correct environment variables are set
3. The Docker logs for errors:
   ```bash
   docker-compose logs mcp-server
   ```

#### Qdrant Connection Issues

If the MCP server can't connect to Qdrant:
1. Verify Qdrant is running:
   ```bash
   curl http://localhost:6333/healthz
   ```
2. Check the network configuration in docker-compose.yml
3. Ensure the QDRANT_URL environment variable is set correctly

#### Health Check Failures

If health checks are failing:
1. For Qdrant, use the `/healthz` endpoint (not `/health`)
2. For the MCP server, use the `/health` endpoint
3. Check the logs for specific error messages

#### Dashboard Not Showing Data

If you don't see data in the Qdrant dashboard:
1. Make sure you've run the test script to add data: `python test_mcp_server.py`
2. Verify the collection exists: `curl http://localhost:6333/collections`
3. Check if the collection has points: `curl http://localhost:6333/collections/test_adr_collection`
4. Try refreshing the dashboard page

### Getting Help

If you encounter issues not covered here, please:
1. Check the logs for both services
2. Review the ADRs for architectural decisions that might impact your issue
3. Open an issue on GitHub with detailed information about the problem 