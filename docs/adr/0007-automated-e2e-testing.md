# ADR-007: Development Test Tracking System with MCP Server Qdrant

## Status
Accepted

## Context
Building on our existing ADRs:
- ADR-001 established our project structure and testing strategy
- ADR-002 defined our containerization approach
- ADR-003 set up our container publishing workflow
- ADR-005 established platform support requirements
- ADR-006 created our documentation analysis system

We need to integrate test tracking and analysis into this ecosystem using our MCP Server Qdrant infrastructure.

## Decision
We will extend the MCP Server Qdrant to handle test tracking and analysis by:

1. Using the existing MCP Server infrastructure
2. Integrating with our documentation system
3. Supporting all platforms defined in ADR-005
4. Following container patterns from ADR-002
5. Publishing test data using ADR-003 workflow

### Key Features
1. **Integrated Test Tracking**
   - Uses MCP Server Qdrant collections
   - Shares infrastructure with documentation storage
   - Supports cross-platform testing
   - Container-aware test execution

2. **Unified Vector Storage**
   - Combined documentation and test vectors
   - Shared embedding infrastructure
   - Cross-referenced search capabilities
   - Platform-aware vector storage

3. **Container Integration**
   - Test results included in container metadata
   - Platform-specific test tracking
   - Containerized test execution
   - Automated result publishing

4. **Documentation Sync**
   - Real-time documentation updates from tests
   - Automated pattern documentation
   - Cross-referenced test cases
   - Platform-specific guides

## Implementation

### MCP Server Collections
```yaml
collections:
  mcp_unified_store:
    vectors:
      size: 384  # Using all-MiniLM-L6-v2 embeddings
      distance: Cosine
    payload_schema:
      content_type: str  # 'test_result', 'documentation', 'pattern'
      content: str
      metadata:
        source: str
        platform: str
        container_id: str
        timestamp: datetime
```

### Integration Flow
```python
async def process_test_result(result: dict):
    """Process test result and update documentation."""
    # Create vector embedding
    vector = embed_text(
        f"{result['test_name']} {result['error_message']}"
    )
    
    # Store in MCP Server Qdrant
    await qdrant_client.upsert(
        collection_name="mcp_unified_store",
        points=[{
            "id": generate_uuid(),
            "vector": vector,
            "payload": {
                "content_type": "test_result",
                "content": json.dumps(result),
                "metadata": {
                    "source": "test_execution",
                    "platform": result["platform"],
                    "container_id": result.get("container_id"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        }]
    )
    
    # Update documentation if needed
    await update_documentation(result)

async def update_documentation(result: dict):
    """Update documentation based on test results."""
    # Find related documentation
    similar_docs = await qdrant_client.search(
        collection_name="mcp_unified_store",
        query_vector=embed_text(result["test_name"]),
        query_filter={
            "must": [
                {"key": "content_type", "match": {"value": "documentation"}}
            ]
        },
        limit=5
    )
    
    # Update if needed
    if needs_update(result, similar_docs):
        await generate_documentation_update(result)
```

### Developer Experience
```bash
# Run tests with documentation sync
$ mcp test --sync-docs

# Search across tests and docs
$ mcp search "authentication flow"

# View platform-specific patterns
$ mcp patterns --platform windows

# Analyze container test results
$ mcp analyze --container <container_id>
```

## Consequences

### Positive
- Unified storage for tests and documentation
- Cross-platform test tracking
- Integrated container support
- Automated documentation updates
- Shared infrastructure usage

### Negative
- More complex data model
- Increased storage requirements
- Cross-platform synchronization overhead

### Mitigations
1. **Data Management**
   - Regular cleanup of old test results
   - Efficient vector storage
   - Platform-specific caching

2. **Performance**
   - Batch updates for documentation
   - Async test processing
   - Selective vector creation

## References
- [MCP Server Documentation](https://docs.mcp-server.io)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Container Integration Guide](https://docs.docker.com/engine/api/)
- [Cross-Platform Testing](https://docs.pytest.org/en/latest/example/simple.html) 