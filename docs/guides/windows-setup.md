# Windows Setup Guide

This guide provides detailed instructions for setting up and running the MCP Server Qdrant on Windows systems.

## Prerequisites

1. **Python 3.11+**
   - Download from [Python.org](https://www.python.org/downloads/)
   - During installation:
     - Check "Add Python to PATH"
     - Check "Install for all users"

2. **Node.js and npm**
   - Download from [Node.js website](https://nodejs.org/)
   - Install the LTS version
   - Verify installation:
     ```cmd
     node --version
     npm --version
     ```

3. **Git (Optional)**
   - Download from [Git-scm.com](https://git-scm.com/download/win)
   - Install with default options

## Installation Steps

### 1. Install Global Dependencies

Open PowerShell as Administrator and run:

```powershell
# Install MCP server packages
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-github
npm install -g @modelcontextprotocol/server-memory
npm install -g @modelcontextprotocol/server-qdrant

# Install Python package
pip install mcp-server-qdrant
```

### 2. Configure Claude Desktop

1. Open File Explorer
2. Navigate to `%APPDATA%\Claude Desktop`
3. Create or edit `claude_desktop_config.json`:

```json
{
  "servers": [
    {
      "type": "qdrant",
      "config": {
        "node_path": "C:\\Program Files\\nodejs\\node.exe",
        "server_path": "C:\\Users\\YourUsername\\AppData\\Roaming\\npm\\node_modules\\@modelcontextprotocol\\server-qdrant\\dist\\index.js",
        "env": {
          "QDRANT_URL": "http://localhost:6333",
          "COLLECTION_NAME": "memories",
          "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2"
        }
      }
    }
  ]
}
```

Replace `YourUsername` with your actual Windows username.

### 3. Local Development Setup

If you want to develop or modify the server:

1. Clone the repository:
```cmd
git clone https://github.com/yourusername/mcp-server-qdrant.git
cd mcp-server-qdrant
```

2. Create a virtual environment:
```cmd
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:
```cmd
pip install hatch
hatch env create
```

4. Install in development mode:
```cmd
pip install -e .
```

## Running the Server

### Method 1: Direct Run

```cmd
set COLLECTION_NAME=my_collection
set QDRANT_URL=http://localhost:6333
python -m mcp_server_qdrant
```

### Method 2: Using Docker Desktop

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Run:
```cmd
docker run -d -p 8000:8000 ^
    -e COLLECTION_NAME=my_collection ^
    -e QDRANT_URL=http://host.docker.internal:6333 ^
    mcp-server-qdrant:latest
```

## Troubleshooting

### Common Issues

1. **Python not found**
   - Verify Python is in PATH
   - Open System Properties > Environment Variables
   - Add Python installation path to System PATH

2. **Permission Errors**
   - Run PowerShell/CMD as Administrator
   - Check file permissions in installation directories

3. **Node.js Global Installation Fails**
   - Clear npm cache: `npm cache clean --force`
   - Reinstall with admin rights

4. **Claude Desktop Integration Issues**
   - Verify paths in `claude_desktop_config.json`
   - Check Claude Desktop logs
   - Ensure all required environment variables are set

### Getting Help

1. Check the [GitHub Issues](https://github.com/yourusername/mcp-server-qdrant/issues)
2. Join our [Discord Community](#)
3. Review the [FAQ](../faq.md)

## Security Considerations

1. **API Keys**
   - Store API keys securely
   - Use environment variables instead of hardcoding
   - Never commit sensitive data to version control

2. **Network Security**
   - Use HTTPS for remote Qdrant instances
   - Configure firewalls appropriately
   - Limit access to local ports

## Updating

To update the MCP server and its dependencies:

```powershell
# Update global packages
npm update -g @modelcontextprotocol/server-qdrant

# Update Python package
pip install --upgrade mcp-server-qdrant
```

## References

- [Claude Desktop Documentation](https://docs.claude.ai/desktop)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [Python Windows Setup Guide](https://docs.python.org/3/using/windows.html) 