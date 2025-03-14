# Docker Desktop Setup Guide

This guide provides instructions for running the MCP Server Qdrant using Docker Desktop across Windows, macOS, and Linux platforms.

> **Note for RHEL 9 Users**: If you're using RHEL 9 or compatible distributions, please refer to our [RHEL 9 Podman Setup Guide](./rhel-podman-setup.md) for platform-specific instructions using Podman.

## Prerequisites

1. **Docker Desktop**
   - Windows: [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
   - macOS: [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
   - Linux: [Docker Desktop for Linux](https://docs.docker.com/desktop/install/linux-install/)

2. **Claude Desktop**
   - Pro subscription required
   - Latest version installed

## Docker Configuration

### 1. Install Docker Desktop

#### Windows
1. Download and run Docker Desktop Installer for Windows
2. Enable WSL 2 if prompted
3. Log out and log back in when installation completes

#### macOS
1. Download Docker Desktop for Mac (Intel or Apple Silicon)
2. Drag to Applications folder
3. Open Docker Desktop and complete installation

#### Linux (Ubuntu example)
```bash
# Add Docker's official GPG key
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Desktop
sudo apt-get update
sudo apt-get install docker-desktop
```

### 2. Configure Claude Desktop

Create or edit your `claude_desktop_config.json`:

#### Windows (`%APPDATA%\Claude Desktop\claude_desktop_config.json`):
```json
{
  "servers": [
    {
      "type": "qdrant",
      "config": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "-p", "8000:8000",
          "--name", "mcp-qdrant",
          "-e", "COLLECTION_NAME=memories",
          "-e", "QDRANT_URL=http://host.docker.internal:6333",
          "-e", "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2",
          "mcp-server-qdrant:latest"
        ],
        "env": {
          "DOCKER_HOST": "npipe:////.//pipe//docker_engine"
        }
      }
    }
  ]
}
```

#### macOS/Linux (`~/.config/Claude Desktop/claude_desktop_config.json`):
```json
{
  "servers": [
    {
      "type": "qdrant",
      "config": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "-p", "8000:8000",
          "--name", "mcp-qdrant",
          "-e", "COLLECTION_NAME=memories",
          "-e", "QDRANT_URL=http://host.docker.internal:6333",
          "-e", "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2",
          "mcp-server-qdrant:latest"
        ]
      }
    }
  ]
}
```

### 3. Build the Docker Image

From the project directory:

```bash
# Clone the repository (if not already done)
git clone https://github.com/yourusername/mcp-server-qdrant.git
cd mcp-server-qdrant

# Build the image
docker build \
    --build-arg VERSION=$(cat VERSION) \
    --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
    --build-arg VCS_REF=$(git rev-parse --short HEAD) \
    -t mcp-server-qdrant:latest .
```

### 4. Running Qdrant

You'll need a running Qdrant instance. Here's how to run it with Docker:

```bash
# Create a volume for persistent storage
docker volume create qdrant_storage

# Run Qdrant container
docker run -d \
    --name qdrant \
    -p 6333:6333 \
    -p 6334:6334 \
    -v qdrant_storage:/qdrant/storage \
    qdrant/qdrant
```

## Usage

### Starting the Server

The server will start automatically when Claude Desktop launches, based on the configuration in `claude_desktop_config.json`.

To manually start the server:

```bash
# Windows CMD
docker run -d -p 8000:8000 ^
    --name mcp-qdrant ^
    -e COLLECTION_NAME=memories ^
    -e QDRANT_URL=http://host.docker.internal:6333 ^
    -e EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 ^
    mcp-server-qdrant:latest

# macOS/Linux
docker run -d -p 8000:8000 \
    --name mcp-qdrant \
    -e COLLECTION_NAME=memories \
    -e QDRANT_URL=http://host.docker.internal:6333 \
    -e EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 \
    mcp-server-qdrant:latest
```

### Stopping the Server

```bash
docker stop mcp-qdrant
```

### Viewing Logs

```bash
docker logs mcp-qdrant
```

## Troubleshooting

### Common Issues

1. **Container Network Issues**
   - Ensure Qdrant is accessible via `host.docker.internal`
   - Check Docker network settings
   - Verify ports are not in use

2. **Permission Issues**
   - Run Docker Desktop as administrator (Windows)
   - Check Docker group membership (Linux)
   - Verify file permissions

3. **Resource Constraints**
   - Check Docker Desktop resource settings
   - Monitor container resource usage
   - Increase allocated memory if needed

### Docker Commands for Debugging

```bash
# Check container status
docker ps -a

# View container logs
docker logs mcp-qdrant

# Inspect container
docker inspect mcp-qdrant

# Check container resources
docker stats mcp-qdrant
```

## Advanced Configuration

### Using Custom Networks

```bash
# Create a custom network
docker network create mcp-network

# Run Qdrant in the network
docker run -d --network mcp-network --name qdrant qdrant/qdrant

# Run MCP server in the same network
docker run -d --network mcp-network \
    -e QDRANT_URL=http://qdrant:6333 \
    -e COLLECTION_NAME=memories \
    mcp-server-qdrant:latest
```

### Using Environment Files

Create a `.env` file:
```env
COLLECTION_NAME=memories
QDRANT_URL=http://host.docker.internal:6333
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

Run with environment file:
```bash
docker run -d --env-file .env mcp-server-qdrant:latest
```

## References

- [Docker Desktop Documentation](https://docs.docker.com/desktop/)
- [Qdrant Docker Guide](https://qdrant.tech/documentation/guides/installation/#docker)
- [Model Context Protocol Documentation](https://modelcontextprotocol.io/) 