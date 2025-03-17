FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy test tracker code
COPY scripts/test_tracker.py /app/scripts/
COPY scripts/debug_tools /app/scripts/debug_tools/

# Create necessary directories
RUN mkdir -p /app/.mcp/debug_sessions /app/.mcp/snapshots /app/.mcp/audit_trail

# Environment variables
ENV PYTHONPATH=/app
ENV MCP_LLM_ENABLED=true
ENV MCP_QDRANT_URL=http://qdrant:6333

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/app/.mcp/test_history.db').close()"

# Start test tracker
CMD ["python", "-m", "scripts.test_tracker", "serve"] 