import pytest
from docker import DockerClient
from docker.models.networks import Network
from docker.models.containers import Container
import requests
import time
import os
from typing import Generator
import subprocess

# Skip all tests in this file if SKIP_DOCKER_TESTS is set
pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_DOCKER_TESTS") == "true",
    reason="Docker tests are skipped in this environment"
)

@pytest.fixture(scope="module")
def docker_client() -> DockerClient:
    try:
        return DockerClient.from_env()
    except Exception as e:
        pytest.skip(f"Docker client could not be initialized: {str(e)}")

@pytest.fixture(scope="module")
def docker_network(docker_client: DockerClient) -> Generator[Network, None, None]:
    network_name = "test-mcp-network"
    try:
        network = docker_client.networks.create(network_name, driver="bridge")
        yield network
    except Exception as e:
        pytest.skip(f"Docker network could not be created: {str(e)}")
    finally:
        try:
            network.remove()
        except Exception:
            pass

@pytest.fixture(scope="module")
def qdrant_container(docker_client: DockerClient, docker_network: Network) -> Generator[Container, None, None]:
    container = docker_client.containers.run(
        "qdrant/qdrant:latest",
        name="test-qdrant",
        network=docker_network.name,
        ports={'6333/tcp': 6333, '6334/tcp': 6334},
        detach=True
    )
    
    # Wait for Qdrant to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            # Try both possible health check endpoints
            response = requests.get("http://localhost:6333/collections")
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    else:
        raise Exception("Qdrant failed to start")

    yield container
    
    container.remove(force=True)

@pytest.fixture(scope="module")
def mcp_container(docker_client: DockerClient, docker_network: Network, qdrant_container: Container) -> Generator[Container, None, None]:
    # Get the local image tag
    result = subprocess.run(['docker', 'images', 'quay.io/takinosh/mcp-server-qdrant', '--format', '{{.Tag}}'], capture_output=True, text=True)
    image_tag = result.stdout.strip().split('\n')[0]  # Take only the first tag
    
    if not image_tag:
        raise Exception("Local MCP server image not found. Please build the image first using 'make build'")
    
    container = docker_client.containers.run(
        f"quay.io/takinosh/mcp-server-qdrant:{image_tag}",
        name="test-mcp-server",
        network=docker_network.name,
        environment={
            "QDRANT_URL": "http://test-qdrant:6333",
            "COLLECTION_NAME": "test_collection",
            "LOG_LEVEL": "INFO"
        },
        ports={'8080/tcp': 8080},
        detach=True
    )
    
    # Wait for MCP server to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8080/health")
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    else:
        raise Exception("MCP server failed to start")

    yield container
    
    container.remove(force=True)

def test_docker_image_health_check(mcp_container: Container):
    """Test that the Docker image's health check endpoint is working"""
    response = requests.get("http://localhost:8080/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_docker_image_qdrant_connection(mcp_container: Container):
    """Test that the MCP server can connect to Qdrant"""
    # This endpoint should exist and return successfully if Qdrant connection is working
    response = requests.get("http://localhost:8080/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert "qdrant_status" in data
    assert data["qdrant_status"] == "connected"

def test_docker_image_environment_variables(mcp_container: Container):
    """Test that environment variables are properly set in the container"""
    # Get container environment variables
    env_output = mcp_container.exec_run("env").output.decode()
    
    # Check for required environment variables
    assert "QDRANT_URL=http://test-qdrant:6333" in env_output
    assert "COLLECTION_NAME=test_collection" in env_output
    assert "LOG_LEVEL=INFO" in env_output

def test_docker_image_python_modules(mcp_container: Container):
    """Test that required Python modules are installed and importable"""
    # Try to import key modules
    result = mcp_container.exec_run(
        "python3 -c 'import mcp_server_qdrant.core; print(\"Success\")'")
    assert result.exit_code == 0
    assert b"Success" in result.output 