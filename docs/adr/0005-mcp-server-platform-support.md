# 5. MCP Server Platform Support

Date: 2024-03-19

## Status

Accepted

## Context

The MCP (Model Context Protocol) server needs to run reliably across different platforms and integrate seamlessly with Claude Desktop. This ADR documents the decisions and requirements for platform support, with a particular focus on Windows environments and Claude Desktop integration.

## Decision

We will support running the MCP server in the following configurations:

### 1. Local Development Environment

- Python 3.11+ required for development and testing
- Virtual environment management using `hatch`
- Package management through `pyproject.toml` and `requirements.txt`

### 2. Claude Desktop Integration

- Support for Claude Desktop Pro subscription required
- MCP server plugins must be installed globally
- Configuration through `claude_desktop_config.json`
- Administrator privileges required for Windows installations

### 3. Windows-Specific Requirements

- Node.js and npm for running MCP server plugins
- Python 3.11+ with PATH configuration
- Global installation of MCP server packages
- Absolute paths in configuration files
- Administrator rights for Claude Desktop

### 4. Installation Steps

For Windows:
```bash
# Install required packages globally
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-github
npm install -g @modelcontextprotocol/server-memory

# Install Python packages
pip install mcp-server-qdrant
```

For macOS/Linux:
```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install hatch
hatch env create
```

### 5. Configuration

Claude Desktop configuration (`claude_desktop_config.json`):
```json
{
  "servers": [
    {
      "type": "qdrant",
      "config": {
        "node_path": "C:\\Program Files\\nodejs\\node.exe",
        "server_path": "C:\\Users\\Username\\AppData\\Roaming\\npm\\node_modules\\@modelcontextprotocol\\server-qdrant\\dist\\index.js",
        "env": {
          "QDRANT_URL": "http://localhost:6333",
          "COLLECTION_NAME": "memories"
        }
      }
    }
  ]
}
```

## Consequences

### Positive

1. Consistent development experience across platforms
2. Clear installation and configuration requirements
3. Reliable integration with Claude Desktop
4. Support for both local and remote Qdrant instances
5. Standardized environment setup process

### Negative

1. Additional setup complexity on Windows
2. Administrator privileges requirement
3. Global package installation requirements
4. Multiple runtime dependencies

### Mitigations

1. Provide detailed setup documentation
2. Include platform-specific troubleshooting guides
3. Implement automated environment checks
4. Add validation for configuration files

## References

1. [Setting up Claude Filesystem MCP](https://medium.com/@richardhightower/setting-up-claude-filesystem-mcp-80e48a1d3def)
2. [MCP Protocol Documentation](https://modelcontextprotocol.io/tutorials/building-mcp-with-llms)
3. [Windows Installation Guide](https://gist.github.com/feveromo/7a340d7795fca1ccd535a5802b976e1f) 