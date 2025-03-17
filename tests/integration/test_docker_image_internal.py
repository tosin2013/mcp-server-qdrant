"""Tests to be run INSIDE the Docker container"""
import os
import pytest
import importlib
import sys
from pathlib import Path

@pytest.fixture(autouse=True)
def skip_if_not_in_docker():
    """Skip tests if not running in a Docker container."""
    if not os.path.exists("/.dockerenv"):
        pytest.skip("Test only runs in Docker container")

def test_python_environment():
    """Test Python environment is correctly set up."""
    assert sys.version_info.major == 3, "Python major version should be 3"
    assert sys.version_info.minor >= 10, "Python minor version should be at least 10"

def test_required_modules_installed():
    """Test required modules are installed."""
    try:
        importlib.import_module("fastapi")
    except ImportError as e:
        pytest.fail(f"Failed to import fastapi: {str(e)}")
    
    try:
        importlib.import_module("qdrant_client")
    except ImportError as e:
        pytest.fail(f"Failed to import qdrant_client: {str(e)}")
    
    try:
        importlib.import_module("mcp_server_qdrant")
    except ImportError as e:
        pytest.fail(f"Failed to import mcp_server_qdrant: {str(e)}")

def test_environment_variables():
    """Test environment variables are set."""
    required_vars = [
        "QDRANT_URL",
        "COLLECTION_NAME",
        "EMBEDDING_PROVIDER",
        "EMBEDDING_MODEL"
    ]
    
    for var in required_vars:
        assert var in os.environ, f"Environment variable {var} not found"

def test_file_permissions():
    """Test file permissions are correct."""
    # Check source directory exists
    src_dir = Path("/app/src/mcp_server_qdrant")
    assert src_dir.exists(), f"Path {src_dir} does not exist"
    
    # Check main module is executable
    main_py = src_dir / "main.py"
    assert main_py.exists(), f"Path {main_py} does not exist"
    assert os.access(main_py, os.X_OK), f"File {main_py} is not executable" 