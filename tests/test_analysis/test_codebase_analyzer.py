"""Tests for the codebase analyzer."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from qdrant_client import QdrantClient

from mcp_server_qdrant.analysis import CodebaseAnalyzer
from mcp_server_qdrant.analysis.config import AnalysisConfig

SAMPLE_PYTHON_FILE = '''
"""Sample module docstring."""

import os
import sys
from typing import List, Optional

def hello_world(name: str = "World") -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

class Calculator:
    """A simple calculator class."""
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b
'''

SAMPLE_JAVASCRIPT_FILE = '''
// Sample JavaScript file

function greet(name = "World") {
    return `Hello, ${name}!`;
}

class Person {
    constructor(name) {
        this.name = name;
    }
    
    sayHello() {
        return greet(this.name);
    }
}

export { greet, Person };
'''

SAMPLE_MARKDOWN_FILE = '''
# Sample Project

This is a sample project for testing the codebase analyzer.

## Features
- Python code analysis
- JavaScript code analysis
- Documentation analysis

## Usage
See the examples in the code.
'''

SAMPLE_CONFIG_FILE = '''
{
    "name": "sample-project",
    "version": "1.0.0",
    "description": "A sample project for testing"
}
'''

@pytest.fixture
def sample_repo() -> Generator[str, None, None]:
    """Create a temporary sample repository."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create directory structure
        src_dir = Path(temp_dir) / "src"
        src_dir.mkdir()
        
        # Python package
        pkg_dir = src_dir / "sample_pkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").touch()
        
        with open(pkg_dir / "main.py", "w") as f:
            f.write(SAMPLE_PYTHON_FILE)
            
        # JavaScript files
        js_dir = src_dir / "web"
        js_dir.mkdir()
        
        with open(js_dir / "app.js", "w") as f:
            f.write(SAMPLE_JAVASCRIPT_FILE)
            
        # Documentation
        docs_dir = Path(temp_dir) / "docs"
        docs_dir.mkdir()
        
        with open(docs_dir / "README.md", "w") as f:
            f.write(SAMPLE_MARKDOWN_FILE)
            
        # Configuration
        with open(Path(temp_dir) / "config.json", "w") as f:
            f.write(SAMPLE_CONFIG_FILE)
        
        yield temp_dir

@pytest.fixture
def qdrant_client():
    """Create a Qdrant client for testing."""
    return QdrantClient(":memory:")

@pytest.fixture
def analyzer(sample_repo):
    """Create a CodebaseAnalyzer instance for testing."""
    config = AnalysisConfig(root_dir=sample_repo)
    return CodebaseAnalyzer(root_dir=sample_repo, config=config)

def test_analyzer_finds_all_files(sample_repo, analyzer):
    """Test that the analyzer finds all relevant files."""
    files = analyzer.get_files()
    
    # Check if all expected files are found
    expected_files = {
        "main.py",
        "app.js",
        "README.md",
        "config.json",
        "__init__.py"
    }
    
    found_files = {Path(f).name for f in files}
    assert found_files == expected_files

def test_python_file_analysis(sample_repo, analyzer):
    """Test analysis of Python files."""
    python_file = Path(sample_repo) / "src" / "sample_pkg" / "main.py"
    analysis = analyzer.analyze_file(str(python_file))
    
    assert analysis["language"] == "python"
    assert "Calculator" in analysis["content"]
    assert "hello_world" in analysis["content"]

def test_javascript_file_analysis(sample_repo, analyzer):
    """Test analysis of JavaScript files."""
    js_file = Path(sample_repo) / "src" / "web" / "app.js"
    analysis = analyzer.analyze_file(str(js_file))
    
    assert analysis["language"] == "javascript"
    assert "greet" in analysis["content"]
    assert "Person" in analysis["content"]

def test_markdown_file_analysis(sample_repo, analyzer):
    """Test analysis of Markdown files."""
    md_file = Path(sample_repo) / "docs" / "README.md"
    analysis = analyzer.analyze_file(str(md_file))
    
    assert analysis["language"] == "markdown"
    assert "Sample Project" in analysis["content"]
    assert "Features" in analysis["content"]

def test_full_analysis(sample_repo, qdrant_client, analyzer):
    """Test the full analysis process."""
    # Run the analysis
    results = analyzer.analyze_structure()
    
    # Check that all files were analyzed
    assert len(results) >= 4  # At least 4 files should be analyzed
    
    # Check that different file types were recognized
    languages = {r.get("language") for r in results if r.get("language")}
    assert "python" in languages
    assert "javascript" in languages
    assert "markdown" in languages 