from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

class TestResult(BaseModel):
    """Model representing a test result."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    error: Optional[str] = None
    context: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    platform: Optional[str] = None
    container_id: Optional[str] = None

class TaskSuggestions(BaseModel):
    """Model representing suggestions for a task."""
    description: str
    fixes: List[str]
    priority: int = 1
    should_create_task: bool = True
    task_id: Optional[UUID] = None
    relevant_docs: List[str] = Field(default_factory=list)

class Task(BaseModel):
    """Model representing a development task."""
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    priority: int = 1
    status: str = "open"
    related_tests: List[UUID] = Field(default_factory=list)
    related_docs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    solution: Optional[str] = None

    def to_qdrant_point(self):
        """Convert task to Qdrant point format."""
        return {
            "id": str(self.id),
            "vector": None,  # Will be filled by the embeddings service
            "payload": {
                "content_type": "task",
                "content": self.model_dump_json(),
                "metadata": {
                    "created_at": self.created_at.isoformat(),
                    "updated_at": self.updated_at.isoformat(),
                    "status": self.status
                }
            }
        } 