# MCP Server Qdrant Usage Guide

This document provides instructions for using the MCP Server with Qdrant for vector storage and retrieval, with a focus on integration with AI coding assistants like Cursor.ai, Claude, Windsurf AI, and Roo-Code @Web.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Health Checks](#health-checks)
- [Working with ADRs](#working-with-adrs)
- [Qdrant Dashboard](#qdrant-dashboard)
- [Integration with AI Coding Assistants](#integration-with-ai-coding-assistants)
  - [Cursor.ai Integration](#cursorai-integration)
  - [Claude Integration](#claude-integration)
  - [Windsurf AI Integration](#windsurf-ai-integration)
  - [Roo-Code @Web Integration](#roo-code-web-integration)
- [Task Management](#task-management)
- [Code Analysis](#code-analysis)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher
- curl (for testing endpoints)
- Access to one or more AI coding assistants:
  - Cursor.ai
  - Claude (via API)
  - Windsurf AI
  - Roo-Code @Web

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

## Integration with AI Coding Assistants

The MCP server with Qdrant can be integrated with various AI coding assistants to enhance code understanding, documentation retrieval, and development workflows.

### Cursor.ai Integration

[Cursor.ai](https://cursor.ai/) is an AI-powered code editor that can leverage the MCP server's vector database for improved code understanding.

#### Setup with Cursor.ai

1. Start the MCP server and Qdrant using Docker Compose
2. Open your project in Cursor.ai
3. Configure Cursor.ai to use the MCP server as a knowledge base:

```javascript
// In Cursor.ai settings.json
{
  "ai.knowledgeBases": [
    {
      "name": "MCP Server Knowledge",
      "url": "http://localhost:8000/api/query",
      "headers": {
        "Content-Type": "application/json"
      }
    }
  ]
}
```

#### Using with Cursor.ai

1. Use the `/search` command in Cursor.ai to search your codebase
2. Cursor.ai will query the MCP server, which uses Qdrant to retrieve relevant code snippets and ADRs
3. Reference ADRs directly in your prompts:

```
/search What does our ADR say about containerization strategy?
```

4. Get code suggestions based on your project's architectural decisions:

```
/generate Implement a function that follows our ADR-002 for Docker deployment
```

### Claude Integration

[Claude](https://www.anthropic.com/claude) is an AI assistant that can be integrated with the MCP server to provide context-aware coding assistance.

#### Setup with Claude API

1. Start the MCP server and Qdrant using Docker Compose
2. Set up a Python script to query the MCP server and provide context to Claude:

```python
import requests
import anthropic

# Query MCP server for relevant context
def get_context(query):
    response = requests.post(
        "http://localhost:8000/api/query",
        json={"query": query, "limit": 5}
    )
    return response.json()

# Use Claude API with context
def ask_claude_with_context(query):
    context = get_context(query)
    context_text = "\n\n".join([item["content"] for item in context["results"]])
    
    client = anthropic.Anthropic(api_key="your_api_key")
    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1000,
        system=f"You are a coding assistant with access to the following context from the project's documentation and ADRs:\n\n{context_text}",
        messages=[{"role": "user", "content": query}]
    )
    return message.content
```

#### Using with Claude

1. Use the function to ask Claude questions about your codebase:

```python
response = ask_claude_with_context("How should we implement containerization according to our ADRs?")
print(response)
```

2. Claude will provide responses informed by your project's ADRs and documentation stored in Qdrant.

### Windsurf AI Integration

[Windsurf AI](https://windsurf.ai/) is a code understanding platform that can be enhanced with the MCP server's vector database.

#### Setup with Windsurf AI

1. Start the MCP server and Qdrant using Docker Compose
2. Configure Windsurf AI to use the MCP server as an additional knowledge source:

```yaml
# In Windsurf AI configuration
knowledge_sources:
  - name: mcp_server
    type: rest_api
    url: http://localhost:8000/api/query
    method: POST
    headers:
      Content-Type: application/json
    query_param: query
    response_path: results
```

#### Using with Windsurf AI

1. Use Windsurf AI's interface to query your codebase
2. Windsurf AI will combine its own analysis with context from the MCP server
3. Ask questions about architectural decisions:

```
What is our approach to containerization according to our ADRs?
```

4. Get implementation suggestions that align with your project's architecture:

```
How should I implement a new microservice following our established patterns?
```

### Roo-Code @Web Integration

[Roo-Code @Web](https://roo.ai/) is a web-based coding assistant that can be integrated with the MCP server.

#### Setup with Roo-Code @Web

1. Start the MCP server and Qdrant using Docker Compose
2. Create a custom plugin for Roo-Code @Web that queries the MCP server:

```javascript
// Roo-Code @Web plugin
const mcpServerPlugin = {
  name: "MCP Server Knowledge",
  description: "Access project knowledge from MCP Server",
  version: "1.0.0",
  
  async query(question) {
    const response = await fetch("http://localhost:8000/api/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        query: question,
        limit: 5
      })
    });
    
    return await response.json();
  }
};

// Register the plugin
RooCode.registerPlugin(mcpServerPlugin);
```

#### Using with Roo-Code @Web

1. Access the Roo-Code @Web interface
2. Enable the MCP Server Knowledge plugin
3. Ask questions about your project's architecture:

```
What does our ADR say about vector storage?
```

4. Get code suggestions that align with your architectural decisions:

```
Generate a function to connect to Qdrant following our established patterns
```

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

### Using Analysis Results with AI Assistants

The code analysis results stored in Qdrant can be leveraged by AI coding assistants:

```python
# Example: Query code analysis results for AI context
def get_code_context(file_path, function_name=None):
    query = {
        "filter": {
            "must": [
                {"key": "file_path", "match": {"value": file_path}}
            ]
        },
        "limit": 10
    }
    
    if function_name:
        query["filter"]["must"].append(
            {"key": "function_name", "match": {"value": function_name}}
        )
    
    response = requests.post(
        "http://localhost:6333/collections/code_analysis/points/scroll",
        json=query
    )
    
    return response.json()
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

#### AI Integration Issues

If you're having trouble integrating with AI coding assistants:

1. Ensure the MCP server API endpoints are accessible from the AI tool
2. Check CORS settings if accessing from a web-based tool
3. Verify that the response format matches what the AI tool expects
4. For API-based integrations, check authentication settings

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