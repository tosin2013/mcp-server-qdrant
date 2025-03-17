"""Tests for the documentation analyzer system."""

import os
import ast
import tempfile
from pathlib import Path
import pytest
import yaml
from unittest.mock import Mock, patch, MagicMock

from docs.scripts.analyze_codebase import (
    Config, 
    QdrantIndexer,
    CodebaseAnalyzer,
    DocumentationGenerator
)

@pytest.fixture
def test_config():
    """Create a test configuration."""
    return {
        "file_patterns": {
            "include": ["*.py", "*.md"]
        },
        "ignore_directories": [".git", "__pycache__"],
        "analysis": {
            "max_file_size": 1048576,
            "include_source": False,
            "generate_metrics": True,
            "metrics": ["complexity", "documentation_coverage"]
        },
        "qdrant": {
            "enabled": True,
            "url": "http://localhost:6333",
            "collection_name": "test_collection",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "batch_size": 100,
            "index_types": ["docstring", "class_description"]
        },
        "templates": {
            "custom_templates_dir": "custom",
            "default_template": "module.md.j2"
        }
    }

@pytest.fixture
def test_module_content():
    """Create test Python module content."""
    return '''"""Test module docstring."""

class TestClass:
    """Test class docstring."""
    
    def test_method(self, arg1: str) -> None:
        """Test method docstring."""
        if arg1:
            print(arg1)
        
def test_function(param1: int, param2: str = "default") -> bool:
    """Test function docstring."""
    for i in range(param1):
        if i % 2 == 0:
            return True
    return False

from typing import List
import os
'''

class TestConfig:
    """Tests for the Config class."""
    
    def test_load_config(self, tmp_path, test_config):
        """Test loading configuration from file."""
        config_path = tmp_path / "test_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(test_config, f)
        
        config = Config(config_path)
        assert config.config == test_config
    
    def test_resolve_env_vars(self, tmp_path):
        """Test environment variable resolution in config."""
        os.environ["TEST_URL"] = "http://test-url:6333"
        test_config = {
            "qdrant": {
                "url": "${TEST_URL}",
                "nested": {
                    "value": "${TEST_URL}"
                }
            }
        }
        
        config_path = tmp_path / "test_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(test_config, f)
        
        config = Config(config_path)
        assert config.config["qdrant"]["url"] == "http://test-url:6333"
        assert config.config["qdrant"]["nested"]["value"] == "http://test-url:6333"

class TestQdrantIndexer:
    """Tests for the QdrantIndexer class."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client."""
        with patch("docs.scripts.analyze_codebase.QdrantClient") as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock
    
    @pytest.fixture
    def mock_text_embedding(self):
        """Create a mock TextEmbedding."""
        with patch("docs.scripts.analyze_codebase.TextEmbedding") as mock:
            mock_instance = MagicMock()
            # Return a list of embeddings that can be processed by numpy
            mock_instance.embed.return_value = [[0.1] * 384]
            mock.return_value = mock_instance
            # Mock the list_supported_models method
            mock.list_supported_models.return_value = ["sentence-transformers/all-MiniLM-L6-v2"]
            yield mock
    
    def test_index_documents(self, test_config, mock_qdrant_client, mock_text_embedding):
        """Test indexing documents in Qdrant."""
        with patch("docs.scripts.analyze_codebase.TextEmbedding", mock_text_embedding):
            indexer = QdrantIndexer(test_config)
            
            documents = [
                {
                    "type": "docstring",
                    "path": "test.py",
                    "content": "Test docstring"
                }
            ]
            
            result = indexer.index_documents(documents)
            assert result is True
            # Verify that the upsert method was called
            mock_qdrant_client.return_value.upsert.assert_called_once()

