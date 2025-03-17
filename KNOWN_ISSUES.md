# Known Issues

## MCP Server Startup Issues

### Manual Start Required for MCP Server Container

**Issue:** The MCP server container (`mcp-server-qdrant-mcp-server-1`) does not start automatically with `docker-compose up -d` and requires manual intervention.

**Workaround:** After starting the services with Docker Compose, manually start the MCP server container:

```bash
docker start mcp-server-qdrant-mcp-server-1
```

**Root Cause:** The MCP server is likely failing its initial startup due to timing issues with the Qdrant container. Although we've implemented retry logic and health checks, there may still be race conditions or configuration issues preventing automatic startup.

**Future Fix:** We plan to investigate and resolve this issue in a future update by:
1. Improving the startup script to better handle Qdrant availability
2. Adding more robust health checking between containers
3. Implementing proper Docker Compose dependency management with healthchecks

## Qdrant Connection Issues

### Intermittent Connection Failures

**Issue:** Occasionally, the MCP server may fail to connect to Qdrant even when both containers are running.

**Workaround:** Restart the MCP server container:

```bash
docker restart mcp-server-qdrant-mcp-server-1
```

**Root Cause:** This may be due to network timing issues or DNS resolution problems within the Docker network.

## Dashboard Data Visibility

### Data Not Immediately Visible in Dashboard

**Issue:** After running the test script, data may not immediately appear in the Qdrant dashboard.

**Workaround:** Refresh the dashboard page or wait a few seconds and navigate to the Collections tab again.

## Environment-Specific Issues

### MacOS Docker Network Issues

**Issue:** On some MacOS systems, there may be issues with Docker networking between containers.

**Workaround:** Use host networking mode in Docker Compose:

```yaml
# In docker-compose.yml
services:
  mcp-server:
    # ... other settings
    network_mode: "host"
  
  qdrant:
    # ... other settings
    network_mode: "host"
```

### Windows Path Issues

**Issue:** On Windows systems, there may be path-related issues when mounting volumes.

**Workaround:** Use WSL2 for Docker or adjust paths in docker-compose.yml to use proper Windows path format. 