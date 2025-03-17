# Docker Desktop Setup Guide

This guide provides instructions for running the MCP Server Qdrant using Docker Desktop across Windows, macOS, and Linux platforms.

> **Note for RHEL 9 Users**: If you're using RHEL 9 or compatible distributions, please refer to our [RHEL 9 Podman Setup Guide](./rhel-podman-setup.md) for platform-specific instructions using Podman.

## Prerequisites

1. **Docker Desktop**
   - Windows: [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
   - macOS: [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
   - Linux: [Docker Desktop for Linux](https://docs.docker.com/desktop/install/linux-install/)

2. **Git**
   - Required for cloning the repository and build process

## Installation

### 1. Install Docker Desktop

Follow the standard installation process for your platform from the [Docker Desktop Documentation](https://docs.docker.com/desktop/).

### 2. Clone the Repository

```bash
git clone https://github.com/modelcontextprotocol/mcp-server-qdrant.git
cd mcp-server-qdrant
```

### 3. Build the Docker Image

The project uses a Makefile to simplify the build process:

```bash
# Build the image
make build
```

This will:
- Generate requirements from pyproject.toml
- Build a multi-stage Docker image
- Tag the image as both latest and version-specific tags

### 4. Start the Services

The project includes a docker-compose.yml for easy deployment:

```bash
# Start both Qdrant and MCP server
docker compose up -d
```

This will start:
- Qdrant on ports 6333 (HTTP) and 6334 (GRPC)
- MCP Server on port 8080

## Configuration

### Environment Variables

The MCP server supports the following environment variables:

```bash
QDRANT_URL=http://qdrant:6333      # URL of the Qdrant service
COLLECTION_NAME=mcp_unified_store   # Name of the Qdrant collection
LOG_LEVEL=INFO                     # Logging level
```

### Docker Compose Configuration

The default `docker-compose.yml` provides a production-ready setup:

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
      - COLLECTION_NAME=mcp_unified_store
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
    image: qdrant/qdrant:latest
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

## Usage

### Managing the Services

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Rebuild and restart
docker compose up -d --build
```

### Health Checks

The services expose health check endpoints:

- MCP Server: http://localhost:8080/health
- Qdrant: http://localhost:6333/health

## Claude Desktop Integration

### Configuration

Create or edit the Claude Desktop configuration file:

- **Windows**: `%APPDATA%\Claude Desktop\claude_desktop_config.json`
- **macOS/Linux**: `~/.config/Claude Desktop/claude_desktop_config.json`

### Setup Steps

1. **Create Docker Network** (if not already created):
```bash
docker network create mcp-network
```

2. **Start Qdrant** (if using local Qdrant):
```bash
docker run -d \
    --name qdrant \
    --network mcp-network \
    -p 6333:6333 \
    -p 6334:6334 \
    -v ./data/qdrant:/qdrant/storage \
    docker.io/qdrant/qdrant:latest
```

3. **Configure Claude Desktop**

Choose the appropriate configuration based on your setup:

#### 1. Local Docker Setup (Recommended)

```json
{
  "qdrant": {
    "command": "docker",
    "args": [
      "run",
      "--rm",
      "--network", "mcp-network",
      "-p", "8080:8080",
      "-e", "QDRANT_URL=http://qdrant:6333",
      "-e", "COLLECTION_NAME=mcp_unified_store",
      "-e", "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2",
      "-e", "LOG_LEVEL=INFO",
      "-e", "PYTHONPATH=/usr/local/lib/python3.11/site-packages",
      "quay.io/takinosh/mcp-server-qdrant:v0.7.1"
    ]
  }
}
```

#### 2. Cloud-Hosted Qdrant

For cloud-hosted Qdrant, you don't need the Docker network:

```json
{
  "qdrant": {
    "command": "docker",
    "args": [
      "run",
      "--rm",
      "-p", "8080:8080",
      "-e", "QDRANT_URL=https://xyz-example.eu-central.aws.cloud.qdrant.io:6333",
      "-e", "QDRANT_API_KEY=your_api_key",
      "-e", "COLLECTION_NAME=your-collection-name",
      "-e", "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2",
      "-e", "LOG_LEVEL=INFO",
      "-e", "PYTHONPATH=/usr/local/lib/python3.11/site-packages",
      "quay.io/takinosh/mcp-server-qdrant:v0.7.1"
    ]
  }
}
```