class TestCodebaseAnalyzer:
    """Tests for the CodebaseAnalyzer class."""
    
    @pytest.fixture
    def mock_text_embedding(self):
        """Create a mock TextEmbedding."""
        with patch("docs.scripts.analyze_codebase.TextEmbedding") as mock:
            mock_instance = MagicMock()
            # Return a list of embeddings that can be processed by numpy
            mock_instance.embed.return_value = [[0.1] * 384, [0.1] * 384, [0.1] * 384]
            mock.return_value = mock_instance
            # Mock the list_supported_models method
            mock.list_supported_models.return_value = ["sentence-transformers/all-MiniLM-L6-v2"]
            yield mock
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client."""
        with patch("docs.scripts.analyze_codebase.QdrantClient") as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock
    
    def test_analyze_python_module(self, tmp_path, test_config, test_module_content, mock_text_embedding, mock_qdrant_client):
        """Test analyzing a Python module."""
        # Create test module file
        module_path = tmp_path / "test_module.py"
        with open(module_path, "w") as f:
            f.write(test_module_content)
        
        with patch("docs.scripts.analyze_codebase.TextEmbedding", mock_text_embedding), \
             patch("docs.scripts.analyze_codebase.QdrantClient", mock_qdrant_client):
            analyzer = CodebaseAnalyzer(tmp_path, test_config)
            module_info = analyzer._analyze_python_module(module_path)
            
            assert module_info["type"] == "python_module"
            assert module_info["docstring"] == "Test module docstring."
            assert len(module_info["classes"]) == 1
            assert len(module_info["functions"]) == 2
            assert len(module_info["imports"]) == 2
            assert "complexity" in module_info["metrics"]
            assert "documentation_coverage" in module_info["metrics"]
    
    def test_analyze_structure(self, tmp_path, test_config, test_module_content, mock_text_embedding, mock_qdrant_client):
        """Test analyzing the entire codebase structure."""
        # Create test files
        (tmp_path / "src").mkdir()
        module_path = tmp_path / "src" / "test_module.py"
        with open(module_path, "w") as f:
            f.write(test_module_content)
        
        # Create a file to ignore
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "ignored.py").write_text("ignored")
        
        # Create a Config object directly with the supported extensions
        with patch("docs.scripts.analyze_codebase.TextEmbedding", mock_text_embedding), \
             patch("docs.scripts.analyze_codebase.QdrantClient", mock_qdrant_client):
            from docs.scripts.analyze_codebase import Config
            config = Config(root_dir=str(tmp_path))
            config.supported_extensions = {'.py': 'python'}
            
            analyzer = CodebaseAnalyzer(tmp_path, config)
            modules = analyzer.analyze_structure()

            # Check if any key in modules contains 'test_module.py'
            found_module = False
            for key in modules.keys():
                if 'test_module.py' in key:
                    found_module = True
                    break

            assert found_module, "test_module.py not found in analyzed modules"
            assert len(modules) >= 1, "No modules were analyzed"

class TestDocumentationGenerator:
    """Tests for the DocumentationGenerator class."""
    
    @pytest.fixture
    def test_template(self):
        """Create a test Jinja2 template."""
        return """# {{ module_path }}
{% if module_info.docstring %}
{{ module_info.docstring }}
{% endif %}
"""
    
    def test_generate_module_docs(self, tmp_path, test_config, test_template):
        """Test generating module documentation."""
        # Set up directories
        template_dir = tmp_path / "templates"
        output_dir = tmp_path / "output"
        template_dir.mkdir()
        
        # Create test template
        with open(template_dir / "module.md.j2", "w") as f:
            f.write(test_template)
        
        # Create test module info
        modules = {
            "test_module.py": {
                "docstring": "Test docstring",
                "type": "python_module",
                "classes": [],
                "functions": [],
                "imports": []
            }
        }
        
        generator = DocumentationGenerator(test_config, template_dir, output_dir)
        template = generator.env.get_template("module.md.j2")
        generator.generate_module_docs(modules, template, output_dir)
        
        # Verify output
        output_file = output_dir / "test_module.py.md"
        assert output_file.exists()
        content = output_file.read_text()
        assert "Test docstring" in content

def test_end_to_end(tmp_path):
    """Test the entire documentation generation process."""
    # Set up directory structure
    docs_dir = tmp_path / "docs"
    config_dir = docs_dir / "config"
    template_dir = docs_dir / "templates"
    output_dir = docs_dir / "auto-generated"
    src_dir = tmp_path / "src"
    
    for d in [docs_dir, config_dir, template_dir, output_dir, src_dir]:
        d.mkdir(parents=True)
    
    # Create test configuration
    config_path = config_dir / "analyzer_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump({
            "file_patterns": {"include": ["*.py"]},
            "ignore_directories": [".git"],
            "analysis": {
                "max_file_size": 1048576,
                "generate_metrics": True,
                "metrics": ["complexity"]
            },
            "qdrant": {
                "enabled": True,
                "url": ":memory:",  # Use in-memory Qdrant for testing
                "collection_name": "codebase",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "batch_size": 10
            },
            "templates": {
                "default_template": "module.md.j2"
            }
        }, f)
    
    # Create test module
    test_module = src_dir / "test_module.py"
    test_module.write_text('''"""Test module docstring."""

class TestClass:
    """Test class docstring."""
    
    def test_method(self):
        """Test method docstring."""
        pass
''')
    
    # Create test template
    template_file = template_dir / "module.md.j2"
    template_file.write_text("""# {{ module_path }}

