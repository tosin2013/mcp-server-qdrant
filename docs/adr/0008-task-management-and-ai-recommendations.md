# ADR-008: MCP Server Qdrant Task Management

## Status
Proposed

## Context
When developing with MCP Server Qdrant, developers need:
- Immediate feedback on test failures
- AI-powered suggestions for fixes
- Context from similar past issues
- Integration with their existing workflow
- Platform-specific guidance

Our existing ADRs provide the foundation:
- ADR-001: Project structure for adding task management
- ADR-007: Qdrant integration for storing task data
- ADR-006: Documentation linkage
- ADR-005: Platform-specific considerations

## Decision
We will extend MCP Server Qdrant to provide AI-assisted task management during development by:

1. Integrating with the developer's test workflow
2. Using Qdrant's vector search for similar issues
3. Providing immediate AI suggestions
4. Maintaining task context in the vector store
5. Linking to relevant documentation and tests

### Key Features
1. **Development Workflow Integration**
   - Automatic task creation from test runs
   - Immediate feedback in IDE/CLI
   - Context-aware suggestions
   - History of similar issues

2. **MCP Server Integration**
   - Uses existing Qdrant connection
   - Shares vector storage
   - Leverages existing embeddings
   - Maintains development context

3. **Developer Assistance**
   - Real-time fix suggestions
   - Similar issue lookup
   - Code snippet examples
   - Platform-specific guidance

4. **Task Context**
   - Test case linkage
   - Related documentation
   - Previous solutions
   - Environment details

## Implementation

### MCP Server Extension
```python
from mcp_server_qdrant.core import QdrantClient
from mcp_server_qdrant.embeddings import embed_text
from mcp_server_qdrant.models import TestResult, Task

class MCPTaskManager:
    def __init__(self, qdrant_client: QdrantClient):
        self.client = qdrant_client
        self.collection = "mcp_unified_store"

    async def handle_test_failure(self, test_result: TestResult):
        """Process test failure during development."""
        # Create vector from test failure
        vector = embed_text(
            f"{test_result.name} {test_result.error}"
        )
        
        # Find similar issues
        similar = await self.find_similar_issues(vector)
        
        # Generate suggestions
        suggestions = await self.generate_suggestions(
            test_result, 
            similar
        )
        
        # Create task if needed
        if suggestions.should_create_task:
            await self.create_task(
                test_result,
                suggestions
            )
        
        # Return immediate feedback
        return {
            "similar_issues": similar,
            "suggestions": suggestions.fixes,
            "task_id": suggestions.task_id,
            "docs": suggestions.relevant_docs
        }

    async def find_similar_issues(self, vector):
        """Find similar issues in development history."""
        return await self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter={
                "should": [
                    {"key": "content_type", "match": {"value": "test_result"}},
                    {"key": "content_type", "match": {"value": "task"}}
                ]
            },
            limit=5
        )

    async def create_task(self, test_result: TestResult, suggestions):
        """Create a development task."""
        task = Task(
            title=f"Fix: {test_result.name}",
            description=suggestions.description,
            priority=suggestions.priority,
            related_tests=[test_result.id],
            related_docs=suggestions.docs
        )
        
        await self.client.upsert(
            collection_name=self.collection,
            points=[task.to_qdrant_point()]
        )
```

### Developer Usage
```python
# In your test code
from mcp_server_qdrant import MCPTaskManager

async def test_authentication():
    try:
        # Your test code
        result = await auth_service.authenticate(user)
        assert result.is_authenticated
    except AssertionError as e:
        # MCP Server handles the failure
        task_manager = MCPTaskManager()
        feedback = await task_manager.handle_test_failure(
            TestResult(
                name="test_authentication",
                error=str(e),
                context=get_test_context()
            )
        )
        
        # Immediate developer feedback
        print("Similar issues found:")
        for issue in feedback["similar_issues"]:
            print(f"- {issue.title}: {issue.solution}")
        
        print("\nSuggested fixes:")
        for fix in feedback["suggestions"]:
            print(f"- {fix}")
        
        raise
```

### CLI Integration
```bash
# Run tests with MCP task management
$ mcp test

# During test failure:
> Test failed: test_authentication
> Found 3 similar issues:
  - Authentication timeout in Docker: Fixed by increasing timeout
  - Token validation error: Fixed by updating key rotation
  - Session handling bug: Fixed by clearing cache
> 
> Suggested fixes:
  1. Check authentication timeout settings
  2. Verify token validation process
  3. Review session management
>
> Task T123 created for tracking
> Related docs: auth.md, deployment.md

# View task details
$ mcp task show T123

# Update task with solution
$ mcp task solve T123 --solution "Updated timeout settings"
```

## Consequences

### Positive
- Immediate developer feedback
- Context from past issues
- AI-powered fix suggestions
- Integrated with normal workflow
- Minimal additional setup

### Negative
- Learning curve for AI suggestions
- Potential suggestion overload
- Need for quality initial data
- Storage growth over time

### Mitigations
1. **Developer Experience**
   - Progressive suggestion rollout
   - Configurable feedback levels
   - Clear suggestion prioritization
   - Easy suggestion dismissal

2. **Data Management**
   - Regular cleanup of old tasks
   - Suggestion quality tracking
   - Feedback incorporation
   - Storage optimization

## References
- [MCP Server Qdrant Docs](https://docs.mcp-server.io)
- [Python Testing Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
- [Developer Workflow Integration](https://martinfowler.com/articles/developer-effectiveness.html) 