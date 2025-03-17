"""Module for analyzing and storing codebase information in Qdrant."""

import ast
import datetime
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np
from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams

from mcp_server_qdrant.core.config import Settings
from mcp_server_qdrant.analysis.config import AnalysisConfig

@dataclass
class CodeAnalysis:
    """Data class for code analysis results."""
    file_path: str
    content_type: str
    content: str
    metadata: Dict
    embeddings: Optional[List[float]] = None

class CodebaseAnalyzer:
    """Analyzes codebase and stores results in Qdrant."""

    def __init__(self, settings: Settings, config: Optional[AnalysisConfig] = None):
        """Initialize analyzer with configuration."""
        self.settings = settings
        self.config = config or AnalysisConfig()
        self.client = QdrantClient(url=settings.qdrant_url)
        self.embedding_model = TextEmbedding()
        
    def setup_collection(self, collection_name: str = "codebase") -> str:
        """Initialize or get Qdrant collection for storing code analysis."""
        try:
            self.client.get_collection(collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
        return collection_name

    def get_files(self, root_dir: str) -> List[str]:
        """Get all relevant files from the codebase."""
        files = []
        for root, dirs, filenames in os.walk(root_dir):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in self.config.ignore_dirs]
            
            for filename in filenames:
                ext = os.path.splitext(filename)[1]
                if ext in self.config.file_extensions:
                    files.append(os.path.join(root, filename))
        return sorted(files)

    def analyze_imports(self, node: ast.AST) -> Tuple[Set[str], Set[str]]:
        """Analyze imports in Python AST."""
        stdlib_imports = set()
        third_party_imports = set()
        
        for node in ast.walk(node):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = node.names[0].name.split('.')[0]
                if module in os.listdir(os.path.dirname(os.__file__)):
                    stdlib_imports.add(module)
                else:
                    third_party_imports.add(module)
        
        return stdlib_imports, third_party_imports

    def analyze_functions(self, node: ast.AST) -> List[Dict[str, Union[str, int]]]:
        """Analyze functions in Python AST."""
        functions = []
        
        for node in ast.walk(node):
            if isinstance(node, ast.FunctionDef):
                doc = ast.get_docstring(node) or ""
                functions.append({
                    'name': node.name,
                    'docstring': doc,
                    'lineno': node.lineno,
                    'complexity': len(list(ast.walk(node)))  # Simple complexity metric
                })
        
        return functions

    def analyze_file(self, file_path: str) -> CodeAnalysis:
        """Analyze a single file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ext = os.path.splitext(file_path)[1]
        language = self.config.file_extensions.get(ext, 'unknown')
        
        metadata = {
            'last_modified': datetime.datetime.fromtimestamp(
                os.path.getmtime(file_path)
            ).isoformat(),
            'size': os.path.getsize(file_path),
            'language': language,
            'dependencies': [],
            'complexity': 0
        }
        
        # Additional Python-specific analysis
        if language == 'python':
            try:
                tree = ast.parse(content)
                stdlib, third_party = self.analyze_imports(tree)
                metadata['dependencies'] = list(stdlib | third_party)
                
                functions = self.analyze_functions(tree)
                metadata['functions'] = functions
                metadata['complexity'] = sum(f['complexity'] for f in functions)
            except SyntaxError:
                pass  # Skip failed parsing
        
        return CodeAnalysis(
            file_path=file_path,
            content_type=language,
            content=content,
            metadata=metadata
        )

    def generate_embeddings(self, analysis: CodeAnalysis) -> CodeAnalysis:
        """Generate embeddings for the analyzed content."""
        # Split content into chunks based on config
        content_chunks = [
            analysis.content[i:i + self.config.chunk_size]
            for i in range(0, len(analysis.content), self.config.chunk_size)
        ]
        
        # Add metadata chunks
        text_chunks = content_chunks + [
            analysis.metadata.get('docstring', ''),  # Documentation
            ' '.join(analysis.metadata.get('dependencies', [])),  # Dependencies
        ]
        
        # Generate and average embeddings
        embeddings = self.embedding_model.embed(text_chunks)
        analysis.embeddings = np.mean(embeddings, axis=0).tolist()
        
        return analysis

    def store_analysis(self, collection_name: str, analysis: CodeAnalysis):
        """Store analysis results in Qdrant."""
        if not analysis.embeddings:
            analysis = self.generate_embeddings(analysis)
        
        self.client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=hash(analysis.file_path),
                    payload={
                        'file_path': analysis.file_path,
                        'content_type': analysis.content_type,
                        'content': analysis.content,
                        'metadata': analysis.metadata
                    },
                    vector=analysis.embeddings
                )
            ]
        )

    def analyze_codebase(self, root_dir: str = '.', collection_name: str = "codebase") -> Dict:
        """Analyze the entire codebase and store results in Qdrant."""
        collection_name = self.setup_collection(collection_name)
        
        files = self.get_files(root_dir)
        analysis_results = {
            'files_analyzed': len(files),
            'languages': set(),
            'total_size': 0,
            'complexity': 0,
            'config': {
                'ignore_dirs': list(self.config.ignore_dirs),
                'file_extensions': self.config.file_extensions,
                'chunk_size': self.config.chunk_size
            }
        }
        
        for file_path in files:
            analysis = self.analyze_file(file_path)
            self.store_analysis(collection_name, analysis)
            
            analysis_results['languages'].add(analysis.metadata['language'])
            analysis_results['total_size'] += analysis.metadata['size']
            analysis_results['complexity'] += analysis.metadata.get('complexity', 0)
        
        analysis_results['languages'] = list(analysis_results['languages'])
        return analysis_results 