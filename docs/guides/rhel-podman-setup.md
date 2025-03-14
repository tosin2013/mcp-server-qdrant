# RHEL 9 Podman Setup Guide

This guide provides instructions for running the MCP Server Qdrant on RHEL 9 using Podman.

## Prerequisites

1. **RHEL 9 System Requirements**
   - RHEL 9 or compatible distribution (CentOS Stream 9, Rocky Linux 9, etc.)
   - Minimum 4GB RAM
   - 20GB free disk space
   - sudo/root access

2. **Claude Desktop**
   - Pro subscription required
   - Latest version installed

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

# Optional: Create aliases for Docker commands
echo 'alias docker=podman' >> ~/.bashrc
source ~/.bashrc
```

### 3. Configure SELinux (if enabled)

```bash
# Allow container network access
sudo setsebool -P container_manage_cgroup 1

# Allow container volume access
sudo semanage fcontext -a -t container_file_t "/path/to/qdrant/storage(/.*)?"
sudo restorecon -Rv /path/to/qdrant/storage
```

### 4. Configure Claude Desktop

Create or edit `~/.config/Claude Desktop/claude_desktop_config.json`:

```json
{
  "servers": [
    {
      "type": "qdrant",
      "config": {
        "command": "podman",
        "args": [
          "run",
          "--rm",
          "-p", "8000:8000",
          "--name", "mcp-qdrant",
          "--security-opt", "label=disable",
          "-e", "COLLECTION_NAME=memories",
          "-e", "QDRANT_URL=http://host.containers.internal:6333",
          "-e", "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2",
          "localhost/mcp-server-qdrant:latest"
        ]
      }
    }
  ]
}
```

## Building and Running

### 1. Build the Container Image

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-server-qdrant.git
cd mcp-server-qdrant

# Build the image using Podman
podman build \
    --build-arg VERSION=$(cat VERSION) \
    --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
    --build-arg VCS_REF=$(git rev-parse --short HEAD) \
    -t localhost/mcp-server-qdrant:latest .
```

### 2. Set Up Persistent Storage

```bash
# Create a volume for Qdrant data
podman volume create qdrant_storage

# Optional: Set specific permissions
sudo chown -R $USER:$USER $HOME/.local/share/containers/storage/volumes/qdrant_storage
```

### 3. Run Qdrant

```bash
# Run Qdrant container with persistent storage
podman run -d \
    --name qdrant \
    -p 6333:6333 \
    -p 6334:6334 \
    --security-opt label=disable \
    -v qdrant_storage:/qdrant/storage \
    docker.io/qdrant/qdrant:latest
```

### 4. Run MCP Server

```bash
# Run MCP server container
podman run -d \
    --name mcp-qdrant \
    -p 8000:8000 \
    --security-opt label=disable \
    -e COLLECTION_NAME=memories \
    -e QDRANT_URL=http://host.containers.internal:6333 \
    -e EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 \
    localhost/mcp-server-qdrant:latest
```

## Container Management

### Basic Commands

```bash
# List running containers
podman ps

# Stop containers
podman stop mcp-qdrant qdrant

# Start containers
podman start mcp-qdrant qdrant

# View logs
podman logs -f mcp-qdrant

# Remove containers
podman rm -f mcp-qdrant qdrant
```

### Using Podman Compose

Create `podman-compose.yml`:

```yaml
version: '3'
services:
  qdrant:
    image: docker.io/qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
    security_opt:
      - label=disable

  mcp-server:
    image: localhost/mcp-server-qdrant:latest
    ports:
      - "8000:8000"
    environment:
      - COLLECTION_NAME=memories
      - QDRANT_URL=http://qdrant:6333
      - EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
    depends_on:
      - qdrant
    security_opt:
      - label=disable

volumes:
  qdrant_storage:
```

Run with compose:
```bash
podman-compose up -d
```

## Troubleshooting

### Common Issues

1. **SELinux Conflicts**
   ```bash
   # Temporarily disable SELinux
   sudo setenforce 0
   
   # Check SELinux status
   getenforce
   
   # View SELinux denials
   sudo ausearch -m AVC -ts recent
   ```

2. **Network Issues**
   ```bash
   # Check container networking
   podman network ls
   
   # Inspect container network settings
   podman inspect mcp-qdrant -f '{{.NetworkSettings.IPAddress}}'
   
   # Test container connectivity
   podman exec mcp-qdrant curl -v http://qdrant:6333
   ```

3. **Permission Issues**
   ```bash
   # Check volume permissions
   ls -la $HOME/.local/share/containers/storage/volumes/
   
   # Fix ownership
   sudo chown -R $USER:$USER $HOME/.local/share/containers/
   ```

### Resource Management

```bash
# View container resources
podman stats

# Set resource limits
podman run -d \
    --name mcp-qdrant \
    --memory=2g \
    --cpus=2 \
    localhost/mcp-server-qdrant:latest
```

## Security Considerations

1. **Rootless Containers**
   - Podman runs containers as non-root by default
   - No need for root privileges for most operations
   - Better security isolation

2. **Network Security**
   ```bash
   # Create isolated network
   podman network create mcp-network
   
   # Run containers in isolated network
   podman run -d --network mcp-network --name qdrant qdrant/qdrant
   ```

3. **SELinux Policies**
   - Use `--security-opt label=disable` only when necessary
   - Consider creating custom SELinux policies for production

## References

- [RHEL 9 Container Documentation](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/building_running_and_managing_containers/index)
- [Podman Documentation](https://docs.podman.io/)
- [SELinux Container Guide](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/using_selinux/) 