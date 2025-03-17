"""Configuration for codebase analysis."""

from dataclasses import dataclass, field
from typing import Dict, Set


@dataclass
class AnalysisConfig:
    """Configuration for codebase analysis."""
    
    root_dir: str = "."
    collection_name: str = "codebase"
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
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_size: int = 384
    batch_size: int = 100

    @classmethod
    def from_file(cls, path: str) -> "AnalysisConfig":
        """Load configuration from a file."""
        import json
        import yaml
        from pathlib import Path
        
        path = Path(path)
        if not path.exists():
            return cls()
            
        with open(path) as f:
            if path.suffix in {'.yml', '.yaml'}:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
                
        return cls(**data) 