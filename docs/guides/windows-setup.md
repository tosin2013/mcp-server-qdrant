# Windows Setup Guide

This guide provides instructions for running the MCP Server Qdrant on Windows using Docker Desktop.

## Prerequisites

1. **Windows System Requirements**
   - Windows 10/11 Pro, Enterprise, or Education (64-bit)
   - WSL 2 enabled
   - 8GB RAM recommended
   - 20GB free disk space

2. **Docker Desktop**
   - [Download and install Docker Desktop](https://www.docker.com/products/docker-desktop)
   - Enable WSL 2 backend in Docker Desktop settings

3. **Git for Windows**
   - [Download and install Git](https://git-scm.com/download/win)
   - Required for cloning the repository and build process

## Installation

### 1. Install Docker Desktop

1. Download Docker Desktop from the [official website](https://www.docker.com/products/docker-desktop)
2. Run the installer and follow the prompts
3. During installation, ensure the "WSL 2" option is selected
4. After installation, start Docker Desktop
5. Open PowerShell and verify the installation:
   ```powershell
   docker --version
   docker-compose --version
   ```

### 2. Enable WSL 2 (if not already enabled)

Open PowerShell as Administrator and run:
```powershell
# Enable WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Enable Virtual Machine Platform
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Set WSL 2 as default
wsl --set-default-version 2
```

### 3. Clone the Repository

```powershell
git clone https://github.com/modelcontextprotocol/mcp-server-qdrant.git
cd mcp-server-qdrant
```

### 4. Build the Container Image

The project uses a Makefile to simplify the build process. In PowerShell:

```powershell
# Build the image using Docker
docker-compose build
```

## Running the Services

### Using Docker Compose

The project includes a `docker-compose.yml` for easy deployment:

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
```powershell
docker-compose up -d
```

### Manual Container Management

If not using docker-compose:

```powershell
# Create network
docker network create mcp-network

# Create data directories
mkdir -p data/qdrant data/mcp

# Run Qdrant
docker run -d `
    --name qdrant `
    --network mcp-network `
    -p 6333:6333 `
    -p 6334:6334 `
    -v ${PWD}/data/qdrant:/qdrant/storage `
    docker.io/qdrant/qdrant:latest

# Run MCP server
docker run -d `
    --name mcp-server `
    --network mcp-network `
    -p 8080:8080 `
    -e QDRANT_URL=http://qdrant:6333 `
    -e MCP_COLLECTION=mcp_unified_store `
    -e LOG_LEVEL=INFO `
    -v ${PWD}/data/mcp:/data/mcp `
    mcp-server-qdrant:latest
```

## Container Management

### Basic Commands

```powershell
# Using docker-compose
docker-compose ps
docker-compose logs -f
docker-compose down
docker-compose up -d --build

# Direct docker commands
docker ps
docker logs -f mcp-server
docker logs -f qdrant
docker stop mcp-server qdrant
docker start mcp-server qdrant
```

## Claude Desktop Integration

### Configuration

Create or edit the Claude Desktop configuration file at `%APPDATA%\Claude Desktop\claude_desktop_config.json`.

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
      "-e", "MCP_COLLECTION=mcp_unified_store",
      "-e", "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2",
      "-e", "LOG_LEVEL=INFO",
      "mcp-server-qdrant:latest"
    ]
  }
}
```

#### 2. Cloud-Hosted Qdrant

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
      "-e", "MCP_COLLECTION=your-collection-name",
      "-e", "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2",
      "-e", "LOG_LEVEL=INFO",
      "mcp-server-qdrant:latest"
    ]
  }
}
```

### Configuration Options

1. **Local Docker Setup**:
   - Uses Docker network for communication between services
   - Requires running Qdrant container locally
   - No API key needed for local deployment
   - Requires Docker Desktop with WSL 2

2. **Cloud-Hosted Setup**:
   - Uses cloud-hosted Qdrant instance
   - Requires valid API key
   - No local Qdrant container needed
   - Supports custom collection names
   - Works with or without WSL 2

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
   - The MCP server needs to be on the same Docker network as Qdrant
   - The `--network mcp-network` flag ensures this connectivity
   - Docker Desktop must be running for network communication

2. **Port Mapping**:
   - The server runs on port 8080 internally and is mapped to the same port externally
   - Ensure this port is available on your system
   - Windows Defender Firewall may need to allow this port

3. **Container Cleanup**:
   - The `--rm` flag automatically removes the container when it stops
   - This prevents accumulation of stopped containers

### Verifying the Setup

1. Start Qdrant using docker-compose:
   ```powershell
   docker-compose up -d qdrant
   ```

2. Open Claude Desktop and check the logs for successful connection
3. Test the connection by making a query in Claude Desktop

### Windows-Specific Considerations

1. **File Paths**:
   - Use Windows-style paths in the configuration
   - Environment variables like `%APPDATA%` are supported
   - Use double backslashes or forward slashes in paths

2. **Docker Desktop Settings**:
   - Ensure WSL 2 integration is enabled
   - Check resource allocation in Docker Desktop settings
   - Enable file sharing for required directories

### Troubleshooting Claude Desktop Integration

1. **Connection Issues**:
   - Verify Docker Desktop is running
   - Check Qdrant is running: `docker ps | grep qdrant`
   - Check Qdrant logs: `docker logs qdrant`
   - Ensure the Docker network exists: `docker network ls`

2. **Configuration Problems**:
   - Validate JSON syntax in `claude_desktop_config.json`
   - Check file permissions on the config file
   - Verify Claude Desktop logs for configuration errors
   - Ensure Docker Desktop has started completely

3. **Port Conflicts**:
   - Check if port 8080 is in use: `netstat -ano | findstr :8080`
   - Try a different port mapping if needed (e.g., `-p 8081:8080`)
   - Check Windows Defender Firewall settings

4. **WSL 2 Issues**:
   - Verify WSL 2 is running: `wsl --status`
   - Check Docker Desktop WSL integration
   - Restart WSL if needed: `wsl --shutdown`

## Troubleshooting

### Common Issues

1. **WSL 2 Issues**
   ```powershell
   # Check WSL version
   wsl --status
   
   # Update WSL
   wsl --update
   
   # Restart WSL
   wsl --shutdown
   ```

2. **Network Issues**
   ```powershell
   # Check container networking
   docker network ls
   docker network inspect mcp-network
   
   # Test container connectivity
   docker exec mcp-server curl -v http://qdrant:6333/health
   ```

3. **Volume Permissions**
   ```powershell
   # Check volume permissions
   icacls .\data\qdrant
   icacls .\data\mcp
   
   # Fix permissions if needed
   icacls .\data /grant "Users":(OI)(CI)F
   ```

4. **Docker Desktop Issues**
   - Check Docker Desktop is running
   - Verify WSL 2 integration is enabled in settings
   - Restart Docker Desktop if needed

### Health Checks

The services expose health check endpoints:

- MCP Server: http://localhost:8080/health
- Qdrant: http://localhost:6333/health

## References

- [Docker Desktop Documentation](https://docs.docker.com/desktop/windows/)
- [WSL Documentation](https://docs.microsoft.com/en-us/windows/wsl/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Model Context Protocol Documentation](https://modelcontextprotocol.io/) 