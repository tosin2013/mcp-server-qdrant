"""Codebase analyzer implementation."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from mcp_server_qdrant.analysis.config import AnalysisConfig


class CodebaseAnalyzer:
    """Analyzes Python modules and generates documentation."""

    def __init__(self, root_dir: str, config: Optional[AnalysisConfig] = None):
        """Initialize the codebase analyzer.
        
        Args:
            root_dir: Root directory of the codebase
            config: Optional analysis configuration
        """
        self.root_dir = Path(root_dir)
        self.config = config or AnalysisConfig(root_dir=str(self.root_dir))
        self.client = QdrantClient(":memory:")
        self._setup_collection()
    
    def _setup_collection(self) -> None:
        """Set up the Qdrant collection for storing analysis results."""
        self.client.recreate_collection(
            collection_name=self.config.collection_name,
            vectors_config=VectorParams(
                size=self.config.vector_size,
                distance=Distance.COSINE
            )
        )
    
    def get_files(self) -> List[str]:
        """Get all relevant files from the codebase."""
        files = []
        for root, dirs, filenames in os.walk(self.root_dir):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in self.config.ignore_dirs]
            
            for filename in filenames:
                ext = os.path.splitext(filename)[1]
                if ext in self.config.supported_extensions:
                    files.append(os.path.join(root, filename))
        return sorted(files)
    
    def analyze_python_module(self, module_path: str) -> Dict:
        """Analyze a Python module and extract its structure."""
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "path": module_path,
            "type": "module",
            "language": "python",
            "content": content,
            "functions": [],
            "classes": [],
            "doc": ""
        }
    
    def analyze_javascript_file(self, file_path: str) -> Dict:
        """Analyze a JavaScript file and extract its structure."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "path": file_path,
            "type": "module",
            "language": "javascript",
            "content": content,
            "functions": [],
            "classes": [],
            "doc": ""
        }
    
    def analyze_markdown_file(self, file_path: str) -> Dict:
        """Analyze a Markdown file and extract its content."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "path": file_path,
            "type": "documentation",
            "language": "markdown",
            "content": content,
            "doc": content
        }
    
    def analyze_file(self, file_path: str) -> Dict:
        """Analyze a file based on its extension."""
        ext = os.path.splitext(file_path)[1]
        language = self.config.supported_extensions.get(ext)
        
        if language == 'python':
            return self.analyze_python_module(file_path)
        elif language in ('javascript', 'typescript'):
            return self.analyze_javascript_file(file_path)
        elif language == 'markdown':
            return self.analyze_markdown_file(file_path)
        else:
            # Generic file analysis
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "path": file_path,
                "type": "file",
                "language": language,
                "content": content,
                "doc": ""
            }
    
    def analyze_structure(self) -> List[Dict]:
        """Analyze the entire codebase structure."""
        files = self.get_files()
        results = []
        
        for file_path in files:
            try:
                analysis = self.analyze_file(file_path)
                results.append(analysis)
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
        
        return results
    
    def analyze_and_store(self) -> Dict:
        """Analyze the codebase and store results in Qdrant."""
        results = self.analyze_structure()
        
        # TODO: Generate embeddings and store in Qdrant
        
        return {
            "files_analyzed": len(results),
            "languages": set(r.get("language") for r in results if r.get("language")),
            "total_size": sum(len(r.get("content", "")) for r in results)
        } 