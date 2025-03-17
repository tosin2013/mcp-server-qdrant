from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from ..qdrant import QdrantConnector
from ..embeddings import embed_text
from ..models.task import Task, TestResult, TaskSuggestions
from ..utils.logger import get_logger

logger = get_logger(__name__)

class MCPTaskManager:
    """Service for managing development tasks and test failures."""
    
    def __init__(self, qdrant_client: QdrantConnector):
        self.client = qdrant_client
        self.collection = "mcp_unified_store"

    async def handle_test_failure(self, test_result: TestResult) -> Dict[str, Any]:
        """Process test failure during development."""
        logger.info(f"Handling test failure for {test_result.name}")
        
        # Create vector from test failure
        vector = await embed_text(
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
        task_id = None
        if suggestions.should_create_task:
            task = await self.create_task(
                test_result,
                suggestions
            )
            task_id = task.id
        
        return {
            "similar_issues": similar,
            "suggestions": suggestions.fixes,
            "task_id": task_id,
            "docs": suggestions.relevant_docs
        }

    async def find_similar_issues(self, vector: List[float]) -> List[Dict[str, Any]]:
        """Find similar issues in development history."""
        results = await self.client.search(
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
        
        return [
            {
                "title": r.payload.get("title", "Unknown Issue"),
                "solution": r.payload.get("solution", "No solution recorded"),
                "score": r.score
            }
            for r in results
        ]

    async def generate_suggestions(
        self, 
        test_result: TestResult, 
        similar_issues: List[Dict[str, Any]]
    ) -> TaskSuggestions:
        """Generate suggestions based on test failure and similar issues."""
        # Analyze similar issues to generate suggestions
        fixes = []
        for issue in similar_issues:
            if issue["solution"]:
                fixes.append(f"Try: {issue['solution']}")
        
        # If no similar solutions found, provide generic suggestions
        if not fixes:
            fixes = [
                f"Review the test failure in {test_result.name}",
                "Check the test environment and dependencies",
                "Verify input data and test conditions"
            ]
        
        return TaskSuggestions(
            description=f"Fix test failure in {test_result.name}",
            fixes=fixes,
            priority=self._calculate_priority(test_result, similar_issues),
            should_create_task=len(fixes) > 0,
            relevant_docs=self._find_relevant_docs(test_result, similar_issues)
        )

    async def create_task(
        self, 
        test_result: TestResult, 
        suggestions: TaskSuggestions
    ) -> Task:
        """Create a development task."""
        task = Task(
            title=f"Fix: {test_result.name}",
            description=suggestions.description,
            priority=suggestions.priority,
            related_tests=[test_result.id],
            related_docs=suggestions.relevant_docs
        )
        
        # Create vector for the task
        vector = await embed_text(
            f"{task.title} {task.description}"
        )
        
        # Store in Qdrant
        point = task.to_qdrant_point()
        point["vector"] = vector
        
        await self.client.upsert(
            collection_name=self.collection,
            points=[point]
        )
        
        return task

    async def get_task(self, task_id: UUID) -> Task:
        """Retrieve a task by ID."""
        result = await self.client.retrieve(
            collection_name=self.collection,
            ids=[str(task_id)]
        )
        
        if not result:
            raise ValueError(f"Task {task_id} not found")
            
        return Task.model_validate_json(result[0].payload["content"])

    async def update_task(self, task_id: UUID, solution: str) -> Task:
        """Update a task with a solution."""
        task = await self.get_task(task_id)
        task.solution = solution
        task.status = "completed"
        
        # Create updated vector
        vector = await embed_text(
            f"{task.title} {task.description} {solution}"
        )
        
        # Update in Qdrant
        point = task.to_qdrant_point()
        point["vector"] = vector
        
        await self.client.upsert(
            collection_name=self.collection,
            points=[point]
        )
        
        return task

    def _calculate_priority(
        self, 
        test_result: TestResult, 
        similar_issues: List[Dict[str, Any]]
    ) -> int:
        """Calculate task priority based on test result and similar issues."""
        # Start with default priority
        priority = 1
        
        # Increase priority if similar issues exist
        if similar_issues:
            priority += 1
        
        # Increase priority for certain keywords in error
        critical_keywords = ["security", "crash", "data loss", "critical"]
        if test_result.error and any(k in test_result.error.lower() for k in critical_keywords):
            priority += 2
            
        return min(priority, 5)  # Cap at priority 5

    def _find_relevant_docs(
        self, 
        test_result: TestResult, 
        similar_issues: List[Dict[str, Any]]
    ) -> List[str]:
        """Find relevant documentation for the task."""
        docs = set()
        
        # Add docs from similar issues
        for issue in similar_issues:
            if "docs" in issue:
                docs.update(issue["docs"])
        
        # Add default docs based on test name
        if "auth" in test_result.name.lower():
            docs.add("auth.md")
        elif "api" in test_result.name.lower():
            docs.add("api.md")
            
        return list(docs) 