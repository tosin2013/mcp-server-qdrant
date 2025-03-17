"""Configuration module for MCP Server Qdrant."""

from mcp_server_qdrant.settings import Settings

__all__ = ["Settings"]

from dataclasses import dataclass, field
from typing import Dict, Optional, Set

@dataclass
class Settings:
    """Core settings for MCP Server Qdrant."""
    
    # Qdrant settings
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    collection_name: str = "default"
    vector_size: int = 384
    
    # Analysis settings
    root_dir: str = "."
    ignore_dirs: Set[str] = field(default_factory=lambda: {
        'node_modules', '.venv', 'venv', 'vendor',
        '__pycache__', '.git', '.pytest_cache'
    })
    supported_extensions: Dict[str, str] = field(default_factory=lambda: {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.md': 'markdown',
        '.json': 'json',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.sh': 'shell'
    })
    
    # Embedding settings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 100
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'Settings':
        """Create Settings instance from dictionary."""
        return cls(
            qdrant_url=config_dict.get("qdrant", {}).get("url", cls.qdrant_url),
            qdrant_api_key=config_dict.get("qdrant", {}).get("api_key"),
            collection_name=config_dict.get("qdrant", {}).get("collection_name", cls.collection_name),
            vector_size=config_dict.get("qdrant", {}).get("vector_size", cls.vector_size),
            root_dir=config_dict.get("root_dir", cls.root_dir),
            ignore_dirs=set(config_dict.get("ignore_directories", cls.ignore_dirs)),
            supported_extensions=config_dict.get("file_patterns", {}).get("extensions", cls.supported_extensions),
            embedding_model=config_dict.get("embedding", {}).get("model", cls.embedding_model),
            batch_size=config_dict.get("batch_size", cls.batch_size)
        ) 