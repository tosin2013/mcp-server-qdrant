# MCP Server Qdrant

Model Context Protocol server implementation for Qdrant vector database.

## Features

- Implements MCP protocol for Qdrant vector database
- Supports embedding generation with FastEmbed
- Configurable through environment variables
- Docker support for easy deployment

## Installation

```bash
pip install mcp-server-qdrant
```

## Usage

Set required environment variables:

```bash
export QDRANT_URL=http://localhost:6333
export COLLECTION_NAME=my_collection
```

Run the server:

```bash
mcp-server-qdrant
```

## Development

Run tests:

```bash
docker-compose -f docker-compose.test.yml up --build
```

## Documentation

- [Getting Started](docs/guides/getting-started.md)
- [Docker Setup Guide](docs/guides/docker-setup.md)
- [Task Management Guide](docs/guides/task-management.md)
- [Architecture Decisions](docs/adr/)

## Quick Start

1. Install prerequisites:
   - Docker Desktop
   - Claude Desktop or another MCP client
   - Git

2. Clone and start services:
```bash
git clone https://github.com/your-org/mcp-server-qdrant
cd mcp-server-qdrant
docker-compose up -d
```

3. Configure your MCP client (see [Task Management Guide](docs/guides/task-management.md))

4. Start using the system:
```
I have a test failure in test_authentication. Can you help me find similar issues?
```

## Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

### Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Prerequisites

- Python 3.11 or higher
- Docker (optional, for containerized deployment)
- Node.js and npm (for Claude Desktop integration)

## Platform-Specific Setup Guides

We provide detailed setup guides for different platforms and deployment methods:

1. [Docker Desktop Setup Guide](docs/guides/docker-setup.md)
   - For Windows, macOS, and Linux users using Docker Desktop
   - Includes container configuration and Claude Desktop integration
   - Best for users who prefer containerized deployment

2. [RHEL 9 Podman Setup Guide](docs/guides/rhel-podman-setup.md)
   - For RHEL 9 and compatible distributions using Podman
   - Includes SELinux configuration and security considerations
   - Optimized for enterprise Linux environments

3. [Windows Setup Guide](docs/guides/windows-setup.md)
   - For Windows users running directly on the host
   - Includes detailed Python and Node.js setup
   - Best for local development on Windows

Choose the guide that best matches your platform and deployment preferences.

## Configuration

The server can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| QDRANT_URL | URL of the Qdrant server | None |
| QDRANT_LOCAL_PATH | Path to local Qdrant storage | None |
| COLLECTION_NAME | Name of the Qdrant collection | Required |
| EMBEDDING_PROVIDER | Embedding provider (fastembed) | fastembed |
| EMBEDDING_MODEL | Model name for embeddings | sentence-transformers/all-MiniLM-L6-v2 |

Note: You must specify either `QDRANT_URL` or `QDRANT_LOCAL_PATH`, but not both.

## Testing

### Running Tests

1. Run all tests:
```bash
./scripts/e2e_test.sh
```

2. Run specific test categories:
```bash
# Unit tests only
python -m pytest tests/unit/

# Integration tests only
python -m pytest tests/integration/

# Settings tests
python -m pytest tests/test_settings.py
```

### Test Coverage

To generate a test coverage report:
```bash
python -m pytest --cov=src/mcp_server_qdrant tests/
```

## Building

### Local Build

```bash
hatch build
```

### Docker Build

```bash
docker build \
    --build-arg VERSION=$(cat VERSION) \
    --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
    --build-arg VCS_REF=$(git rev-parse --short HEAD) \
    -t mcp-server-qdrant:latest .
```

## Running

### Local Development

```bash
# Set required environment variables
export COLLECTION_NAME=my_collection
export QDRANT_URL=http://localhost:6333

# Run the server
python -m mcp_server_qdrant
```

### Docker Container

```bash
docker run -d \
    -p 8000:8000 \
    -e COLLECTION_NAME=my_collection \
    -e QDRANT_URL=http://qdrant:6333 \
    mcp-server-qdrant:latest
```

## Claude Desktop Integration

### Configuration Format

For local development using `uvx`:
```json
{
  "qdrant": {
    "command": "uvx",
    "args": ["mcp-server-qdrant"],
    "env": {
      "QDRANT_URL": "https://xyz-example.eu-central.aws.cloud.qdrant.io:6333",
      "QDRANT_API_KEY": "your_api_key",
      "COLLECTION_NAME": "your-collection-name",
      "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2"
    }
  }
}
```

For Docker deployment:
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

For cloud-hosted Qdrant:
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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

[Your License Here]

## References

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [FastEmbed Documentation](https://github.com/qdrant/fastembed)