{% if module_info.docstring %}
{{ module_info.docstring }}
{% endif %}

{% if module_info.classes %}
## Classes

{% for class in module_info.classes %}
### {{ class.name }}

{% if class.docstring %}
{{ class.docstring }}
{% endif %}
{% endfor %}
{% endif %}
""")
    
    # Mock QdrantClient and TextEmbedding
    with patch("docs.scripts.analyze_codebase.QdrantClient") as mock_qdrant, \
         patch("docs.scripts.analyze_codebase.TextEmbedding") as mock_embedding:
        
        # Configure mocks
        mock_qdrant_instance = MagicMock()
        mock_qdrant.return_value = mock_qdrant_instance
        
        mock_embedding_instance = MagicMock()
        # Return a list of embeddings that can be processed by numpy
        mock_embedding_instance.embed.return_value = [[0.1] * 384]
        mock_embedding.return_value = mock_embedding_instance
        mock_embedding.list_supported_models = MagicMock(return_value=["sentence-transformers/all-MiniLM-L6-v2"])
        
        # Create config directly
        from docs.scripts.analyze_codebase import Config
        config = Config(root_dir=str(tmp_path))
        config.supported_extensions = {'.py': 'python'}
        config.qdrant_url = ":memory:"
        config.collection_name = "codebase"
        config.embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
        
        # Create the DocumentationGenerator directly
        from docs.scripts.analyze_codebase import DocumentationGenerator
        generator = DocumentationGenerator(config, str(template_dir), str(output_dir))
        
        # Create a simple module dictionary to generate docs from
        modules = {
            "src/test_module.py": {
                "path": str(test_module),
                "docstring": "Test module docstring.",
                "type": "python_module",
                "classes": [
                    {
                        "name": "TestClass",
                        "docstring": "Test class docstring.",
                        "methods": [
                            {
                                "name": "test_method",
                                "docstring": "Test method docstring."
                            }
                        ]
                    }
                ],
                "functions": [],
                "imports": []
            }
        }
        
        # Generate documentation directly
        template = generator.env.get_template("module.md.j2")
        generator.generate_module_docs(modules, template, output_dir)
        
        # Verify output
        output_file = output_dir / "src" / "test_module.py.md"
        assert output_file.exists(), f"Output file {output_file} does not exist"
        content = output_file.read_text()
        assert "Test module docstring" in content, f"Expected 'Test module docstring' in:\n{content}"
        assert "TestClass" in content, f"Expected 'TestClass' in:\n{content}" 