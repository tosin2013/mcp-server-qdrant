"""Script for analyzing codebase and generating documentation."""

import ast
import datetime
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import jinja2

import numpy as np
from fastembed import TextEmbedding
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams

class Config:
    """Configuration for codebase analysis."""
    def __init__(self, config_path=None, **kwargs):
        """Initialize configuration.
        
        Args:
            config_path: Path to configuration file (YAML or JSON)
            **kwargs: Additional configuration parameters
        """
        self.config = {}
        self.root_dir = kwargs.get("root_dir", ".")
        self.qdrant_url = kwargs.get("qdrant_url", "http://localhost:6333")
        self.collection_name = kwargs.get("collection_name", "codebase")
        self.ignore_dirs = kwargs.get("ignore_dirs", {
            'node_modules', '.venv', 'venv', 'vendor',
            '__pycache__', '.git', '.pytest_cache'
        })
        self.supported_extensions = kwargs.get("supported_extensions", {
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
        self.embedding_model_name = kwargs.get("embedding_model_name", "sentence-transformers/all-MiniLM-L6-v2")
        self.vector_size = kwargs.get("vector_size", 384)
        self.batch_size = kwargs.get("batch_size", 100)
        
        if config_path:
            self._load_config(config_path)
            self.resolve_env_vars()
        
    def _load_config(self, config_path):
        """Load configuration from file."""
        import yaml
        import json
        from pathlib import Path
        
        path = Path(config_path)
        if not path.exists():
            return
            
        with open(path) as f:
            if path.suffix in {'.yml', '.yaml'}:
                self.config = yaml.safe_load(f)
            else:
                self.config = json.load(f)
                
        # Update attributes from config
        if self.config:
            if "root_dir" in self.config:
                self.root_dir = self.config["root_dir"]
                
            if "qdrant" in self.config:
                qdrant_config = self.config["qdrant"]
                if "url" in qdrant_config:
                    self.qdrant_url = qdrant_config["url"]
                if "collection_name" in qdrant_config:
                    self.collection_name = qdrant_config["collection_name"]
                if "embedding_model" in qdrant_config:
                    self.embedding_model_name = qdrant_config["embedding_model"]
                if "batch_size" in qdrant_config:
                    self.batch_size = qdrant_config["batch_size"]
                    
            if "ignore_directories" in self.config:
                self.ignore_dirs = set(self.config["ignore_directories"])
                
            if "file_patterns" in self.config and "extensions" in self.config["file_patterns"]:
                self.supported_extensions = self.config["file_patterns"]["extensions"]
        
    def resolve_env_vars(self):
        """Resolve environment variables in the configuration."""
        import os
        import re
        
        def _resolve_env_var(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                return os.environ.get(env_var, value)
            return value
        
        def _process_dict(d):
            for key, value in d.items():
                if isinstance(value, dict):
                    _process_dict(value)
                elif isinstance(value, str):
                    d[key] = _resolve_env_var(value)
        
        _process_dict(self.config)
        
        # Also resolve environment variables in direct attributes
        if isinstance(self.qdrant_url, str) and self.qdrant_url.startswith("${") and self.qdrant_url.endswith("}"):
            env_var = self.qdrant_url[2:-1]
            self.qdrant_url = os.environ.get(env_var, self.qdrant_url)
            
        if isinstance(self.collection_name, str) and self.collection_name.startswith("${") and self.collection_name.endswith("}"):
            env_var = self.collection_name[2:-1]
            self.collection_name = os.environ.get(env_var, self.collection_name)
            
        return self
        
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'Config':
        """Create Config instance from dictionary."""
        config = cls()
        config.config = config_dict
        
        # Update attributes from config
        if "root_dir" in config_dict:
            config.root_dir = config_dict["root_dir"]
            
        if "qdrant" in config_dict:
            qdrant_config = config_dict["qdrant"]
            if "url" in qdrant_config:
                config.qdrant_url = qdrant_config["url"]
            if "collection_name" in qdrant_config:
                config.collection_name = qdrant_config["collection_name"]
            if "embedding_model" in qdrant_config:
                config.embedding_model_name = qdrant_config["embedding_model"]
            if "batch_size" in qdrant_config:
                config.batch_size = qdrant_config["batch_size"]
                
        if "ignore_directories" in config_dict:
            config.ignore_dirs = set(config_dict["ignore_directories"])
            
        if "file_patterns" in config_dict and "extensions" in config_dict["file_patterns"]:
            config.supported_extensions = config_dict["file_patterns"]["extensions"]
            
        return config

# Initialize embedding model
embedding_model = None

@dataclass
class CodeAnalysis:
    """Data class for code analysis results."""
    file_path: str
    content_type: str
    content: str
    metadata: Dict
    embeddings: Optional[List[float]] = None

def setup_qdrant_collection(client: QdrantClient, collection_name: str, vector_size: int = 384) -> str:
    """Initialize or get Qdrant collection for storing code analysis."""
    try:
        client.get_collection(collection_name)
    except Exception:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    return collection_name

def get_files(config: Config) -> List[str]:
    """Get all relevant files from the codebase."""
    files = []
    for root, dirs, filenames in os.walk(config.root_dir):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in config.ignore_dirs]
        
        for filename in filenames:
            ext = os.path.splitext(filename)[1]
            if ext in config.supported_extensions:
                files.append(os.path.join(root, filename))
    return sorted(files)

def analyze_imports(node: ast.AST) -> Tuple[Set[str], Set[str]]:
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

def analyze_functions(node: ast.AST) -> List[Dict[str, Union[str, int]]]:
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

def analyze_file(file_path: str, config: Config) -> CodeAnalysis:
    """Analyze a single file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    ext = os.path.splitext(file_path)[1]
    language = config.supported_extensions.get(ext, 'unknown')
    
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
            stdlib, third_party = analyze_imports(tree)
            metadata['dependencies'] = list(stdlib | third_party)
            
            functions = analyze_functions(tree)
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

def generate_embeddings(analysis: CodeAnalysis, config: Config) -> CodeAnalysis:
    """Generate embeddings for the analyzed content."""
    global embedding_model
    if embedding_model is None:
        embedding_model = TextEmbedding(config.embedding_model_name)
    
    # Generate embeddings for different components
    text_chunks = [
        analysis.content,  # Full content
        analysis.metadata.get('docstring', ''),  # Documentation
        ' '.join(analysis.metadata.get('dependencies', [])),  # Dependencies
    ]
    
    # Generate and average embeddings
    embeddings = embedding_model.embed(text_chunks)
    analysis.embeddings = np.mean(embeddings, axis=0).tolist()
    
    return analysis

def store_analysis(client: QdrantClient, config: Config, analysis: CodeAnalysis):
    """Store analysis results in Qdrant."""
    if not analysis.embeddings:
        analysis = generate_embeddings(analysis, config)
    
    client.upsert(
        collection_name=config.collection_name,
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

def analyze_codebase(config: Optional[Union[Dict, Config]] = None) -> Dict:
    """Analyze the entire codebase and store results in Qdrant."""
    if config is None:
        config = Config()
    elif isinstance(config, dict):
        config = Config.from_dict(config)
    
    client = QdrantClient(config.qdrant_url)
    collection_name = setup_qdrant_collection(client, config.collection_name)
    
    files = get_files(config)
    analysis_results = {
        'files_analyzed': len(files),
        'languages': set(),
        'total_size': 0,
        'complexity': 0
    }
    
    for file_path in files:
        analysis = analyze_file(file_path, config)
        store_analysis(client, config, analysis)
        
        analysis_results['languages'].add(analysis.metadata['language'])
        analysis_results['total_size'] += analysis.metadata['size']
        analysis_results['complexity'] += analysis.metadata.get('complexity', 0)
    
    analysis_results['languages'] = list(analysis_results['languages'])
    return analysis_results

class QdrantIndexer:
    """Indexes documentation in Qdrant."""

    def __init__(self, config):
        """Initialize the Qdrant indexer.
        
        Args:
            config: Configuration object or dictionary
        """
        if isinstance(config, dict):
            self.config = Config.from_dict(config)
        else:
            self.config = config
            
        self.collection_name = self.config.collection_name
        self.client = QdrantClient(self.config.qdrant_url)
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the collection exists with proper configuration."""
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

    def index_documents(self, documents: List[Dict]) -> bool:
        """Index documents in Qdrant."""
        for i in range(0, len(documents), self.config.batch_size):
            batch = documents[i:i + self.config.batch_size]
            points = []
            
            for doc in batch:
                # Generate embeddings for the document
                embedding = TextEmbedding(self.config.embedding_model_name)
                vector = list(embedding.embed([doc['content']])[0])
                
                points.append(
                    models.PointStruct(
                        id=hash(f"{doc['path']}:{doc.get('type', 'unknown')}"),
                        payload=doc,
                        vector=vector
                    )
                )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        return True

class CodebaseAnalyzer:
    """Analyzes Python modules and generates documentation."""

    def __init__(self, root_dir: str, config: Optional[Union[Dict, Config]] = None):
        """Initialize the codebase analyzer.
        
        Args:
            root_dir: Root directory of the codebase
            config: Optional analysis configuration
        """
        self.root_dir = root_dir
        
        if isinstance(config, dict):
            self.config = Config.from_dict(config)
        elif config is None:
            self.config = Config()
            self.config.root_dir = root_dir
        else:
            self.config = config
            
        self.client = QdrantClient(self.config.qdrant_url)
        self.embedding_model = TextEmbedding(self.config.embedding_model_name)
        setup_qdrant_collection(self.client, self.config.collection_name, self.config.vector_size)
    
    def get_files(self) -> List[str]:
        """Get all relevant files from the codebase."""
        return get_files(self.config)
    
    def _analyze_python_module(self, module_path: str) -> Dict:
        """Analyze a Python module and extract its structure."""
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        module_info = {
            "path": module_path,
            "type": "python_module",
            "language": "python",
            "content": content,
            "docstring": "",
            "functions": [],
            "classes": [],
            "imports": [],
            "metrics": {
                "complexity": 0,
                "documentation_coverage": 0
            }
        }
        
        try:
            tree = ast.parse(content)
            module_info["docstring"] = ast.get_docstring(tree) or ""
            
            # Extract functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    module_info["functions"].append({
                        "name": node.name,
                        "docstring": ast.get_docstring(node) or "",
                        "lineno": node.lineno,
                        "complexity": len(list(ast.walk(node)))
                    })
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "docstring": ast.get_docstring(node) or "",
                        "lineno": node.lineno,
                        "methods": []
                    }
                    
                    for method in [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]:
                        class_info["methods"].append({
                            "name": method.name,
                            "docstring": ast.get_docstring(method) or "",
                            "lineno": method.lineno
                        })
                    
                    module_info["classes"].append(class_info)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for name in node.names:
                        module_info["imports"].append(name.name)
            
            # Calculate metrics
            total_nodes = len(list(ast.walk(tree)))
            module_info["metrics"]["complexity"] = total_nodes
            
            # Calculate documentation coverage
            doc_items = [bool(module_info["docstring"])]
            for func in module_info["functions"]:
                doc_items.append(bool(func["docstring"]))
            for cls in module_info["classes"]:
                doc_items.append(bool(cls["docstring"]))
                for method in cls["methods"]:
                    doc_items.append(bool(method["docstring"]))
            
            if doc_items:
                module_info["metrics"]["documentation_coverage"] = sum(doc_items) / len(doc_items)
            
        except SyntaxError:
            # Handle syntax errors gracefully
            pass
        
        return module_info
    
    def analyze_python_module(self, module_path: str) -> Dict:
        """Analyze a Python module and extract its structure."""
        return self._analyze_python_module(module_path)
    
    def analyze_javascript_file(self, file_path: str) -> Dict:
        """Analyze a JavaScript file and extract its structure."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "path": file_path,
            "type": "javascript_module",
            "language": "javascript",
            "content": content,
            "functions": [],
            "classes": [],
            "doc": ""
        }
    
    def analyze_file(self, file_path: str) -> Dict:
        """Analyze a single file."""
        ext = os.path.splitext(file_path)[1]
        language = self.config.supported_extensions.get(ext, 'unknown')
        
        if language == 'python':
            return self._analyze_python_module(file_path)
        elif language in ('javascript', 'typescript'):
            return self.analyze_javascript_file(file_path)
        else:
            # Generic file analysis
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "path": file_path,
                "type": "file",
                "language": language,
                "content": content,
                "size": os.path.getsize(file_path),
                "last_modified": datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                ).isoformat()
            }
    
    def analyze_structure(self) -> Dict[str, Dict]:
        """Analyze the entire codebase structure and index in Qdrant."""
        files = self.get_files()
        results = {}
        
        for file_path in files:
            try:
                rel_path = os.path.relpath(file_path, self.root_dir)
                analysis = self.analyze_file(file_path)
                results[rel_path] = analysis
                
                # Index in Qdrant
                self._index_document(analysis)
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
        
        return results
    
    def _index_document(self, document: Dict) -> None:
        """Index a document in Qdrant."""
        try:
            # Generate embeddings for the document
            content = document.get('content', '')
            if not content:
                return
                
            vector = list(self.embedding_model.embed([content])[0])
            
            # Create a unique ID for the document
            doc_id = hash(f"{document.get('path', '')}:{document.get('type', 'unknown')}")
            
            # Index in Qdrant
            self.client.upsert(
                collection_name=self.config.collection_name,
                points=[
                    models.PointStruct(
                        id=doc_id,
                        payload=document,
                        vector=vector
                    )
                ]
            )
        except Exception as e:
            print(f"Error indexing document: {e}")
    
    def analyze_and_store(self) -> Dict:
        """Analyze the codebase and store results in Qdrant."""
        results = self.analyze_structure()
        return results

class DocumentationGenerator:
    """Generates documentation from analyzed code."""

    def __init__(self, config=None, template_dir=None, output_dir=None):
        """Initialize the documentation generator.
        
        Args:
            config: Configuration object or dictionary
            template_dir: Directory containing templates
            output_dir: Directory to output generated documentation
        """
        if isinstance(config, dict):
            self.config = Config.from_dict(config)
        elif config is None:
            self.config = Config()
        else:
            self.config = config
            
        self.template_dir = template_dir or "templates"
        self.output_dir = output_dir or "docs/generated"
        
        # Set up Jinja2 environment
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def generate_module_docs(self, modules, template=None, output_dir=None):
        """Generate documentation for modules.
        
        Args:
            modules: Dictionary of module information
            template: Jinja2 template to use
            output_dir: Directory to output generated documentation
        """
        output_dir = output_dir or self.output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        if template is None:
            template = self.env.get_template("module.md.j2")
        
        for module_path, module_info in modules.items():
            output_path = os.path.join(output_dir, f"{module_path}.md")
            
            # Create parent directories if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Render template
            content = template.render(
                module_path=module_path,
                module_info=module_info
            )
            
            # Write to file
            with open(output_path, 'w') as f:
                f.write(content)
                
        return True

def analyze_and_index_codebase(
    root_dir: str,
    qdrant_url: Optional[str] = None,
    qdrant_path: Optional[str] = None,
    collection_name: str = "code_documentation",
) -> bool:
    """
    Analyze codebase and index documentation in Qdrant.
    
    Args:
        root_dir: Root directory of the codebase
        qdrant_url: URL of the Qdrant server (optional)
        qdrant_path: Path to local Qdrant storage (optional)
        collection_name: Name of the collection to store documentation
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Initialize Qdrant client
    if qdrant_url:
        client = QdrantClient(url=qdrant_url)
    elif qdrant_path:
        client = QdrantClient(path=qdrant_path)
    else:
        raise ValueError("Either qdrant_url or qdrant_path must be provided")

    # Initialize components
    config = Config(root_dir=root_dir, qdrant_url=qdrant_url, collection_name=collection_name)
    analyzer = CodebaseAnalyzer(root_dir, config)
    indexer = QdrantIndexer(config)
    generator = DocumentationGenerator()

    # Analyze codebase
    modules = analyzer.analyze_structure()

    # Generate and index documentation
    documents = []
    for module in modules:
        doc = generator.generate_module_docs(modules)
        documents.append({
            "content": doc,
            "metadata": {
                "path": module["path"],
                "type": module["type"]
            }
        })

    # Index in Qdrant
    return indexer.index_documents(documents)

if __name__ == '__main__':
    results = analyze_codebase()
    print(json.dumps(results, indent=2)) 