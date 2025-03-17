# RHEL 9 Podman Setup Guide

This guide provides instructions for running the MCP Server Qdrant on RHEL 9 using Podman.

## Prerequisites

1. **RHEL 9 System Requirements**
   - RHEL 9 or compatible distribution (CentOS Stream 9, Rocky Linux 9, etc.)
   - Minimum 4GB RAM
   - 20GB free disk space
   - sudo/root access

2. **Git**
   - Required for cloning the repository and build process

## Installation

### 1. Install Podman and Dependencies

```bash
# Install required packages
sudo dnf update -y
sudo dnf install -y podman podman-docker container-tools

# Optional: Install podman-compose
sudo dnf install -y python3-pip
pip3 install --user podman-compose
```

### 2. Configure Podman

```bash
# Enable and start podman socket for Docker compatibility
systemctl --user enable podman.socket
systemctl --user start podman.socket

# Set up environment variables
echo 'export DOCKER_HOST="unix://$XDG_RUNTIME_DIR/podman/podman.sock"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Configure SELinux (if enabled)

```bash
# Allow container network access
sudo setsebool -P container_manage_cgroup 1

# Allow container volume access
sudo semanage fcontext -a -t container_file_t "./data/qdrant(/.*)?"
sudo restorecon -Rv ./data/qdrant
```

### 4. Clone the Repository

```bash
git clone https://github.com/modelcontextprotocol/mcp-server-qdrant.git
cd mcp-server-qdrant
```

### 5. Build the Container Image

The project uses a Makefile to simplify the build process:

```bash
# Set container runtime to podman
export CONTAINER_RUNTIME=podman

# Build the image
make build
```

This will:
- Generate requirements from pyproject.toml
- Build a multi-stage container image
- Tag the image appropriately

## Running the Services

### Using Podman Compose

The project includes a `podman-compose.yml` for easy deployment:

```yaml
version: '3.8'

services:
  mcp-server:
    build:
      context: .
      dockerfile: Containerfile
    ports:
      - "8080:8080"
    environment:
      - QDRANT_URL=http://qdrant:6333
      - MCP_COLLECTION=mcp_unified_store
      - LOG_LEVEL=INFO
    depends_on:
      - qdrant
    volumes:
      - ./data/mcp:/data/mcp
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

  qdrant:
    image: docker.io/qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./data/qdrant:/qdrant/storage
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

networks:
  mcp-network:
    driver: bridge
```

Start the services:
```bash
podman-compose up -d
```

### Manual Container Management

If not using podman-compose:

```bash
# Create network
podman network create mcp-network

# Run Qdrant
podman run -d \
    --name qdrant \
    --network mcp-network \
    -p 6333:6333 \
    -p 6334:6334 \
    -v ./data/qdrant:/qdrant/storage \
    docker.io/qdrant/qdrant:latest

# Run MCP server
podman run -d \
    --name mcp-server \
    --network mcp-network \
    -p 8080:8080 \
    -e QDRANT_URL=http://qdrant:6333 \
    -e MCP_COLLECTION=mcp_unified_store \
    -e LOG_LEVEL=INFO \
    -v ./data/mcp:/data/mcp \
    localhost/mcp-server-qdrant:latest
```

## Container Management

### Basic Commands

```bash
# Using podman-compose
podman-compose ps
podman-compose logs -f
podman-compose down
podman-compose up -d --build

