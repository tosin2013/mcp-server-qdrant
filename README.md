# MCP Server Qdrant

A Model Context Protocol (MCP) server implementation using Qdrant as the vector database backend. This server enables semantic search and memory storage capabilities for AI assistants.

## Features

- Semantic search using Qdrant vector database
- FastEmbed for efficient text embeddings
- Support for both local and remote Qdrant instances
- Configurable through environment variables
- Integration with Claude Desktop and other MCP clients

## Prerequisites

- Python 3.11 or higher
- Docker (optional, for containerized deployment)
- Node.js and npm (for Claude Desktop integration)

## Installation

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/tosin2013/mcp-server-qdrant.git
cd mcp-server-qdrant
```

2. Create and activate a virtual environment:
```bash
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install hatch
hatch env create
```

4. Install the package in development mode:
```bash
pip install -e .
```

### Production Installation

```bash
pip install mcp-server-qdrant
```

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

1. Install required packages globally:
```bash
npm install -g @modelcontextprotocol/server-qdrant
```

2. Configure Claude Desktop:
- Create or edit `claude_desktop_config.json`
- Add the Qdrant server configuration (see ADR for details)

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