# Direct podman commands
podman ps
podman logs -f mcp-server
podman logs -f qdrant
podman stop mcp-server qdrant
podman start mcp-server qdrant
```

## Claude Desktop Integration

### Configuration

Create or edit the Claude Desktop configuration file at `~/.config/Claude Desktop/claude_desktop_config.json`.

Choose the appropriate configuration based on your setup:

#### 1. Local Podman Setup (Recommended)

```json
{
  "qdrant": {
    "command": "podman",
    "args": [
      "run",
      "--rm",
      "--network", "mcp-network",
      "-p", "8080:8080",
      "-e", "QDRANT_URL=http://qdrant:6333",
      "-e", "MCP_COLLECTION=mcp_unified_store",
      "-e", "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2",
      "-e", "LOG_LEVEL=INFO",
      "localhost/mcp-server-qdrant:latest"
    ]
  }
}
```

#### 2. Cloud-Hosted Qdrant

```json
{
  "qdrant": {
    "command": "podman",
    "args": [
      "run",
      "--rm",
      "-p", "8080:8080",
      "-e", "QDRANT_URL=https://xyz-example.eu-central.aws.cloud.qdrant.io:6333",
      "-e", "QDRANT_API_KEY=your_api_key",
      "-e", "MCP_COLLECTION=your-collection-name",
      "-e", "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2",
      "-e", "LOG_LEVEL=INFO",
      "localhost/mcp-server-qdrant:latest"
    ]
  }
}
```

### Configuration Options

1. **Local Podman Setup**:
   - Uses Podman network for communication between services
   - Requires running Qdrant container locally
   - No API key needed for local deployment
   - SELinux contexts must be properly set

2. **Cloud-Hosted Setup**:
   - Uses cloud-hosted Qdrant instance
   - Requires valid API key
   - No local Qdrant container needed
   - Supports custom collection names
   - May require additional SELinux network permissions

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| QDRANT_URL | URL of the Qdrant service | `http://qdrant:6333` or `https://cloud.qdrant.io:6333` |
| QDRANT_API_KEY | API key for cloud-hosted Qdrant | `your_api_key` |
| MCP_COLLECTION | Name of the Qdrant collection | `mcp_unified_store` |
| EMBEDDING_MODEL | Model for text embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| LOG_LEVEL | Logging verbosity | `INFO` |

### Important Notes

1. **Network Configuration**: 
   - The MCP server needs to be on the same Podman network as Qdrant
   - The `--network mcp-network` flag ensures this connectivity
   - SELinux contexts must be properly set for network communication

2. **Port Mapping**:
   - The server runs on port 8080 internally and is mapped to the same port externally
   - Ensure this port is available on your system
   - SELinux may need to be configured to allow port binding

3. **Environment Variables**:
   - `QDRANT_URL`: Points to the Qdrant service using the container network DNS
   - `MCP_COLLECTION`: Specifies the collection name in Qdrant
   - `LOG_LEVEL`: Controls the verbosity of logging

4. **Container Cleanup**:
   - The `--rm` flag automatically removes the container when it stops
   - This prevents accumulation of stopped containers

### Verifying the Setup

1. Start Qdrant using podman-compose:
   ```bash
   podman-compose up -d qdrant
   ```

2. Open Claude Desktop and check the logs for successful connection
3. Test the connection by making a query in Claude Desktop

### SELinux Configuration for Claude Desktop

If SELinux is enabled, you may need additional configuration:

```bash
# Allow Claude Desktop to execute podman commands
sudo semanage fcontext -a -t container_runtime_exec_t $(which podman)
sudo restorecon -v $(which podman)

# Allow network connections
sudo setsebool -P container_connect_any 1
```

### Troubleshooting Claude Desktop Integration

1. **Connection Issues**:
   - Verify Qdrant is running: `podman ps | grep qdrant`
   - Check Qdrant logs: `podman logs qdrant`
   - Ensure the Podman network exists: `podman network ls`
   - Check SELinux denials: `sudo ausearch -m AVC -ts recent`

2. **Configuration Problems**:
   - Validate JSON syntax in `claude_desktop_config.json`
   - Verify file permissions on the config file
   - Check Claude Desktop logs for configuration errors
   - Ensure Podman socket is running: `systemctl --user status podman.socket`

3. **Port Conflicts**:
   - Ensure no other service is using port 8080
   - Try a different port mapping if needed (e.g., `-p 8081:8080`)
   - Check SELinux port contexts: `semanage port -l | grep 8080`

## Troubleshooting

### Common Issues

1. **SELinux Conflicts**
   ```bash
   # Check SELinux status
   getenforce
   
   # View SELinux denials
   sudo ausearch -m AVC -ts recent
   
   # Set correct context for volumes
   sudo semanage fcontext -a -t container_file_t "./data(/.*)?"
   sudo restorecon -Rv ./data
   ```

2. **Network Issues**
   ```bash
   # Check container networking
   podman network ls
   podman network inspect mcp-network
   
   # Test container connectivity
   podman exec mcp-server curl -v http://qdrant:6333/health
   ```

3. **Volume Permissions**
   ```bash
   # Check volume permissions
   ls -la ./data/qdrant
   ls -la ./data/mcp
   
   # Fix ownership if needed
   sudo chown -R $USER:$USER ./data
   ```

### Health Checks

The services expose health check endpoints:

- MCP Server: http://localhost:8080/health
- Qdrant: http://localhost:6333/health

## References

- [Podman Documentation](https://docs.podman.io/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Model Context Protocol Documentation](https://modelcontextprotocol.io/) 